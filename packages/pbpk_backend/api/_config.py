"""Centralized configuration for API layer.

Resolves schema_path and template_path based on model_type,
replacing duplicated _cfg() functions across API modules.
"""

from __future__ import annotations

import os
from pathlib import Path

from pbpk_backend.services.orchestrator import OrchestratorConfig


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


_MODEL_CONFIG = {
    "pbpk": {
        "schema_path": lambda root: root / "packages" / "pbpk_validation" / "schemas" / "pbpk-metadata.schema.json",
        "template_path": lambda root: root / "packages" / "pbpk-metadata-spec" / "jsonld" / "pbpk-core-template.jsonld",
    },
    "qaop": {
        "schema_path": lambda root: root / "packages" / "qaop_validation" / "schemas" / "qaop-metadata.schema.json",
        "template_path": lambda root: root / "packages" / "qaop-metadata-spec" / "jsonld" / "qaop-core-template.jsonld",
    },
}


def cfg(model_type: str = "pbpk") -> OrchestratorConfig:
    """Return OrchestratorConfig for the given model type."""
    repo_root = _repo_root()
    data_root = Path(os.environ.get("PBPK_DATA_ROOT", str(repo_root / "var"))).resolve()

    config = _MODEL_CONFIG.get(model_type)
    if config is None:
        raise ValueError(f"Unknown model_type: {model_type!r}")

    return OrchestratorConfig(
        data_root=data_root,
        schema_path=config["schema_path"](repo_root),
        template_path=config["template_path"](repo_root),
    )
