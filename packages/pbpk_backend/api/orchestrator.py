from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from pbpk_backend.services.orchestrator import (
    OrchestratorConfig,
    build_crate,
    deposit_crate,
    validate_crate,
    validate_metadata,
)

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


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@router.post("/uploads")
def api_create_upload() -> Dict[str, Any]:
    cfg = _cfg()
    upload_id = _new_id("upload")
    upload_dir = (cfg.data_root / "uploads" / upload_id).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    return {"upload_id": upload_id, "upload_dir": str(upload_dir)}


@router.post("/uploads/{upload_id}/file")
async def api_upload_file(
    upload_id: str,
    relpath: str = Form(...),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Upload a file to a staging area.
    relpath is the target path inside the staging dir (e.g. 'model/model.xml').
    """
    cfg = _cfg()
    upload_dir = (cfg.data_root / "uploads" / upload_id).resolve()
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail="upload_id not found")

    # Prevent path traversal
    rel = Path(relpath)
    if rel.is_absolute() or ".." in rel.parts:
        raise HTTPException(status_code=400, detail="Invalid relpath")

    target = (upload_dir / rel).resolve()
    if not str(target).startswith(str(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid relpath")

    target.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    target.write_bytes(content)

    return {"ok": True, "stored_as": str(target), "bytes": len(content)}


@router.post("/metadata/validate")
def api_validate_metadata(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Accepts either:
      - raw PBPK metadata payload, OR
      - {"metadata": <payload>, ...}
    """
    cfg = _cfg()
    payload = body["metadata"] if "metadata" in body else body
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")
    return validate_metadata(cfg, payload)


@router.post("/rocrate/build")
def api_build_rocrate(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Accepts either:
      - raw PBPK metadata payload (dict with general_model_information...), OR
      - {"metadata": <payload>, "upload_id": "upload_..."}.
    """
    cfg = _cfg()

    if "metadata" in body:
        payload = body["metadata"]
        upload_id = body.get("upload_id")
    else:
        payload = body
        upload_id = None

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")

    source_dir = None
    if upload_id:
        source_dir = (cfg.data_root / "uploads" / upload_id).resolve()
        if not source_dir.exists():
            raise HTTPException(status_code=404, detail="upload_id not found")

    out = build_crate(cfg, payload, source_files_dir=source_dir)
    if upload_id:
        out["upload_id"] = upload_id
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

    # Avoid leaking temp dirs: store zips under PBPK_DATA_ROOT/tmp_zips/
    zip_dir = (cfg.data_root / "tmp_zips").resolve()
    zip_dir.mkdir(parents=True, exist_ok=True)

    zip_base = zip_dir / crate_id  # shutil.make_archive adds ".zip"
    zip_path = Path(str(zip_base) + ".zip")

    # Recreate zip each time (simple + deterministic)
    if zip_path.exists():
        zip_path.unlink()

    shutil.make_archive(str(zip_base), "zip", root_dir=str(crate_dir))

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