from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from pbpk_backend.services.array_ops import build_array_patch
from pbpk_backend.services.hydrate import _load_draft_metadata

router = APIRouter(prefix="/v1/form-spec", tags=["form-array-ops"])


@router.post("/pbpk/array-ops")
def api_pbpk_array_ops(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Build JSON Patch ops for array operations on a draft.

    Example:
    {
      "draft_id": "draft_...",
      "array_path": "/model_evaluation_and_validation/evaluation_activities",
      "action": "append",
      "value": { ... }
    }
    """
    draft_id = body.get("draft_id")
    array_path = body.get("array_path")
    action = body.get("action")
    index = body.get("index", None)
    value = body.get("value", None)

    if not isinstance(draft_id, str) or not draft_id:
        raise HTTPException(status_code=400, detail="draft_id is required")
    if not isinstance(array_path, str) or not array_path.startswith("/"):
        raise HTTPException(status_code=400, detail="array_path must be a JSON pointer")
    if not isinstance(action, str) or not action:
        raise HTTPException(status_code=400, detail="action is required")

    if index is not None and not isinstance(index, int):
        raise HTTPException(status_code=400, detail="index must be an integer when provided")

    try:
        md = _load_draft_metadata(draft_id)
        patch = build_array_patch(
            metadata=md,
            array_path=array_path,
            action=action,
            index=index,
            value=value,
        )
        return {
            "api_version": "v1",
            "kind": "pbpk.json_patch",
            "draft_id": draft_id,
            "patch": patch,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))