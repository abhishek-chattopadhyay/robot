from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from pbpk_backend.api.auth import get_current_user
from pbpk_backend.models.user import User
from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.deposit_index import list_recent_deposits

router = APIRouter(prefix="/v1/deposits", tags=["deposit-index"])


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


@router.get("")
def api_list_deposits(
    limit: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    cfg = _cfg()
    items = list_recent_deposits(
        data_root=cfg.data_root,
        limit=limit,
        owner_orcid=user.orcid,
    )
    return {
        "api_version": "v1",
        "kind": "pbpk.deposit_index",
        "count": len(items),
        "items": items,
    }