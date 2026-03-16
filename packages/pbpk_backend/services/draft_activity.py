from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pbpk_backend.services.deposit_history import list_deposit_history


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _draft_paths(data_root: Path, draft_id: str) -> tuple[Path, Path]:
    draft_dir = (data_root / "drafts" / draft_id).resolve()
    return draft_dir / "draft.json", draft_dir / "audit.json"


def _sort_by_timestamp_desc(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(items, key=lambda x: str(x.get("timestamp") or ""), reverse=True)


def get_draft_activity(
    *,
    data_root: Path,
    draft_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    draft_json, audit_json = _draft_paths(data_root, draft_id)

    if not draft_json.exists():
        raise FileNotFoundError(draft_id)

    draft_obj = _read_json(draft_json)
    audit_obj: Dict[str, Any] = _read_json(audit_json) if audit_json.exists() else {}

    events = audit_obj.get("events", [])
    if not isinstance(events, list):
        events = []

    build_history: List[Dict[str, Any]] = []
    crate_ids: List[str] = []

    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("action") != "build_from_draft":
            continue

        details = ev.get("details", {})
        if not isinstance(details, dict):
            details = {}

        crate_id = details.get("crate_id")
        item = {
            "timestamp": ev.get("timestamp"),
            "crate_id": crate_id,
            "upload_id": details.get("upload_id"),
            "raw": ev,
        }
        build_history.append(item)

        if isinstance(crate_id, str) and crate_id:
            crate_ids.append(crate_id)

    build_history = _sort_by_timestamp_desc(build_history)
    latest_build: Optional[Dict[str, Any]] = build_history[0] if build_history else None

    deposit_history: List[Dict[str, Any]] = []
    seen = set()

    for crate_id in crate_ids:
        if crate_id in seen:
            continue
        seen.add(crate_id)
        deposit_history.extend(
            list_deposit_history(
                data_root=data_root,
                crate_id=crate_id,
                limit=limit,
            )
        )

    deposit_history = _sort_by_timestamp_desc(deposit_history)[: max(1, min(limit, 200))]

    return {
        "draft_id": draft_id,
        "draft_status": draft_obj.get("status"),
        "latest_build": latest_build,
        "build_history": build_history[: max(1, min(limit, 200))],
        "deposit_history": deposit_history,
    }