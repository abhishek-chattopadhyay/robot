from __future__ import annotations

import shutil
import tempfile
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from pbpk_backend.services.orchestrator import OrchestratorConfig, build_crate, deposit_crate, validate_crate, validate_metadata


router = APIRouter(prefix="/v1", tags=["pbpk-orchestrator"])


def _cfg() -> OrchestratorConfig:
    repo_root = Path(__file__).resolve().parents[3]  # .../packages/pbpk_backend/api -> repo root
    data_root = Path(os.environ.get("PBPK_DATA_ROOT", str(repo_root / "var"))).resolve()

    schema_path = repo_root / "packages" / "pbpk_validation" / "schemas" / "pbpk-metadata.schema.json"
    template_path = repo_root / "packages" / "pbpk-metadata-spec" / "jsonld" / "pbpk-core-template.jsonld"

    return OrchestratorConfig(
        data_root=data_root,
        schema_path=schema_path,
        template_path=template_path,
    )


@router.post("/metadata/validate")
def api_validate_metadata(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    cfg = _cfg()
    return validate_metadata(cfg, payload)


@router.post("/rocrate/build")
def api_build_rocrate(
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    cfg = _cfg()

    # v1: no file upload wiring here yet; that will connect to your storage layer next.
    out = build_crate(cfg, payload, source_files_dir=None)
    return out


@router.get("/rocrate/{crate_id}/validate")
def api_validate_rocrate(crate_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    return validate_crate(cfg, crate_id)

@router.get("/rocrate/{crate_id}/download")
def api_download_rocrate(crate_id: str):
    cfg = _cfg()
    crate_dir = (cfg.data_root / "crates" / crate_id).resolve()
    if not crate_dir.exists():
        raise HTTPException(status_code=404, detail="Crate not found")

    tmpdir = Path(tempfile.mkdtemp(prefix="pbpk_crate_dl_"))
    zip_base = tmpdir / crate_id
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", root_dir=str(crate_dir)))

    return FileResponse(
        path=str(zip_path),
        filename=f"{crate_id}.zip",
        media_type="application/zip",
    )

@router.post("/deposit/{platform}")
def api_deposit(platform: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    body expects:
      - crate_id: str
      - token: str
      - sandbox: bool (optional)
      - publish: bool (optional)
    """
    cfg = _cfg()

    crate_id = body.get("crate_id")
    token = body.get("token")
    sandbox = bool(body.get("sandbox", False))
    publish = bool(body.get("publish", False))

    if not crate_id or not token:
        raise HTTPException(status_code=400, detail="Missing crate_id or token")

    return deposit_crate(cfg, crate_id=crate_id, platform=platform, token=token, sandbox=sandbox, publish=publish)