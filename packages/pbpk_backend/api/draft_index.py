from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Query

from pbpk_backend.api._config import cfg
from pbpk_backend.services.draft_index import list_drafts_with_activity

router = APIRouter(prefix="/v1/drafts", tags=["draft-index"])


@router.get("")
def api_list_drafts(
    limit: int = Query(default=20, ge=1, le=200),
    include_archived: bool = Query(default=False),
) -> Dict[str, Any]:
    c = cfg()
    items = list_drafts_with_activity(
        data_root=c.data_root,
        limit=limit,
        include_archived=include_archived,
    )
    return {
        "api_version": "v1",
        "kind": "pbpk.draft_index",
        "count": len(items),
        "items": items,
    }