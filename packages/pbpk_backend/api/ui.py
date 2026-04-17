from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

router = APIRouter(prefix="/ui", tags=["ui"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _static_dir() -> Path:
    return _repo_root() / "packages" / "pbpk_backend" / "static"


def _read_text(path: Path) -> str:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"UI asset not found: {path}")
    return path.read_text(encoding="utf-8")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def ui_index() -> HTMLResponse:
    html_path = _static_dir() / "index.html"
    return HTMLResponse(_read_text(html_path))


@router.get("/pbpk", response_class=HTMLResponse)
def ui_pbpk() -> HTMLResponse:
    html_path = _static_dir() / "pbpk-form.html"
    return HTMLResponse(_read_text(html_path))


@router.get("/qaop", response_class=HTMLResponse)
def ui_qaop() -> HTMLResponse:
    html_path = _static_dir() / "qaop-form.html"
    return HTMLResponse(_read_text(html_path))


@router.get("/qaop.js")
def ui_qaop_js() -> Response:
    js_path = _static_dir() / "qaop.js"
    return Response(_read_text(js_path), media_type="application/javascript")


@router.get("/example/pbpk-metadata.json")
def ui_example_metadata() -> Response:
    root = _repo_root()
    ex = root / "examples" / "minimal-pbpk-metadata" / "pbpk-metadata.json"
    if not ex.exists():
        raise HTTPException(status_code=404, detail=f"Example not found: {ex}")
    obj = json.loads(ex.read_text(encoding="utf-8"))
    return Response(json.dumps(obj, indent=2) + "\n", media_type="application/json")