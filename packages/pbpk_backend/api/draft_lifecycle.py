from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from pbpk_backend.api._config import cfg
from pbpk_backend.services.drafts import archive_draft, delete_draft, duplicate_draft

router = APIRouter(prefix="/v1/drafts", tags=["draft-lifecycle"])


@router.post("/{draft_id}/archive")
def api_archive_draft(draft_id: str) -> Dict[str, Any]:
    c = cfg()
    try:
      return archive_draft(c, draft_id=draft_id)
    except FileNotFoundError:
      raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/duplicate")
def api_duplicate_draft(draft_id: str) -> Dict[str, Any]:
    c = cfg()
    try:
      return duplicate_draft(c, draft_id=draft_id)
    except FileNotFoundError:
      raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{draft_id}")
def api_delete_draft(draft_id: str) -> Dict[str, Any]:
    c = cfg()
    try:
      return delete_draft(c, draft_id=draft_id)
    except FileNotFoundError:
      raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))