from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from pbpk_backend.models.user import User
from pbpk_backend.storage.database import SQLiteDB


router = APIRouter(prefix="/v1/auth", tags=["auth"])

SESSION_COOKIE_NAME = os.environ.get("PBPK_SESSION_COOKIE", "pbpk_session")


def _db() -> SQLiteDB:
    return SQLiteDB.from_env()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _default_orcid_sandbox() -> bool:
    return _env_bool("ORCID_USE_SANDBOX", False)


def _sanitize_redirect_to(redirect_to: Optional[str]) -> str:
    """
    Allow only internal relative redirects.
    Prevent open redirect issues such as:
      - https://evil.com
      - //evil.com
      - javascript:...
    """
    if not redirect_to:
      return "/ui"

    redirect_to = redirect_to.strip()
    if not redirect_to.startswith("/"):
        return "/ui"
    if redirect_to.startswith("//"):
        return "/ui"
    return redirect_to


def _orcid_base(sandbox: bool) -> str:
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
    token_url = f"{base}/oauth/token"

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
    orcid = token_payload.get("orcid")
    if not orcid or not isinstance(orcid, str):
        raise HTTPException(status_code=400, detail="ORCID response missing 'orcid' field")

    name = token_payload.get("name")
    if name is not None and not isinstance(name, str):
        name = None

    return User(orcid=orcid, name=name)


@router.get("/login")
def login_redirect(
    request: Request,
    sandbox: Optional[bool] = None,
    redirect_to: Optional[str] = None,
):
    db = _db()

    use_sandbox = _default_orcid_sandbox() if sandbox is None else sandbox
    safe_redirect = _sanitize_redirect_to(redirect_to)

    state = db.create_oauth_state(redirect_to=safe_redirect)
    url = _build_authorize_url(sandbox=use_sandbox, state=state)
    return RedirectResponse(url=url, status_code=302)


@router.get("/orcid/login")
def orcid_login(
    request: Request,
    sandbox: Optional[bool] = None,
    redirect_to: Optional[str] = None,
):
    return login_redirect(request=request, sandbox=sandbox, redirect_to=redirect_to)


@router.get("/orcid/callback")
def orcid_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    sandbox: Optional[bool] = None,
):
    if error:
        raise HTTPException(status_code=400, detail=f"ORCID error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    use_sandbox = _default_orcid_sandbox() if sandbox is None else sandbox

    db = _db()
    st = db.consume_oauth_state(state=state)
    if st is None:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    token_payload = _exchange_code_for_token(sandbox=use_sandbox, code=code)
    user = _user_from_orcid_token(token_payload)

    row = db.upsert_user(orcid=user.orcid, name=user.name)
    session_token, _expires_at = db.create_session(orcid=user.orcid)

    redirect_to = _sanitize_redirect_to(st.get("redirect_to"))
    resp = RedirectResponse(url=redirect_to, status_code=302)

    secure_cookie = _env_bool("PBPK_COOKIE_SECURE", False)
    cookie_samesite = os.environ.get("PBPK_COOKIE_SAMESITE", "lax").strip().lower()
    if cookie_samesite not in {"lax", "strict", "none"}:
        cookie_samesite = "lax"

    cookie_domain = os.environ.get("PBPK_COOKIE_DOMAIN")
    max_age = 60 * 60 * 24 * 14

    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=secure_cookie,
        samesite=cookie_samesite,
        max_age=max_age,
        path="/",
        domain=cookie_domain if cookie_domain else None,
    )
    return resp


@router.get("/me")
def auth_me(request: Request) -> Dict[str, Any]:
    try:
        user = get_current_user(request)
    except HTTPException:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "orcid": user.orcid,
        "name": user.name,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


@router.get("/config")
def auth_config() -> Dict[str, Any]:
    """
    Useful for debugging deployment configuration without exposing secrets.
    """
    return {
        "orcid_use_sandbox": _default_orcid_sandbox(),
        "orcid_base_url": _orcid_base(_default_orcid_sandbox()),
        "redirect_uri": os.environ.get("ORCID_REDIRECT_URI"),
        "cookie_secure": _env_bool("PBPK_COOKIE_SECURE", False),
        "cookie_samesite": os.environ.get("PBPK_COOKIE_SAMESITE", "lax"),
        "cookie_domain": os.environ.get("PBPK_COOKIE_DOMAIN"),
    }


@router.post("/logout")
def logout(request: Request):
    db = _db()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        db.delete_session(token=token)

    resp = JSONResponse({"ok": True})
    cookie_domain = os.environ.get("PBPK_COOKIE_DOMAIN")
    resp.delete_cookie(SESSION_COOKIE_NAME, path="/", domain=cookie_domain if cookie_domain else None)
    return resp


def get_current_user(request: Request) -> User:
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

    return User(
        orcid=row.orcid,
        name=row.name,
        created_at=row.created_at,
        last_login_at=row.last_login_at,
    )