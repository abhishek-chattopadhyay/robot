from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Body, HTTPException, Query

from pbpk_backend.services.form_spec import (
    compile_pbpk_form_spec,
    compile_pbpk_form_registry,
    compile_form_spec,
    compile_form_registry,
)
from pbpk_backend.services.hydrate import (
    hydrate_pbpk_form,
    hydrate_pbpk_form_from_draft,
    hydrate_qaop_form,
    hydrate_qaop_form_from_draft,
)

router = APIRouter(prefix="/v1/form-spec", tags=["form-spec"])


@router.get("/pbpk")
def get_pbpk_form_spec(
    include_helptexts: bool = Query(False, description="Include helptexts/*.md content inline"),
    include_vocabularies: bool = Query(False, description="Include vocabularies inline"),
) -> Dict:
    try:
        return compile_pbpk_form_spec(
            include_helptexts=include_helptexts,
            include_vocabularies=include_vocabularies,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"form-spec error: {e}")


@router.get("/pbpk/registry")
def get_pbpk_form_registry(
    include_helptexts: bool = Query(False, description="Include helptexts/*.md content inline"),
    include_vocabularies: bool = Query(True, description="Include vocabularies and resolve vocabulary refs"),
) -> Dict:
    try:
        return compile_pbpk_form_registry(
            include_helptexts=include_helptexts,
            include_vocabularies=include_vocabularies,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"form-registry error: {e}")


@router.get("/qaop")
def get_qaop_form_spec(
    include_helptexts: bool = Query(False, description="Include helptexts inline"),
    include_vocabularies: bool = Query(False, description="Include vocabularies inline"),
) -> Dict:
    try:
        return compile_form_spec(
            model_type="qaop",
            include_helptexts=include_helptexts,
            include_vocabularies=include_vocabularies,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"qaop form-spec error: {e}")


@router.get("/qaop/registry")
def get_qaop_form_registry(
    include_helptexts: bool = Query(False, description="Include helptexts inline"),
    include_vocabularies: bool = Query(True, description="Include vocabularies and resolve refs"),
) -> Dict:
    try:
        return compile_form_registry(
            model_type="qaop",
            include_helptexts=include_helptexts,
            include_vocabularies=include_vocabularies,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"qaop form-registry error: {e}")


@router.post("/pbpk/hydrate")
def post_pbpk_hydrate(body: Dict = Body(...)) -> Dict:
    """
    Accepts either:
      - {"metadata": {...}}  OR raw metadata payload
      - {"draft_id": "draft_..."}
    Returns a flat list of fields with extracted values and missing flags.
    """
    try:
        include_helptexts = bool(body.get("include_helptexts", False))

        if "draft_id" in body:
            draft_id = body["draft_id"]
            if not isinstance(draft_id, str) or not draft_id:
                raise ValueError("draft_id must be a non-empty string")
            return hydrate_pbpk_form_from_draft(draft_id=draft_id, include_helptexts=include_helptexts)

        md = body.get("metadata")
        if md is None:
            md = body  # allow raw metadata
        if not isinstance(md, dict):
            raise ValueError("metadata must be a JSON object")
        return hydrate_pbpk_form(metadata=md, include_helptexts=include_helptexts)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"hydrate error: {e}")


@router.post("/qaop/hydrate")
def post_qaop_hydrate(body: Dict = Body(...)) -> Dict:
    """
    Accepts either:
      - {"metadata": {...}}  OR raw metadata payload
      - {"draft_id": "draft_..."}
    Returns a flat list of fields with extracted values and missing flags.
    """
    try:
        include_helptexts = bool(body.get("include_helptexts", False))

        if "draft_id" in body:
            draft_id = body["draft_id"]
            if not isinstance(draft_id, str) or not draft_id:
                raise ValueError("draft_id must be a non-empty string")
            return hydrate_qaop_form_from_draft(draft_id=draft_id, include_helptexts=include_helptexts)

        md = body.get("metadata")
        if md is None:
            md = body  # allow raw metadata
        if not isinstance(md, dict):
            raise ValueError("metadata must be a JSON object")
        return hydrate_qaop_form(metadata=md, include_helptexts=include_helptexts)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"qaop hydrate error: {e}")