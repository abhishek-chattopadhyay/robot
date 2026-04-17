from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException

from pbpk_backend.api._config import cfg
from pbpk_backend.api.auth import get_current_user
from pbpk_backend.models.user import User
from pbpk_backend.services import drafts as draft_svc
from pbpk_backend.services.draft_apply import (
    apply_patch_to_draft,
    apply_edits_to_draft,
    apply_array_op_to_draft,
)

router = APIRouter(prefix="/v1/drafts", tags=["drafts"])


def _cfg(model_type: str = "pbpk"):
    return cfg(model_type)


def _assert_owner(cfg_obj, draft_id: str, user: User) -> None:
    try:
        draft_svc.require_draft_owner(cfg_obj, draft_id=draft_id, owner_orcid=user.orcid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this draft")


@router.post("")
def api_create_draft(
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    model_type = body.get("model_type", "pbpk")
    cfg_obj = _cfg(model_type)

    if "metadata" in body:
        metadata = body.get("metadata")
        upload_id = body.get("upload_id")
    else:
        metadata = body
        upload_id = None

    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")

    try:
        return draft_svc.create_draft(
            cfg_obj,
            metadata=metadata,
            upload_id=upload_id,
            owner_orcid=user.orcid,
            model_type=model_type,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{draft_id}")
def api_get_draft(
    draft_id: str,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)

    try:
        env = draft_svc.get_draft(base_cfg, draft_id=draft_id)
        return env
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{draft_id}")
def api_replace_draft(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)
    current = draft_svc.get_draft(base_cfg, draft_id=draft_id)
    cfg_obj = _cfg(current.get("model_type", "pbpk"))

    if "metadata" in body:
        metadata = body.get("metadata")
        upload_id = body.get("upload_id")
    else:
        metadata = body
        upload_id = None

    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="metadata must be a JSON object")

    try:
        return draft_svc.replace_draft(
            cfg_obj,
            draft_id=draft_id,
            metadata=metadata,
            upload_id=upload_id,
            actor_orcid=user.orcid,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{draft_id}")
def api_patch_draft(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)
    current = draft_svc.get_draft(base_cfg, draft_id=draft_id)
    cfg_obj = _cfg(current.get("model_type", "pbpk"))

    patch = body.get("patch")
    if not isinstance(patch, list):
        raise HTTPException(status_code=400, detail="patch must be a list of operations")

    try:
        return draft_svc.patch_draft(cfg_obj, draft_id=draft_id, patch_ops=patch, actor_orcid=user.orcid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/validate")
def api_validate_draft(
    draft_id: str,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)
    current = draft_svc.get_draft(base_cfg, draft_id=draft_id)
    cfg_obj = _cfg(current.get("model_type", "pbpk"))

    try:
        return draft_svc.validate_draft(cfg_obj, draft_id=draft_id, actor_orcid=user.orcid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/build")
def api_build_from_draft(
    draft_id: str,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)
    current = draft_svc.get_draft(base_cfg, draft_id=draft_id)
    cfg_obj = _cfg(current.get("model_type", "pbpk"))

    try:
        envelope, build_result = draft_svc.build_from_draft(cfg_obj, draft_id=draft_id, actor_orcid=user.orcid)
        return {"ok": True, "draft": envelope, "build": build_result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/apply")
def api_apply_patch(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)
    current = draft_svc.get_draft(base_cfg, draft_id=draft_id)
    cfg_obj = _cfg(current.get("model_type", "pbpk"))

    patch = body.get("patch")
    if not isinstance(patch, list):
        raise HTTPException(status_code=400, detail="patch must be a list of operations")

    try:
        return apply_patch_to_draft(cfg_obj, draft_id=draft_id, patch_ops=patch)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/apply-edits")
def api_apply_edits(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)
    current = draft_svc.get_draft(base_cfg, draft_id=draft_id)
    cfg_obj = _cfg(current.get("model_type", "pbpk"))

    edits = body.get("edits")
    if not isinstance(edits, dict):
        raise HTTPException(status_code=400, detail="edits must be a JSON object")

    try:
        return apply_edits_to_draft(cfg_obj, draft_id=draft_id, edits=edits)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/apply-array")
def api_apply_array(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    base_cfg = _cfg()
    _assert_owner(base_cfg, draft_id, user)
    current = draft_svc.get_draft(base_cfg, draft_id=draft_id)
    cfg_obj = _cfg(current.get("model_type", "pbpk"))

    array_path = body.get("array_path")
    action = body.get("action")
    index = body.get("index")
    value = body.get("value")

    if not isinstance(array_path, str) or not array_path:
        raise HTTPException(status_code=400, detail="array_path must be a non-empty string")
    if not isinstance(action, str) or not action:
        raise HTTPException(status_code=400, detail="action must be a non-empty string")

    try:
        return apply_array_op_to_draft(
            cfg_obj,
            draft_id=draft_id,
            array_path=array_path,
            action=action,
            index=index,
            value=value,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))