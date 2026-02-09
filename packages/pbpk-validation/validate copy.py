#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from jsonschema import Draft202012Validator

# Local (same folder) lint rules for soft warnings
from lint_rules import lint


ROOT = Path(__file__).resolve().parents[1]  # packages/
PKG = ROOT / "pbpk-validation"
DEFAULT_SCHEMA = PKG / "schemas" / "pbpk-metadata.schema.json"


@dataclass
class Issue:
    level: str  # "ERROR" or "WARNING"
    message: str
    path: str


def _json_pointer_path(error_path: List[Any]) -> str:
    # Convert jsonschema error.path (deque-like) to a JSON pointer-ish string
    if not error_path:
        return "/"
    parts = []
    for p in error_path:
        parts.append(str(p))
    return "/" + "/".join(parts)


def die(msg: str, code: int = 2) -> int:
    print(f"[ERROR] {msg}", file=sys.stderr)
    return code


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")


def load_schema(schema_path: Path) -> Draft202012Validator:
    schema = load_json(schema_path)
    return Draft202012Validator(schema)


def validate_instance(instance: Any, validator: Draft202012Validator) -> List[Issue]:
    issues: List[Issue] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        issues.append(
            Issue(
                level="ERROR",
                message=err.message,
                path=_json_pointer_path(list(err.path)),
            )
        )
    return issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pbpk-validate",
        description="Validate PBPK metadata payloads (Tan et al. 2020) against JSON Schema (v1), then run soft-warning lint rules.",
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to PBPK metadata JSON (domain payload), e.g. examples/minimal-pbpk-metadata/pbpk-metadata.json",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=str(DEFAULT_SCHEMA),
        help=f"Path to JSON Schema (default: {DEFAULT_SCHEMA})",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    schema_path = Path(args.schema).resolve()

    try:
        instance = load_json(input_path)
    except Exception as e:
        return die(str(e), 2)

    try:
        validator = load_schema(schema_path)
    except Exception as e:
        return die(str(e), 2)

    # Hard validation: JSON Schema
    issues = validate_instance(instance, validator)
    if issues:
        print("PBPK metadata validation FAILED\n")
        for i, issue in enumerate(issues, start=1):
            print(f"{i}. [{issue.level}] {issue.path}: {issue.message}")
        return 1

    # Soft validation: Lint warnings
    warnings = lint(instance)
    if warnings:
        print("PBPK metadata validation PASSED (with warnings)\n")
        print("Soft warnings")
        for i, w in enumerate(warnings, start=1):
            print(f"{i}. [{w.code}] {w.path}: {w.message}")
        return 0

    print("PBPK metadata validation PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
