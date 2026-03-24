from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from pbpk_backend.api.auth import get_current_user


PUBLIC_PREFIXES = (
    "/v1/auth",
    "/docs",
    "/redoc",
    "/openapi.json",
)

PUBLIC_EXACT = {
    "/",
    "/ui",
    "/health",
    "/favicon.ico",
}


def _enforce_auth() -> bool:
    return os.environ.get("ROBOT_ENFORCE_AUTH", "false").lower() == "true"


def auth_middleware_factory():
    async def auth_middleware(request: Request, call_next):
        path = request.url.path

        if not _enforce_auth():
            return await call_next(request)

        if path in PUBLIC_EXACT or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
            return await call_next(request)

        try:
            user = get_current_user(request)
        except Exception:
            user = None

        if not user:
            if path.startswith("/ui/"):
                target = request.url.path
                if request.url.query:
                    target = f"{target}?{request.url.query}"
                return RedirectResponse(url=f"/v1/auth/login?redirect_to={target}", status_code=302)

            if path.startswith("/v1/"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required",
                        "login_url": "/v1/auth/login",
                    },
                )

            return RedirectResponse(url="/ui", status_code=302)

        request.state.user = user
        return await call_next(request)

    return auth_middleware