from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_jsonl_read(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not path.exists() or not path.is_file():
        return items

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                items.append(obj)
        except Exception:
            continue
    return items


def _candidate_files(data_root: Path) -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()

    explicit = [
        data_root / "audit" / "deposit_events.jsonl",
        data_root / "audit" / "deposit-events.jsonl",
        data_root / "audit" / "deposits.jsonl",
        data_root / "deposit_events.jsonl",
        data_root / "deposit-events.jsonl",
    ]

    for p in explicit:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            candidates.append(p)

    for p in data_root.rglob("*deposit*.jsonl"):
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            candidates.append(p)

    return candidates


def _normalize_event(obj: Dict[str, Any]) -> Dict[str, Any]:
    result = obj.get("result") if isinstance(obj.get("result"), dict) else {}
    request_obj = obj.get("request") if isinstance(obj.get("request"), dict) else {}
    details = obj.get("details") if isinstance(obj.get("details"), dict) else {}

    crate_id = obj.get("crate_id") or details.get("crate_id")
    platform = obj.get("platform") or details.get("platform")
    timestamp = obj.get("timestamp") or obj.get("created_at") or obj.get("time")
    actor = obj.get("actor")

    out = {
        "timestamp": timestamp,
        "crate_id": crate_id,
        "platform": platform,
        "actor": actor,
        "sandbox": request_obj.get("sandbox"),
        "publish_requested": request_obj.get("publish"),
        "ok": result.get("ok") if isinstance(result, dict) else obj.get("ok"),
        "record_id": result.get("record_id") if isinstance(result, dict) else obj.get("record_id"),
        "doi": result.get("doi") if isinstance(result, dict) else obj.get("doi"),
        "url": result.get("url") if isinstance(result, dict) else obj.get("url"),
        "published": result.get("published") if isinstance(result, dict) else obj.get("published"),
        "message": result.get("message") if isinstance(result, dict) else obj.get("message"),
        "raw": obj,
    }
    return out


def list_deposit_history(
    *,
    data_root: Path,
    crate_id: Optional[str] = None,
    platform: Optional[str] = None,
    owner_orcid: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for path in _candidate_files(data_root):
        for obj in _safe_jsonl_read(path):
            item = _normalize_event(obj)

            if crate_id and item.get("crate_id") != crate_id:
                continue
            if platform and item.get("platform") != platform:
                continue
            if owner_orcid and item.get("actor") != owner_orcid:
                continue

            rows.append(item)

    rows.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return rows[: max(1, min(limit, 200))]