from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException

from pbpk_backend.api.orchestrator import _cfg  # reuse cfg resolver
from pbpk_backend.services.drafts import get_draft
from pbpk_ai_assistant.engine import suggest as ai_suggest, explain as ai_explain


router = APIRouter(prefix="/v1/ai", tags=["ai"])


@router.post("/suggest")
def api_ai_suggest(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Accepts either:
      - raw PBPK metadata object
      - {"metadata": <object>, "draft_id": "..."}  (draft_id optional)
      - {"draft_id": "..."}  (loads draft from filesystem)
    """
    cfg = _cfg()

    draft_id: Optional[str] = body.get("draft_id") if isinstance(body, dict) else None

    if isinstance(body, dict) and "draft_id" in body and "metadata" not in body and len(body.keys()) == 1:
        # Load metadata from draft
        try:
            draft = get_draft(cfg, draft_id=body["draft_id"])
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="draft not found")
        metadata = draft.get("metadata", {})
        draft_id = body["draft_id"]
    elif isinstance(body, dict) and "metadata" in body:
        metadata = body["metadata"]
    else:
        metadata = body

    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")

    return ai_suggest(metadata=metadata, draft_id=draft_id)


@router.post("/explain")
def api_ai_explain(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Input:
      {"field_id": "..."} OR {"path": "..."} (either is fine)
    """
    field_id = body.get("field_id")
    path = body.get("path")
    return ai_explain(field_id=field_id, path=path)