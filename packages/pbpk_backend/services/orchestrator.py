from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pbpk_backend.rocrate_builder import build_rocrate_from_pbpk_metadata
from pbpk_deposition.base import get_depositor
from pbpk_validation.validator import validate_pbpk_metadata, validate_pbpk_rocrate


@dataclass
class OrchestratorConfig:
    data_root: Path
    schema_path: Path
    template_path: Path


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def validate_metadata(cfg: OrchestratorConfig, pbpk_metadata: Dict[str, Any]) -> Dict[str, Any]:
    errors, warnings = validate_pbpk_metadata(pbpk_metadata, schema_path=cfg.schema_path)
    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def build_crate(
    cfg: OrchestratorConfig,
    pbpk_metadata: Dict[str, Any],
    *,
    source_files_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    crate_id = _new_id("crate")
    crate_dir = (cfg.data_root / "crates" / crate_id).resolve()
    crate_dir.mkdir(parents=True, exist_ok=True)

    # Persist payload for provenance/debug
    _write_json(crate_dir / "pbpk-metadata.json", pbpk_metadata)

    res = build_rocrate_from_pbpk_metadata(
        pbpk_metadata=pbpk_metadata,
        crate_dir=crate_dir,
        template_path=cfg.template_path,
        source_files_dir=source_files_dir,
    )

    # Validate crate after build (recommended)
    rocrate_obj = json.loads((crate_dir / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    c_errors, c_warnings = validate_pbpk_rocrate(rocrate_obj, crate_dir=crate_dir)

    return {
        "crate_id": crate_id,
        "crate_dir": str(crate_dir),
        "metadata_path": str(res.metadata_path),
        "validation": {"ok": len(c_errors) == 0, "errors": c_errors, "warnings": c_warnings},
    }


def validate_crate(cfg: OrchestratorConfig, crate_id: str) -> Dict[str, Any]:
    crate_dir = (cfg.data_root / "crates" / crate_id).resolve()
    meta_path = crate_dir / "ro-crate-metadata.json"
    if not meta_path.exists():
        return {"ok": False, "errors": [{"code": "E_NOT_FOUND", "message": "ro-crate-metadata.json not found"}], "warnings": []}

    rocrate_obj = json.loads(meta_path.read_text(encoding="utf-8"))
    errors, warnings = validate_pbpk_rocrate(rocrate_obj, crate_dir=crate_dir)
    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def deposit_crate(
    cfg: OrchestratorConfig,
    *,
    crate_id: str,
    platform: str,
    token: str,
    sandbox: bool = False,
    publish: bool = False,
) -> Dict[str, Any]:
    crate_dir = (cfg.data_root / "crates" / crate_id).resolve()
    meta_path = crate_dir / "ro-crate-metadata.json"
    if not meta_path.exists():
        return {"ok": False, "error": "ro-crate-metadata.json not found"}

    depositor_cls = get_depositor(platform)
    depositor = depositor_cls()

    res = depositor.deposit(
        crate_dir=crate_dir,
        metadata_path=meta_path,
        access_token=token,
        sandbox=sandbox,
        publish=publish,
    )

    return {
        "ok": res.ok,
        "platform": res.platform,
        "record_id": res.record_id,
        "doi": res.doi,
        "url": res.url,
        "message": res.message,
    }