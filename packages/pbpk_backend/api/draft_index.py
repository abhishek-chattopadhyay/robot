from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from pbpk_backend.api._config import cfg
from pbpk_backend.api.auth import get_current_user
from pbpk_backend.models.user import User
from pbpk_backend.services.draft_index import list_drafts_with_activity

router = APIRouter(prefix="/v1/drafts", tags=["draft-index"])


@router.get("")
def api_list_drafts(
    limit: int = Query(default=20, ge=1, le=200),
    include_archived: bool = Query(default=False),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    c = cfg()
    items = list_drafts_with_activity(
        data_root=c.data_root,
        limit=limit,
        include_archived=include_archived,
        owner_orcid=user.orcid,
    )
    return {
        "api_version": "v1",
        "kind": "pbpk.draft_index",
        "count": len(items),
        "items": items,
    }