from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException, Query

from pbpk_backend.services.form_spec import compile_pbpk_form_spec

router = APIRouter(prefix="/v1/form-spec", tags=["form-spec"])


@router.get("/pbpk")
def get_pbpk_form_spec(
    include_helptexts: bool = Query(False, description="Include helptexts/*.md content inline"),
    include_vocabularies: bool = Query(False, description="Include pbpk-metadata-spec/vocabularies/*.yaml inline"),
) -> Dict:
    try:
        return compile_pbpk_form_spec(
            include_helptexts=include_helptexts,
            include_vocabularies=include_vocabularies,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        # e.g. missing PyYAML
        raise HTTPException(status_code=500, detail=str(e))