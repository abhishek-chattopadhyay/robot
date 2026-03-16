from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from pbpk_backend.services.deposit_history import list_deposit_history


def list_recent_deposits(
    *,
    data_root: Path,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    items = list_deposit_history(data_root=data_root, crate_id=None, limit=5000)
    items.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return items[: max(1, min(limit, 200))]