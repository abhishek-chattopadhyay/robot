from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query

from pbpk_backend.services.form_ui import build_form_ui_pbpk

router = APIRouter(prefix="/v1/form-ui", tags=["form-ui"])


@router.post("/pbpk")
def api_form_ui_pbpk(
    body: Dict[str, Any] = Body(...),
    include_helptexts: bool = Query(False),
    include_vocabularies: bool = Query(True),
) -> Dict[str, Any]:
    try:
        if "draft_id" in body:
            draft_id = body.get("draft_id")
            if not isinstance(draft_id, str) or not draft_id:
                raise ValueError("draft_id must be a non-empty string")
            return build_form_ui_pbpk(
                draft_id=draft_id,
                include_helptexts=include_helptexts,
                include_vocabularies=include_vocabularies,
            )

        md = body.get("metadata", body)
        if not isinstance(md, dict):
            raise ValueError("metadata must be an object")
        return build_form_ui_pbpk(
            metadata=md,
            include_helptexts=include_helptexts,
            include_vocabularies=include_vocabularies,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))