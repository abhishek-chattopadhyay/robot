from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from pbpk_backend.services.hydrate import hydrate_pbpk_form_from_draft
from pbpk_backend.services.patches import build_json_patch_from_edits

router = APIRouter(prefix="/v1/form-spec", tags=["form-patch"])


@router.post("/pbpk/patch")
def api_pbpk_build_patch(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Build JSON Patch ops from simple field edits.

    Expected:
      {
        "draft_id": "draft_...",
        "edits": {
          "/general_model_information/model_name": "New name",
          "/general_model_information/license": "MIT"
        }
      }
    """
    draft_id = body.get("draft_id")
    edits = body.get("edits")

    if not isinstance(draft_id, str) or not draft_id:
        raise HTTPException(status_code=400, detail="draft_id is required")
    if not isinstance(edits, dict):
        raise HTTPException(status_code=400, detail="edits must be an object")

    # Load draft metadata via hydrate (it already knows how to locate draft on disk)
    hydrated = hydrate_pbpk_form_from_draft(draft_id=draft_id)
    # We want the underlying metadata; easiest is to re-load by calling hydrate service internals.
    # Instead: accept that hydration endpoint isn't returning metadata; we load via draft lookup again.
    # We'll just call hydrate again through the service function used by hydrate.
    from pbpk_backend.services.hydrate import _load_draft_metadata  # local import to avoid cycles

    md = _load_draft_metadata(draft_id)

    patch = build_json_patch_from_edits(metadata=md, edits=edits)

    return {
        "api_version": "v1",
        "kind": "pbpk.json_patch",
        "draft_id": draft_id,
        "patch": patch,
    }