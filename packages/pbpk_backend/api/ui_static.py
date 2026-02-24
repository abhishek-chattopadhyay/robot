from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pbpk-ui"])

@router.get("/ui/pbpk", response_class=HTMLResponse)
def ui_pbpk() -> HTMLResponse:
    repo_root = Path(__file__).resolve().parents[3]
    html_path = repo_root / "packages" / "pbpk_backend" / "static" / "pbpk-form.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))