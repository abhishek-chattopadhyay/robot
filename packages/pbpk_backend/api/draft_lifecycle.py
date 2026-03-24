from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from pbpk_backend.api.auth import get_current_user
from pbpk_backend.models.user import User
from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.drafts import archive_draft, delete_draft, duplicate_draft, require_draft_owner

router = APIRouter(prefix="/v1/drafts", tags=["draft-lifecycle"])


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


@router.post("/{draft_id}/archive")
def api_archive_draft(draft_id: str, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    cfg = _cfg()
    _assert_owner(cfg, draft_id, user)
    try:
        return archive_draft(cfg, draft_id=draft_id, actor_orcid=user.orcid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/duplicate")
def api_duplicate_draft(draft_id: str, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    cfg = _cfg()
    _assert_owner(cfg, draft_id, user)
    try:
        return duplicate_draft(cfg, draft_id=draft_id, owner_orcid=user.orcid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{draft_id}")
def api_delete_draft(draft_id: str, user: User = Depends(get_current_user)) -> Dict[str, Any]:
    cfg = _cfg()
    _assert_owner(cfg, draft_id, user)
    try:
        return delete_draft(cfg, draft_id=draft_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))