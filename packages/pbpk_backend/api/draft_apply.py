from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from pbpk_backend.api.auth import get_current_user
from pbpk_backend.models.user import User
from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.draft_apply import (
    apply_patch_to_draft,
    apply_edits_to_draft,
    apply_array_op_to_draft,
    DraftApplyError,
)
from pbpk_backend.services.drafts import require_draft_owner

router = APIRouter(prefix="/v1/drafts", tags=["draft-apply"])


def _cfg() -> OrchestratorConfig:
    repo_root = Path(__file__).resolve().parents[3]
    data_root = Path(os.environ.get("PBPK_DATA_ROOT", str(repo_root / "var"))).resolve()

    schema_path = repo_root / "packages" / "pbpk_validation" / "schemas" / "pbpk-metadata.schema.json"
    template_path = repo_root / "packages" / "pbpk-metadata-spec" / "jsonld" / "pbpk-core-template.jsonld"

    return OrchestratorConfig(
        data_root=data_root,
        schema_path=schema_path,
        template_path=template_path,
    )


def _assert_owner(cfg: OrchestratorConfig, draft_id: str, user: User) -> None:
    try:
        require_draft_owner(cfg, draft_id=draft_id, owner_orcid=user.orcid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this draft")


@router.post("/{draft_id}/apply")
def api_apply_patch(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    cfg = _cfg()
    _assert_owner(cfg, draft_id, user)

    patch = body.get("patch")
    if not isinstance(patch, list):
        raise HTTPException(status_code=400, detail="patch must be a list of operations")

    try:
        return apply_patch_to_draft(cfg, draft_id=draft_id, patch_ops=patch)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except (DraftApplyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/apply-edits")
def api_apply_edits(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    cfg = _cfg()
    _assert_owner(cfg, draft_id, user)

    edits = body.get("edits")
    if not isinstance(edits, dict):
        raise HTTPException(status_code=400, detail="edits must be a JSON object")

    try:
        return apply_edits_to_draft(cfg, draft_id=draft_id, edits=edits)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except (DraftApplyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/apply-array")
def api_apply_array(
    draft_id: str,
    body: Dict[str, Any] = Body(...),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    cfg = _cfg()
    _assert_owner(cfg, draft_id, user)

    array_path: Optional[str] = body.get("array_path")
    action: Optional[str] = body.get("action")
    value = body.get("value")
    index = body.get("index")

    if not isinstance(array_path, str) or not array_path.startswith("/"):
        raise HTTPException(status_code=400, detail="array_path must be a JSON pointer starting with '/'")
    if not isinstance(action, str) or not action:
        raise HTTPException(status_code=400, detail="action is required")
    if index is not None and not isinstance(index, int):
        raise HTTPException(status_code=400, detail="index must be an integer")

    try:
        return apply_array_op_to_draft(
            cfg,
            draft_id=draft_id,
            array_path=array_path,
            action=action,
            value=value,
            index=index,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except (DraftApplyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))