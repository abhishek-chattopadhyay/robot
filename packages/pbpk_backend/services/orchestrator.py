from __future__ import annotations

from pbpk_backend.services.audit import AuditContext, audit_upload_event, audit_crate_event, audit_deposit_event_jsonl

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from pbpk_backend.rocrate_builder import build_rocrate_from_pbpk_metadata
from pbpk_deposition.base import get_depositor
from rocrate_validation.validator import validate_rocrate_base
from pbpk_validation.validator import validate_pbpk_metadata
from pbpk_validation.validator import validate_rocrate_domain as validate_pbpk_domain
import pbpk_deposition.zenodo  # noqa: F401

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

    _write_json(crate_dir / "pbpk-metadata.json", pbpk_metadata)

    res = build_rocrate_from_pbpk_metadata(
        pbpk_metadata=pbpk_metadata,
        crate_dir=crate_dir,
        template_path=cfg.template_path,
        source_files_dir=source_files_dir,
    )

    rocrate_obj = json.loads((crate_dir / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    base_errors, base_warns = validate_rocrate_base(crate_dir)
    domain_errors, domain_warns = validate_pbpk_domain(rocrate_obj, crate_dir=crate_dir)
    c_errors = base_errors + domain_errors
    c_warnings = base_warns + domain_warns

    return {
        "crate_id": crate_id,
        "crate_dir": str(crate_dir),
        "metadata_path": str(res.metadata_path),
        "validation": {"ok": len(c_errors) == 0, "errors": c_errors, "warnings": c_warnings},
    }


def validate_crate(
    cfg: OrchestratorConfig,
    crate_id: str,
    *,
    layers: set = frozenset({"base", "domain"}),
) -> Dict[str, Any]:
    crate_dir = (cfg.data_root / "crates" / crate_id).resolve()
    meta_path = crate_dir / "ro-crate-metadata.json"
    if not meta_path.exists():
        return {
            "ok": False,
            "errors": [{"code": "E_NOT_FOUND", "message": "ro-crate-metadata.json not found"}],
            "warnings": [],
        }

    errors: list = []
    warnings: list = []

    if "base" in layers:
        base_errors, base_warns = validate_rocrate_base(crate_dir)
        errors += base_errors
        warnings += base_warns

    if "domain" in layers:
        rocrate_obj = json.loads(meta_path.read_text(encoding="utf-8"))
        domain_errors, domain_warns = validate_pbpk_domain(rocrate_obj, crate_dir=crate_dir)
        errors += domain_errors
        warnings += domain_warns

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

    if not crate_dir.exists():
        return {"ok": False, "error": f"crate_id not found: {crate_id}"}

    if not meta_path.exists():
        return {"ok": False, "error": "ro-crate-metadata.json not found"}

    try:
        depositor_cls = get_depositor(platform)
    except KeyError as e:
        return {"ok": False, "error": str(e)}

    depositor = depositor_cls()

    res = depositor.deposit(
        crate_dir=crate_dir,
        metadata_path=meta_path,
        access_token=token,
        sandbox=sandbox,
        publish=publish,
    )

    out = {
        "ok": res.ok,
        "platform": res.platform,
        "record_id": res.record_id,
        "doi": res.doi,
        "url": res.url,
        "bucket_url": res.bucket_url,
        "file_name": res.file_name,
        "published": res.published,
        "message": res.message,
    }

    if res.raw is not None:
        out["raw"] = res.raw

    return out