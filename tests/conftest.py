from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"

if str(PACKAGES) not in sys.path:
    sys.path.insert(0, str(PACKAGES))


@pytest.fixture
def temp_data_root(tmp_path, monkeypatch) -> Path:
    data_root = tmp_path / "var"
    data_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("PBPK_DATA_ROOT", str(data_root))
    monkeypatch.setenv("PBPK_DB_PATH", str(data_root / "pbpk.db"))
    monkeypatch.setenv("ROBOT_ENFORCE_AUTH", "true")
    monkeypatch.setenv("PBPK_COOKIE_SECURE", "false")

    return data_root


@pytest.fixture
def app_client(temp_data_root):
    from pbpk_backend.app import app
    return TestClient(app)


@pytest.fixture
def sample_metadata() -> dict:
    path = ROOT / "examples" / "minimal-pbpk-metadata" / "pbpk-metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))


def create_session_cookie(*, orcid: str, name: str | None = None) -> tuple[str, str]:
    from pbpk_backend.storage.database import SQLiteDB

    db = SQLiteDB.from_env()
    db.upsert_user(orcid=orcid, name=name or orcid)
    token, _ = db.create_session(orcid=orcid)
    return "pbpk_session", token


@pytest.fixture
def client_for_user(app_client):
    def _make(orcid: str, name: str | None = None) -> TestClient:
        cookie_name, cookie_value = create_session_cookie(orcid=orcid, name=name)
        app_client.cookies.set(cookie_name, cookie_value)
        return app_client
    return _make