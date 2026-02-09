from __future__ import annotations

import os
import urllib.parse
import urllib.request
import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

from pbpk_backend.storage.database import SQLiteDB
from pbpk_backend.models.user import User


router = APIRouter(prefix="/v1/auth", tags=["auth"])

SESSION_COOKIE_NAME = os.environ.get("PBPK_SESSION_COOKIE", "pbpk_session")


def _db() -> SQLiteDB:
    return SQLiteDB.from_env()


def _orcid_base(sandbox: bool) -> str:
    # ORCID authorize/token endpoints are under orcid.org / sandbox.orcid.org :contentReference[oaicite:1]{index=1}
    if sandbox:
        return os.environ.get("ORCID_SANDBOX_BASE_URL", "https://sandbox.orcid.org").rstrip("/")
    return os.environ.get("ORCID_BASE_URL", "https://orcid.org").rstrip("/")


def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise HTTPException(status_code=500, detail=f"Missing server env var: {name}")
    return v


def _build_authorize_url(*, sandbox: bool, state: str) -> str:
    base = _orcid_base(sandbox)
    client_id = _require_env("ORCID_CLIENT_ID")
    redirect_uri = _require_env("ORCID_REDIRECT_URI")

    # /authenticate gets an authenticated ORCID iD and read public info :contentReference[oaicite:2]{index=2}
    scope = os.environ.get("ORCID_SCOPE", "/authenticate")

    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"{base}/oauth/authorize?{urllib.parse.urlencode(params)}"


def _exchange_code_for_token(*, sandbox: bool, code: str) -> Dict[str, Any]:
    base = _orcid_base(sandbox)
    token_url = f"{base}/oauth/token"  # ORCID token endpoint :contentReference[oaicite:3]{index=3}

    client_id = _require_env("ORCID_CLIENT_ID")
    client_secret = _require_env("ORCID_CLIENT_SECRET")
    redirect_uri = _require_env("ORCID_REDIRECT_URI")

    data = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        token_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=400, detail=f"ORCID token exchange failed: {body}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ORCID token exchange error: {e}")


def _user_from_orcid_token(token_payload: Dict[str, Any]) -> User:
    """
    ORCID token response commonly includes: orcid, name (for /authenticate flows).
    We treat missing name as None and do not fail login.
    """
    orcid = token_payload.get("orcid")
    if not orcid or not isinstance(orcid, str):
        raise HTTPException(status_code=400, detail="ORCID response missing 'orcid' field")

    name = token_payload.get("name")
    if name is not None and not isinstance(name, str):
        name = None

    return User(orcid=orcid, name=name)


@router.get("/orcid/login")
def orcid_login(request: Request, sandbox: bool = False, redirect_to: Optional[str] = None):
    """
    Redirect user to ORCID OAuth authorize page.
    """
    db = _db()
    state = db.create_oauth_state(redirect_to=redirect_to)
    url = _build_authorize_url(sandbox=sandbox, state=state)
    return RedirectResponse(url, status_code=302)


@router.get("/orcid/callback")
def orcid_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    sandbox: bool = False,
):
    """
    ORCID redirects here with ?code=...&state=...
    """
    if error:
        raise HTTPException(status_code=400, detail=f"ORCID error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    db = _db()
    st = db.consume_oauth_state(state=state)
    if st is None:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    token_payload = _exchange_code_for_token(sandbox=sandbox, code=code)
    user = _user_from_orcid_token(token_payload)

    # Persist user and create session token
    row = db.upsert_user(orcid=user.orcid, name=user.name)
    session_token, expires_at = db.create_session(orcid=user.orcid)

    resp = JSONResponse(
        {
            "ok": True,
            "user": {
                "orcid": row.orcid,
                "name": row.name,
                "created_at": row.created_at,
                "last_login_at": row.last_login_at,
            },
            "session": {"expires_at": expires_at},
            "redirect_to": st.get("redirect_to"),
        }
    )

    # Cookie session (v1). In production: set secure=True behind HTTPS.
    secure_cookie = os.environ.get("PBPK_COOKIE_SECURE", "false").lower() == "true"
    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,  # 14 days
        path="/",
    )
    return resp


@router.post("/logout")
def logout(request: Request):
    db = _db()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        db.delete_session(token=token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return resp


def get_current_user(request: Request) -> User:
    """
    Dependency for protected endpoints. Reads session cookie.
    """
    db = _db()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sess = db.get_session(token=token)
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    row = db.get_user(orcid=sess["orcid"])
    if row is None:
        raise HTTPException(status_code=401, detail="User not found")

    return User(orcid=row.orcid, name=row.name, created_at=row.created_at, last_login_at=row.last_login_at)
