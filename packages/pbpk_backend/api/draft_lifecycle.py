from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.drafts import archive_draft, delete_draft, duplicate_draft

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


@router.post("/{draft_id}/archive")
def api_archive_draft(draft_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    try:
      return archive_draft(cfg, draft_id=draft_id)
    except FileNotFoundError:
      raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/duplicate")
def api_duplicate_draft(draft_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    try:
      return duplicate_draft(cfg, draft_id=draft_id)
    except FileNotFoundError:
      raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{draft_id}")
def api_delete_draft(draft_id: str) -> Dict[str, Any]:
    cfg = _cfg()
    try:
      return delete_draft(cfg, draft_id=draft_id)
    except FileNotFoundError:
      raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e))