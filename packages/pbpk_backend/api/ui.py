from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

router = APIRouter(prefix="/ui", tags=["pbpk-ui"])


def _repo_root() -> Path:
    # .../packages/pbpk_backend/api/ui.py -> repo root
    return Path(__file__).resolve().parents[3]


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def ui_index() -> HTMLResponse:
    """
    Simple static HTML UI (no build step).
    """
    root = _repo_root()
    html_path = root / "packages" / "pbpk_backend" / "ui" / "pbpk.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail=f"UI not found: {html_path}")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@router.get("/pbpk.js")
def ui_js() -> Response:
    root = _repo_root()
    js_path = root / "packages" / "pbpk_backend" / "ui" / "pbpk.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail=f"UI JS not found: {js_path}")
    return Response(js_path.read_text(encoding="utf-8"), media_type="application/javascript")


@router.get("/example/pbpk-metadata.json")
def ui_example_metadata() -> Response:
    """
    Serves the example metadata file to the UI.
    """
    root = _repo_root()
    ex = root / "examples" / "minimal-pbpk-metadata" / "pbpk-metadata.json"
    if not ex.exists():
        raise HTTPException(status_code=404, detail=f"Example not found: {ex}")
    # Validate JSON to avoid serving broken file
    obj = json.loads(ex.read_text(encoding="utf-8"))
    return Response(json.dumps(obj, indent=2) + "\n", media_type="application/json")