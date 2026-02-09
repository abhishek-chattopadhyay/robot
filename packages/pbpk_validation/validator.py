from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator

from .lint_rules import lint as lint_domain
from .rocrate_lint import validate_rocrate


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(schema_path: Path) -> Draft202012Validator:
    schema = load_json(schema_path)
    return Draft202012Validator(schema)


def validate_pbpk_metadata(
    instance: Dict[str, Any],
    *,
    schema_path: Path,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Returns (errors, warnings)
    errors: list of {path, message}
    warnings: list of {code, path, message}
    """
    validator = load_schema(schema_path)

    errors: List[Dict[str, str]] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        path = "/" + "/".join(str(p) for p in err.path) if err.path else "/"
        errors.append({"path": path, "message": err.message})

    warnings: List[Dict[str, str]] = []
    if not errors:
        for w in lint_domain(instance):
            warnings.append({"code": w.code, "path": w.path, "message": w.message})

    return errors, warnings


def validate_pbpk_rocrate(
    rocrate: Dict[str, Any],
    *,
    crate_dir: Optional[Path] = None,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Returns (errors, warnings)
    """
    issues = validate_rocrate(rocrate, crate_dir=crate_dir)
    errors = [{"code": i.code, "node_id": i.node_id, "message": i.message} for i in issues if i.level == "ERROR"]
    warns = [{"code": i.code, "node_id": i.node_id, "message": i.message} for i in issues if i.level == "WARNING"]
    return errors, warns
