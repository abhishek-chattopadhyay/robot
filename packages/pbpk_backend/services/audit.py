from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


@dataclass
class AuditContext:
    data_root: Path


def audit_upload_event(
    ctx: AuditContext,
    *,
    upload_id: str,
    action: str,
    actor: str = "anonymous",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    upload_dir = (ctx.data_root / "uploads" / upload_id).resolve()
    audit_path = upload_dir / "audit.json"

    record = {
        "upload_id": upload_id,
        "actor": actor,
        "timestamp": _utc_now_iso(),
        "action": action,
        "details": details or {},
    }

    if audit_path.exists():
        try:
            existing = json.loads(audit_path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
        except Exception:
            existing = {}
    else:
        existing = {}

    events = existing.get("events")
    if not isinstance(events, list):
        events = []
    events.append(record)

    existing["upload_id"] = upload_id
    existing["events"] = events
    existing["updated_at"] = record["timestamp"]
    if "created_at" not in existing:
        existing["created_at"] = record["timestamp"]

    _write_json(audit_path, existing)


def audit_crate_event(
    ctx: AuditContext,
    *,
    crate_id: str,
    action: str,
    actor: str = "anonymous",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    crate_dir = (ctx.data_root / "crates" / crate_id).resolve()
    audit_path = crate_dir / "audit.json"

    record = {
        "crate_id": crate_id,
        "actor": actor,
        "timestamp": _utc_now_iso(),
        "action": action,
        "details": details or {},
    }

    if audit_path.exists():
        try:
            existing = json.loads(audit_path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
        except Exception:
            existing = {}
    else:
        existing = {}

    events = existing.get("events")
    if not isinstance(events, list):
        events = []
    events.append(record)

    existing["crate_id"] = crate_id
    existing["events"] = events
    existing["updated_at"] = record["timestamp"]
    if "created_at" not in existing:
        existing["created_at"] = record["timestamp"]

    if actor and actor != "anonymous":
        existing["owner_orcid"] = actor

    _write_json(audit_path, existing)


def audit_deposit_event_jsonl(
    ctx: AuditContext,
    *,
    crate_id: str,
    actor: str = "anonymous",
    platform: str,
    result: Dict[str, Any],
    request_details: Optional[Dict[str, Any]] = None,
) -> None:
    crate_dir = (ctx.data_root / "crates" / crate_id).resolve()
    path = crate_dir / "deposit-events.jsonl"

    record = {
        "timestamp": _utc_now_iso(),
        "crate_id": crate_id,
        "actor": actor,
        "platform": platform,
        "request": request_details or {},
        "result": result,
    }

    if "token" in record["request"]:
        record["request"]["token"] = "<redacted>"

    _append_jsonl(path, record)