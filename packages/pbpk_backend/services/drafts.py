from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pbpk_backend.services.orchestrator import OrchestratorConfig, build_crate, validate_metadata
from pbpk_backend.services.jsonpatch import apply_patch, PatchError


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class DraftPaths:
    draft_dir: Path
    draft_json: Path
    audit_json: Path


def _paths(cfg: OrchestratorConfig, draft_id: str) -> DraftPaths:
    ddir = (cfg.data_root / "drafts" / draft_id).resolve()
    return DraftPaths(
        draft_dir=ddir,
        draft_json=ddir / "draft.json",
        audit_json=ddir / "audit.json",
    )


def _init_audit(draft_id: str) -> Dict[str, Any]:
    return {
        "draft_id": draft_id,
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "events": [],
    }


def _append_audit(audit: Dict[str, Any], action: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    audit["updated_at"] = _utc_now_iso()
    ev = {
        "timestamp": _utc_now_iso(),
        "action": action,
        "details": details or {},
        "actor": "anonymous",
    }
    events = audit.get("events")
    if not isinstance(events, list):
        events = []
    events.append(ev)
    audit["events"] = events
    return audit


def _envelope(
    *,
    draft_id: str,
    metadata: Dict[str, Any],
    upload_id: Optional[str],
    status: str,
    validation: Optional[Dict[str, Any]],
    audit: Dict[str, Any],
    model_type: str = "pbpk",
) -> Dict[str, Any]:
    return {
        "api_version": "v1",
        "kind": f"{model_type}.metadata.draft",
        "draft_id": draft_id,
        "upload_id": upload_id,
        "model_type": model_type,
        "status": status,
        "metadata": metadata,
        "validation": validation,
        "audit": {
            "created_at": audit.get("created_at"),
            "updated_at": audit.get("updated_at"),
            "events": audit.get("events", []),
        },
    }


def get_draft_owner(cfg: OrchestratorConfig, *, draft_id: str) -> Optional[str]:
    p = _paths(cfg, draft_id)
    if not p.draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(p.draft_json)
    owner = draft_obj.get("owner_orcid")
    return owner if isinstance(owner, str) and owner else None


def require_draft_owner(cfg: OrchestratorConfig, *, draft_id: str, owner_orcid: str) -> None:
    owner = get_draft_owner(cfg, draft_id=draft_id)
    if owner is None:
        raise PermissionError("Draft has no owner")
    if owner != owner_orcid:
        raise PermissionError("You do not have access to this draft")


def create_draft(cfg: OrchestratorConfig, *, metadata: Dict[str, Any], upload_id: Optional[str] = None, model_type: str = "pbpk") -> Dict[str, Any]:
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")

    draft_id = _new_id("draft")
    p = _paths(cfg, draft_id)
    p.draft_dir.mkdir(parents=True, exist_ok=True)

    audit = _init_audit(draft_id)
    audit = _append_audit(audit, "create_draft", {"upload_id": upload_id, "model_type": model_type})

    draft_obj = {
        "draft_id": draft_id,
        "upload_id": upload_id,
        "model_type": model_type,
        "status": "draft",
        "metadata": metadata,
        "validation": None,
    }

    _write_json(p.draft_json, draft_obj)
    _write_json(p.audit_json, audit)

    return _envelope(
        draft_id=draft_id,
        metadata=metadata,
        upload_id=upload_id,
        status="draft",
        validation=None,
        audit=audit,
        model_type=model_type,
    )


def get_draft(cfg: OrchestratorConfig, *, draft_id: str) -> Dict[str, Any]:
    p = _paths(cfg, draft_id)
    if not p.draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(p.draft_json)
    audit = _read_json(p.audit_json) if p.audit_json.exists() else _init_audit(draft_id)
    model_type = draft_obj.get("model_type", "pbpk")

    return _envelope(
        draft_id=draft_id,
        metadata=draft_obj.get("metadata", {}),
        upload_id=draft_obj.get("upload_id"),
        status=draft_obj.get("status", "draft"),
        validation=draft_obj.get("validation"),
        audit=audit,
        model_type=model_type,
    )


def replace_draft(cfg: OrchestratorConfig, *, draft_id: str, metadata: Dict[str, Any], upload_id: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")

    p = _paths(cfg, draft_id)
    if not p.draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(p.draft_json)
    model_type = draft_obj.get("model_type", "pbpk")
    draft_obj["metadata"] = metadata
    if upload_id is not None:
        draft_obj["upload_id"] = upload_id
    if draft_obj.get("status") == "archived":
        draft_obj["status"] = "draft"
    else:
        draft_obj["status"] = "draft"
    draft_obj["validation"] = None

    audit = _read_json(p.audit_json) if p.audit_json.exists() else _init_audit(draft_id)
    audit = _append_audit(audit, "replace_draft", {"upload_id": draft_obj.get("upload_id")})

    _write_json(p.draft_json, draft_obj)
    _write_json(p.audit_json, audit)

    return _envelope(
        draft_id=draft_id,
        metadata=metadata,
        upload_id=draft_obj.get("upload_id"),
        status=draft_obj["status"],
        validation=None,
        audit=audit,
        model_type=model_type,
    )


def validate_draft(cfg: OrchestratorConfig, *, draft_id: str) -> Dict[str, Any]:
    p = _paths(cfg, draft_id)
    if not p.draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(p.draft_json)
    metadata = draft_obj.get("metadata", {})
    model_type = draft_obj.get("model_type", "pbpk")
    if not isinstance(metadata, dict):
        raise ValueError("draft metadata is not an object")

    validation = validate_metadata(cfg, metadata, model_type=model_type)
    draft_obj["validation"] = validation
    draft_obj["status"] = "validated" if validation.get("ok") else "draft"

    audit = _read_json(p.audit_json) if p.audit_json.exists() else _init_audit(draft_id)
    audit = _append_audit(audit, "validate_draft", {"ok": bool(validation.get("ok"))})

    _write_json(p.draft_json, draft_obj)
    _write_json(p.audit_json, audit)

    return _envelope(
        draft_id=draft_id,
        metadata=metadata,
        upload_id=draft_obj.get("upload_id"),
        status=draft_obj["status"],
        validation=validation,
        audit=audit,
        model_type=model_type,
    )


def build_from_draft(cfg: OrchestratorConfig, *, draft_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Returns (envelope, build_result)
    """
    p = _paths(cfg, draft_id)
    if not p.draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(p.draft_json)
    metadata = draft_obj.get("metadata", {})
    upload_id = draft_obj.get("upload_id")
    model_type = draft_obj.get("model_type", "pbpk")

    if not isinstance(metadata, dict):
        raise ValueError("draft metadata is not an object")

    source_dir = None
    if upload_id:
        source_dir = (cfg.data_root / "uploads" / upload_id).resolve()
        if not source_dir.exists():
            raise FileNotFoundError(f"upload_id not found: {upload_id}")

    build_result = build_crate(cfg, metadata, model_type=model_type, source_files_dir=source_dir)

    draft_obj["status"] = "built"
    audit = _read_json(p.audit_json) if p.audit_json.exists() else _init_audit(draft_id)
    audit = _append_audit(
        audit,
        "build_from_draft",
        {"crate_id": build_result.get("crate_id"), "upload_id": upload_id},
    )

    _write_json(p.draft_json, draft_obj)
    _write_json(p.audit_json, audit)

    envelope = _envelope(
        draft_id=draft_id,
        metadata=metadata,
        upload_id=upload_id,
        status="built",
        validation=draft_obj.get("validation"),
        audit=audit,
        model_type=model_type,
    )
    return envelope, build_result


def patch_draft(cfg: OrchestratorConfig, *, draft_id: str, patch_ops: list[dict[str, Any]]) -> Dict[str, Any]:
    p = _paths(cfg, draft_id)
    if not p.draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(p.draft_json)
    metadata = draft_obj.get("metadata", {})
    model_type = draft_obj.get("model_type", "pbpk")
    if not isinstance(metadata, dict):
        raise ValueError("draft metadata is not an object")

    try:
        new_metadata = apply_patch(metadata, patch_ops)
    except PatchError as e:
        raise ValueError(str(e))

    draft_obj["metadata"] = new_metadata
    draft_obj["status"] = "draft"
    draft_obj["validation"] = None

    audit = _read_json(p.audit_json) if p.audit_json.exists() else _init_audit(draft_id)
    audit = _append_audit(audit, "patch_draft", {"ops": patch_ops})

    _write_json(p.draft_json, draft_obj)
    _write_json(p.audit_json, audit)

    return _envelope(
        draft_id=draft_id,
        metadata=new_metadata,
        upload_id=draft_obj.get("upload_id"),
        status="draft",
        validation=None,
        audit=audit,
        model_type=model_type,
    )


def archive_draft(cfg: OrchestratorConfig, *, draft_id: str) -> Dict[str, Any]:
    p = _paths(cfg, draft_id)
    if not p.draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(p.draft_json)
    model_type = draft_obj.get("model_type", "pbpk")
    draft_obj["status"] = "archived"

    audit = _read_json(p.audit_json) if p.audit_json.exists() else _init_audit(draft_id)
    audit = _append_audit(audit, "archive_draft", {})

    _write_json(p.draft_json, draft_obj)
    _write_json(p.audit_json, audit)

    return _envelope(
        draft_id=draft_id,
        metadata=draft_obj.get("metadata", {}),
        upload_id=draft_obj.get("upload_id"),
        status="archived",
        validation=draft_obj.get("validation"),
        audit=audit,
        model_type=model_type,
    )


def delete_draft(cfg: OrchestratorConfig, *, draft_id: str) -> Dict[str, Any]:
    p = _paths(cfg, draft_id)
    if not p.draft_dir.exists():
        raise FileNotFoundError(draft_id)

    result = {
        "api_version": "v1",
        "kind": "pbpk.draft_delete_result",
        "draft_id": draft_id,
        "ok": True,
        "message": "Draft deleted.",
    }

    shutil.rmtree(p.draft_dir)
    return result


def duplicate_draft(cfg: OrchestratorConfig, *, draft_id: str) -> Dict[str, Any]:
    src = _paths(cfg, draft_id)
    if not src.draft_json.exists():
        raise FileNotFoundError(draft_id)

    src_draft_obj = _read_json(src.draft_json)
    metadata = src_draft_obj.get("metadata", {})
    upload_id = src_draft_obj.get("upload_id")
    model_type = src_draft_obj.get("model_type", "pbpk")

    if not isinstance(metadata, dict):
        raise ValueError("draft metadata is not an object")

    new_draft_id = _new_id("draft")
    dst = _paths(cfg, new_draft_id)
    dst.draft_dir.mkdir(parents=True, exist_ok=True)

    new_audit = _init_audit(new_draft_id)
    new_audit = _append_audit(
        new_audit,
        "duplicate_from_draft",
        {"source_draft_id": draft_id, "upload_id": upload_id},
    )

    new_draft_obj = {
        "draft_id": new_draft_id,
        "upload_id": upload_id,
        "model_type": model_type,
        "status": "draft",
        "metadata": metadata,
        "validation": None,
    }

    _write_json(dst.draft_json, new_draft_obj)
    _write_json(dst.audit_json, new_audit)

    return _envelope(
        draft_id=new_draft_id,
        metadata=metadata,
        upload_id=upload_id,
        status="draft",
        validation=None,
        audit=new_audit,
        model_type=model_type,
    )