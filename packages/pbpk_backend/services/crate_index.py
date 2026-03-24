from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _safe_count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def list_crates(
    *,
    data_root: Path,
    limit: int = 50,
    owner_orcid: Optional[str] = None,
) -> List[Dict[str, Any]]:
    crates_root = (data_root / "crates").resolve()
    if not crates_root.exists():
        return []

    items: List[Dict[str, Any]] = []

    for d in crates_root.iterdir():
        if not d.is_dir():
            continue

        audit = _safe_read_json(d / "audit.json")
        crate_owner = audit.get("owner_orcid")

        if owner_orcid and crate_owner != owner_orcid:
            continue

        rocrate_path = d / "ro-crate-metadata.json"
        deposit_log = d / "deposit-events.jsonl"

        items.append(
            {
                "crate_id": d.name,
                "crate_dir": str(d),
                "owner_orcid": crate_owner,
                "created_at": audit.get("created_at"),
                "updated_at": audit.get("updated_at"),
                "events": len(audit.get("events") or []) if isinstance(audit, dict) else 0,
                "has_rocrate_metadata": rocrate_path.exists(),
                "deposit_events_count": _safe_count_jsonl(deposit_log),
            }
        )

    items.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return items[: max(1, min(limit, 200))]


def get_crate_owner(*, data_root: Path, crate_id: str) -> Optional[str]:
    crate_dir = (data_root / "crates" / crate_id).resolve()
    if not crate_dir.exists():
        raise FileNotFoundError(crate_id)

    audit = _safe_read_json(crate_dir / "audit.json")
    owner = audit.get("owner_orcid")
    return owner if isinstance(owner, str) and owner else None


def require_crate_owner(*, data_root: Path, crate_id: str, owner_orcid: str) -> None:
    owner = get_crate_owner(data_root=data_root, crate_id=crate_id)
    if owner is None:
        raise PermissionError("Crate has no owner")
    if owner != owner_orcid:
        raise PermissionError("You do not have access to this crate")