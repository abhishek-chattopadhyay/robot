from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["ui"])

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

def _static_dir() -> Path:
    # NOTE: pbpk_backend (underscore) not pbpk-backend
    return _repo_root() / "packages" / "pbpk_backend" / "static"

@router.get("/ui")
def ui_index():
    html_path = _static_dir() / "ui-index.html"
    return FileResponse(html_path)

@router.get("/ui/pbpk")
def ui_pbpk():
    html_path = _static_dir() / "pbpk-form.html"
    return FileResponse(html_path)