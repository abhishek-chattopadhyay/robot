from __future__ import annotations

from fastapi import APIRouter, HTTPException

from pbpk_backend.services.templates import get_template, list_templates

router = APIRouter(prefix="/v1/form-spec/pbpk/templates", tags=["form-templates"])


@router.get("")
def api_list_templates():
    return list_templates()


@router.get("/{name}")
def api_get_template(name: str):
    try:
        return get_template(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown template: {name}")