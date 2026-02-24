from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pbpk-ui"])

def _ui_root() -> Path:
    # packages/pbpk_backend/api/ui.py -> packages/pbpk_backend/ui
    return Path(__file__).resolve().parents[1] / "ui"

@router.get("/ui", response_class=HTMLResponse)
def ui_index() -> HTMLResponse:
    html_path = _ui_root() / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))