from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from jsonschema import Draft202012Validator


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(schema_path: Path) -> Draft202012Validator:
    schema = _load_json(schema_path)
    return Draft202012Validator(schema)


def validate_qaop_metadata(
    instance: Dict[str, Any],
    *,
    schema_path: Path,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Validate qAOP metadata against the JSON Schema.

    Returns (errors, warnings).
    errors: list of {"path": "...", "message": "..."}
    warnings: list of {"code": "...", "path": "...", "message": "..."}

    v1: schema-only validation, no domain lint rules.
    """
    validator = _load_schema(schema_path)

    errors: List[Dict[str, str]] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        path = "/" + "/".join(str(p) for p in err.path) if err.path else "/"
        errors.append({"path": path, "message": err.message})

    # v1: no domain lint rules -- warnings always empty
    warnings: List[Dict[str, str]] = []

    return errors, warnings
