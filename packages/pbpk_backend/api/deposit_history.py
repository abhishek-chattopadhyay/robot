from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from pbpk_backend.api.auth import get_current_user
from pbpk_backend.models.user import User
from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.deposit_history import list_deposit_history

router = APIRouter(prefix="/v1/deposits", tags=["deposit-history"])


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


@router.get("/history")
def api_deposit_history(
    crate_id: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    cfg = _cfg()
    items = list_deposit_history(
        data_root=cfg.data_root,
        crate_id=crate_id,
        platform=platform,
        owner_orcid=user.orcid,
        limit=limit,
    )
    return {
        "api_version": "v1",
        "kind": "pbpk.deposit_history",
        "crate_id": crate_id,
        "platform": platform,
        "count": len(items),
        "items": items,
    }