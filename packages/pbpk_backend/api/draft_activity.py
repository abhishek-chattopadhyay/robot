from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from pbpk_backend.api.auth import get_current_user
from pbpk_backend.models.user import User
from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.draft_activity import get_draft_activity
from pbpk_backend.services.drafts import require_draft_owner

router = APIRouter(prefix="/v1/drafts", tags=["draft-activity"])


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


@router.get("/{draft_id}/activity")
def api_draft_activity(
    draft_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    cfg = _cfg()

    try:
        require_draft_owner(cfg, draft_id=draft_id, owner_orcid=user.orcid)
        out = get_draft_activity(data_root=cfg.data_root, draft_id=draft_id, limit=limit)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this draft")

    return {
        "api_version": "v1",
        "kind": "pbpk.draft_activity",
        **out,
    }