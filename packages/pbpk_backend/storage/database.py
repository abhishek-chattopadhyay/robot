from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class UserRow:
    orcid: str
    name: Optional[str]
    created_at: str
    last_login_at: Optional[str]


class SQLiteDB:
    """
    Minimal SQLite storage for:
      - users
      - sessions
      - oauth_states

    Intended for v1. Later you can swap to Postgres with the same method signatures.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def from_env(cls) -> "SQLiteDB":
        # Default under PBPK_DATA_ROOT/ (matches orchestrator default var/)
        data_root = Path(os.environ.get("PBPK_DATA_ROOT", str(Path.cwd() / "var"))).resolve()
        db_path = Path(os.environ.get("PBPK_DB_PATH", str(data_root / "pbpk.db"))).resolve()
        return cls(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def _init_schema(self) -> None:
        with self.connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    orcid TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    orcid TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(orcid) REFERENCES users(orcid)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    redirect_to TEXT
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_sessions_orcid ON sessions(orcid)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")

    # --- users ---

    def upsert_user(self, *, orcid: str, name: Optional[str]) -> UserRow:
        now = _utc_now()
        with self.connect() as con:
            row = con.execute("SELECT * FROM users WHERE orcid = ?", (orcid,)).fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO users(orcid, name, created_at, last_login_at) VALUES (?, ?, ?, ?)",
                    (orcid, name, now, now),
                )
            else:
                # keep created_at, update name if provided, update last_login_at
                new_name = name if name else row["name"]
                con.execute(
                    "UPDATE users SET name = ?, last_login_at = ? WHERE orcid = ?",
                    (new_name, now, orcid),
                )

            out = con.execute("SELECT * FROM users WHERE orcid = ?", (orcid,)).fetchone()
            return UserRow(
                orcid=out["orcid"],
                name=out["name"],
                created_at=out["created_at"],
                last_login_at=out["last_login_at"],
            )

    def get_user(self, *, orcid: str) -> Optional[UserRow]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM users WHERE orcid = ?", (orcid,)).fetchone()
            if row is None:
                return None
            return UserRow(
                orcid=row["orcid"],
                name=row["name"],
                created_at=row["created_at"],
                last_login_at=row["last_login_at"],
            )

    # --- oauth state ---

    def create_oauth_state(self, *, redirect_to: Optional[str] = None, ttl_minutes: int = 10) -> str:
        # random state; store for CSRF protection
        state = secrets.token_urlsafe(24)
        with self.connect() as con:
            con.execute(
                "INSERT INTO oauth_states(state, created_at, redirect_to) VALUES (?, ?, ?)",
                (state, _utc_now(), redirect_to),
            )
        return state

    def consume_oauth_state(self, *, state: str, max_age_minutes: int = 15) -> Optional[Dict[str, Any]]:
        """
        Returns {"redirect_to": ...} if state exists and is fresh; deletes the state.
        """
        with self.connect() as con:
            row = con.execute("SELECT * FROM oauth_states WHERE state = ?", (state,)).fetchone()
            if row is None:
                return None

            created = datetime.fromisoformat(row["created_at"])
            if datetime.now(timezone.utc) - created > timedelta(minutes=max_age_minutes):
                con.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
                return None

            con.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
            return {"redirect_to": row["redirect_to"]}

    # --- sessions ---

    def create_session(self, *, orcid: str, ttl_hours: int = 24 * 14) -> Tuple[str, str]:
        """
        Returns (token, expires_at_iso).
        """
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=ttl_hours)
        with self.connect() as con:
            con.execute(
                "INSERT INTO sessions(token, orcid, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, orcid, now.isoformat(), expires.isoformat()),
            )
        return token, expires.isoformat()

    def get_session(self, *, token: str) -> Optional[Dict[str, str]]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
            if row is None:
                return None

            expires = datetime.fromisoformat(row["expires_at"])
            if datetime.now(timezone.utc) > expires:
                con.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None

            return {"token": row["token"], "orcid": row["orcid"], "expires_at": row["expires_at"]}

    def delete_session(self, *, token: str) -> None:
        with self.connect() as con:
            con.execute("DELETE FROM sessions WHERE token = ?", (token,))
