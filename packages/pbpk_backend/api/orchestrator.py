from __future__ import annotations

import json
from datetime import datetime

import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse

from pbpk_backend.services.audit import (
    AuditContext,
    audit_upload_event,
    audit_crate_event,
    audit_deposit_event_jsonl,
)
from pbpk_backend.services.orchestrator import (
    OrchestratorConfig,
    build_crate,
    deposit_crate,
    validate_crate,
    validate_metadata,
)

from pbpk_backend.services.drafts import create_draft, get_draft, replace_draft, validate_draft, build_from_draft
from pbpk_backend.services.drafts import patch_draft

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

def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _list_dirs_sorted_by_mtime(parent: Path) -> list[Path]:
    if not parent.exists():
        return []
    dirs = [p for p in parent.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs


def _walk_files(root: Path) -> list[Dict[str, Any]]:
    """
    List files under root (relative paths), excluding audit + tmp files.
    """
    out: list[Dict[str, Any]] = []
    if not root.exists():
        return out

    for p in root.rglob("*"):
        if not p.is_file():
            continue

        rel = p.relative_to(root).as_posix()

        # ignore audit/log files but show everything else
        if rel in {"audit.json"} or rel.endswith("deposit-events.jsonl"):
            continue

        out.append(
            {
                "path": rel,
                "bytes": p.stat().st_size,
                "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            }
        )
    out.sort(key=lambda x: x["path"])
    return out

@router.post("/uploads")
def api_create_upload() -> Dict[str, Any]:
    cfg = _cfg()
    upload_id = _new_id("upload")
    upload_dir = (cfg.data_root / "uploads" / upload_id).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    audit_upload_event(
        AuditContext(cfg.data_root),
        upload_id=upload_id,
        action="create_upload",
        details={"upload_dir": str(upload_dir)},
    )

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

    audit_upload_event(
        AuditContext(cfg.data_root),
        upload_id=upload_id,
        action="upload_file",
        details={"relpath": relpath, "stored_as": str(target), "bytes": len(content)},
    )

    return {"ok": True, "stored_as": str(target), "bytes": len(content)}

@router.get("/uploads")
def api_list_uploads(limit: int = 50) -> Dict[str, Any]:
    cfg = _cfg()
    uploads_root = (cfg.data_root / "uploads").resolve()
    items = []
    for d in _list_dirs_sorted_by_mtime(uploads_root)[: max(1, min(limit, 500))]:
        audit = _safe_read_json(d / "audit.json")
        items.append(
            {
                "upload_id": d.name,
                "upload_dir": str(d),
                "mtime": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
                "events": len((audit.get("events") or [])) if isinstance(audit, dict) else 0,
            }
        )
    return {"ok": True, "uploads": items}


@router.get("/uploads/{upload_id}")
def api_get_upload(upload_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    upload_dir = (cfg.data_root / "uploads" / upload_id).resolve()
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail="upload_id not found")

    audit = _safe_read_json(upload_dir / "audit.json")
    files = _walk_files(upload_dir)

    return {
        "ok": True,
        "upload_id": upload_id,
        "upload_dir": str(upload_dir),
        "files": files,
        "audit": audit,
    }

@router.post("/drafts")
def api_create_draft(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Option A: frontend sends raw PBPK metadata as the request body.
    Optional: {"metadata": <payload>, "upload_id": "..."} is accepted too.
    """
    cfg = _cfg()

    if "metadata" in body:
        metadata = body["metadata"]
        upload_id = body.get("upload_id")
    else:
        metadata = body
        upload_id = None

    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")

    return create_draft(cfg, metadata=metadata, upload_id=upload_id)


@router.get("/drafts/{draft_id}")
def api_get_draft(draft_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    try:
        return get_draft(cfg, draft_id=draft_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="draft not found")


@router.put("/drafts/{draft_id}")
def api_replace_draft(draft_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Replace draft metadata (raw payload or {"metadata": ..., "upload_id": ...}).
    """
    cfg = _cfg()

    if "metadata" in body:
        metadata = body["metadata"]
        upload_id = body.get("upload_id")
    else:
        metadata = body
        upload_id = None

    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")

    try:
        return replace_draft(cfg, draft_id=draft_id, metadata=metadata, upload_id=upload_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="draft not found")


@router.post("/drafts/{draft_id}/validate")
def api_validate_draft(draft_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    try:
        return validate_draft(cfg, draft_id=draft_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="draft not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drafts/{draft_id}/build")
def api_build_from_draft(draft_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    try:
        envelope, build_result = build_from_draft(cfg, draft_id=draft_id)
    except FileNotFoundError as e:
        msg = str(e)
        if msg.startswith("upload_id not found"):
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=404, detail="draft not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "draft": envelope, "build": build_result}

@router.patch("/drafts/{draft_id}")
def api_patch_draft(draft_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Body:
      {"patch": [ {op,path,value?}, ... ]}

    Applies JSON Patch ops to draft.metadata.
    """
    cfg = _cfg()
    ops = body.get("patch")
    if not isinstance(ops, list):
        raise HTTPException(status_code=400, detail="body.patch must be a list of JSON Patch operations")

    try:
        return patch_draft(cfg, draft_id=draft_id, patch_ops=ops)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="draft not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        audit_upload_event(
            AuditContext(cfg.data_root),
            upload_id=upload_id,
            action="build_crate_from_upload",
            details={"crate_id": out["crate_id"], "crate_dir": out.get("crate_dir")},
        )

    audit_crate_event(
        AuditContext(cfg.data_root),
        crate_id=out["crate_id"],
        action="build_crate",
        details={
            "upload_id": upload_id,
            "crate_dir": out.get("crate_dir"),
            "metadata_path": out.get("metadata_path"),
            "validation_ok": (out.get("validation") or {}).get("ok"),
        },
    )

    return out

@router.get("/crates")
def api_list_crates(limit: int = 50) -> Dict[str, Any]:
    cfg = _cfg()
    crates_root = (cfg.data_root / "crates").resolve()
    items = []
    for d in _list_dirs_sorted_by_mtime(crates_root)[: max(1, min(limit, 500))]:
        audit = _safe_read_json(d / "audit.json")
        items.append(
            {
                "crate_id": d.name,
                "crate_dir": str(d),
                "mtime": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
                "events": len((audit.get("events") or [])) if isinstance(audit, dict) else 0,
            }
        )
    return {"ok": True, "crates": items}

@router.get("/crates/{crate_id}")
def api_get_crate(crate_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    crate_dir = (cfg.data_root / "crates" / crate_id).resolve()
    if not crate_dir.exists():
        raise HTTPException(status_code=404, detail="Crate not found")

    audit = _safe_read_json(crate_dir / "audit.json")

    rocrate_path = crate_dir / "ro-crate-metadata.json"
    has_rocrate = rocrate_path.exists()
    rocrate_obj = _safe_read_json(rocrate_path) if has_rocrate else {}

    deposit_log = crate_dir / "deposit-events.jsonl"
    deposit_events_count = 0
    if deposit_log.exists():
        try:
            deposit_events_count = sum(1 for _ in deposit_log.open("r", encoding="utf-8"))
        except Exception:
            deposit_events_count = 0

    files = _walk_files(crate_dir)

    return {
        "ok": True,
        "crate_id": crate_id,
        "crate_dir": str(crate_dir),
        "paths": {
            "ro_crate_metadata": str(rocrate_path) if has_rocrate else None,
            "audit": str(crate_dir / "audit.json"),
            "deposit_events_jsonl": str(deposit_log) if deposit_log.exists() else None,
        },
        "validation_hint": {
            "endpoint": f"/v1/rocrate/{crate_id}/validate",
            "download": f"/v1/rocrate/{crate_id}/download",
        },
        "deposit_events_count": deposit_events_count,
        "files": files,
        "audit": audit,
        # For convenience in v1. If too large later, we’ll add a flag to omit it.
        "ro_crate_metadata_jsonld": rocrate_obj,
    }

@router.get("/rocrate/{crate_id}/validate")
def api_validate_rocrate(
    crate_id: str,
    layers: list[str] = Query(default=["base", "domain"]),
) -> Dict[str, Any]:
    cfg = _cfg()
    return validate_crate(cfg, crate_id, layers=set(layers))


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

    result = deposit_crate(
        cfg,
        crate_id=crate_id,
        platform=platform,
        token=token,
        sandbox=sandbox,
        publish=publish,
    )

    audit_deposit_event_jsonl(
        AuditContext(cfg.data_root),
        crate_id=crate_id,
        platform=platform,
        result=result,
        request_details={"sandbox": sandbox, "publish": publish, "token": "<redacted>"},
    )

    return result