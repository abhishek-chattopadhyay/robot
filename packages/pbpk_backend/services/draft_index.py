from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_read_json(path: Path) -> dict[str, Any]:
    try:
        return _read_json(path)
    except Exception:
        return {}


def list_drafts_with_activity(
    *,
    data_root: Path,
    limit: int = 20,
    include_archived: bool = False,
    owner_orcid: str | None = None,
) -> list[dict[str, Any]]:
    drafts_root = (data_root / "drafts").resolve()
    if not drafts_root.exists():
        return []

    items: list[dict[str, Any]] = []

    for draft_dir in drafts_root.iterdir():
        if not draft_dir.is_dir():
            continue

        draft_json = draft_dir / "draft.json"
        audit_json = draft_dir / "audit.json"

        if not draft_json.exists():
            continue

        draft_obj = _safe_read_json(draft_json)
        audit_obj = _safe_read_json(audit_json)

        # Critical: enforce owner scoping here
        if owner_orcid is not None and draft_obj.get("owner_orcid") != owner_orcid:
            continue

        draft_id = draft_obj.get("draft_id") or draft_dir.name
        status = draft_obj.get("status")
        upload_id = draft_obj.get("upload_id")
        metadata = draft_obj.get("metadata") or {}

        if status == "archived" and not include_archived:
            continue

        if not isinstance(metadata, dict):
            metadata = {}

        model_type = draft_obj.get("model_type", "pbpk")

        if model_type == "qaop":
            identity = metadata.get("identity") or {}
            if not isinstance(identity, dict):
                identity = {}
            model_name = identity.get("title")
            model_version = identity.get("version")
        else:
            gmi = metadata.get("general_model_information") or {}
            if not isinstance(gmi, dict):
                gmi = {}
            model_name = gmi.get("model_name")
            model_version = gmi.get("model_version")

        events = audit_obj.get("events", [])
        if not isinstance(events, list):
            events = []

        latest_build: dict[str, Any] | None = None
        for ev in reversed(events):
            if not isinstance(ev, dict):
                continue
            if ev.get("action") == "build_from_draft":
                details = ev.get("details") or {}
                if not isinstance(details, dict):
                    details = {}
                latest_build = {
                    "timestamp": ev.get("timestamp"),
                    "crate_id": details.get("crate_id"),
                    "upload_id": details.get("upload_id"),
                }
                break

        items.append(
            {
                "draft_id": draft_id,
                "model_type": model_type,
                "status": status,
                "upload_id": upload_id,
                "owner_orcid": draft_obj.get("owner_orcid"),
                "model_name": model_name,
                "model_version": model_version,
                "updated_at": audit_obj.get("updated_at"),
                "created_at": audit_obj.get("created_at"),
                "latest_build": latest_build,
            }
        )

    items.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return items[: max(1, min(limit, 200))]