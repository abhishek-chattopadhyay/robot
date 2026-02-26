from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException

from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.draft_apply import (
    apply_patch_to_draft,
    apply_edits_to_draft,
    apply_array_op_to_draft,
    DraftApplyError,
)

router = APIRouter(prefix="/v1/drafts", tags=["draft-apply"])


def _cfg() -> OrchestratorConfig:
    repo_root = Path(__file__).resolve().parents[3]  # .../packages/pbpk_backend/api -> repo root
    data_root = Path(os.environ.get("PBPK_DATA_ROOT", str(repo_root / "var"))).resolve()

    schema_path = repo_root / "packages" / "pbpk_validation" / "schemas" / "pbpk-metadata.schema.json"
    template_path = repo_root / "packages" / "pbpk-metadata-spec" / "jsonld" / "pbpk-core-template.jsonld"

    return OrchestratorConfig(
        data_root=data_root,
        schema_path=schema_path,
        template_path=template_path,
    )


@router.post("/{draft_id}/apply")
def api_apply_patch(draft_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Body: {"patch": [ {op,path,value?}, ... ]}
    Returns: updated draft envelope
    """
    cfg = _cfg()
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
def api_apply_edits(draft_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Body: {"edits": {"/path": value, ...}}
    Convention: value=null => remove (if exists)
    Returns: {"patch":[...], "draft":<envelope>, ...}
    """
    cfg = _cfg()
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
def api_apply_array(draft_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Body:
      {
        "array_path": "/.../array",.
        "action": "append|insert|remove_index|replace_index",
        "value": {...},   # required for append/insert/replace_index
        "index": 0        # required for insert/remove_index/replace_index
      }
    Returns: {"patch":[...], "draft":<envelope>, ...}
    """
    cfg = _cfg()
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