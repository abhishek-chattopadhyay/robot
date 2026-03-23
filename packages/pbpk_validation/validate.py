#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from jsonschema import Draft202012Validator

# Local (same folder) lint rules for soft warnings (domain payload)
from lint_rules import lint as lint_domain

# RO-Crate validators
from rocrate_lint import validate_rocrate
from rocrate_validation.validator import validate_rocrate_base


ROOT = Path(__file__).resolve().parents[1]  # packages/
PKG = ROOT / "pbpk-validation"
DEFAULT_SCHEMA = PKG / "schemas" / "pbpk-metadata.schema.json"


@dataclass
class Issue:
    level: str  # "ERROR" or "WARNING"
    message: str
    path: str


def _json_pointer_path(error_path: List[Any]) -> str:
    if not error_path:
        return "/"
    return "/" + "/".join(str(p) for p in error_path)


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


def run_domain_validation(input_path: Path, schema_path: Path) -> int:
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

    # Soft validation: lint warnings
    warnings = lint_domain(instance)
    if warnings:
        print("PBPK metadata validation PASSED (with warnings)\n")
        print("Soft warnings")
        for i, w in enumerate(warnings, start=1):
            print(f"{i}. [{w.code}] {w.path}: {w.message}")
        return 0

    print("PBPK metadata validation PASSED")
    return 0


def run_rocrate_validation(input_path: Path, crate_dir: Optional[Path]) -> int:
    try:
        rocrate = load_json(input_path)
    except Exception as e:
        return die(str(e), 2)

    # Base RO-Crate 1.1 spec check (requires crate directory)
    base_errors: List[Any] = []
    if crate_dir is not None:
        raw_base_errors, _ = validate_rocrate_base(crate_dir)
        base_errors = raw_base_errors

    # PBPK domain-specific checks
    domain_issues = validate_rocrate(rocrate)
    domain_errors = [x for x in domain_issues if x.level == "ERROR"]
    warns = [x for x in domain_issues if x.level == "WARNING"]

    if base_errors or domain_errors:
        print("RO-Crate validation FAILED\n")
        for i, e in enumerate(base_errors, start=1):
            print(f"{i}. [SPEC] {e['code']}: {e['message']}")
        offset = len(base_errors)
        for i, e in enumerate(domain_errors, start=offset + 1):
            print(f"{i}. [PBPK] {e.code} {e.node_id}: {e.message}")
        if warns:
            print("\nWarnings")
            for i, w in enumerate(warns, start=1):
                print(f"{i}. [{w.code}] {w.node_id}: {w.message}")
        return 1

    if warns:
        print("RO-Crate validation PASSED (with warnings)\n")
        for i, w in enumerate(warns, start=1):
            print(f"{i}. [{w.code}] {w.node_id}: {w.message}")
        return 0

    print("RO-Crate validation PASSED")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pbpk-validate",
        description="Validate PBPK metadata payloads (JSON Schema + soft lint) or PBPK RO-Crates (graph-aware checks).",
    )
    parser.add_argument(
        "--mode",
        choices=["metadata", "rocrate"],
        default="metadata",
        help="Validation mode: 'metadata' for domain payload JSON (default), 'rocrate' for RO-Crate JSON-LD metadata.",
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input JSON file path. For mode=metadata: pbpk-metadata.json. For mode=rocrate: ro-crate-metadata.json",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=str(DEFAULT_SCHEMA),
        help=f"(metadata mode) Path to JSON Schema (default: {DEFAULT_SCHEMA})",
    )
    parser.add_argument(
        "--crate-dir",
        type=str,
        default=None,
        help="(rocrate mode) Path to the crate directory. Required to run the base RO-Crate 1.1 spec check.",
    )

    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()

    if args.mode == "metadata":
        schema_path = Path(args.schema).resolve()
        return run_domain_validation(input_path=input_path, schema_path=schema_path)

    # mode == rocrate
    crate_dir = Path(args.crate_dir).resolve() if args.crate_dir else None
    if crate_dir is not None and not crate_dir.exists():
        return die(f"--crate-dir does not exist: {crate_dir}", 2)

    return run_rocrate_validation(input_path=input_path, crate_dir=crate_dir)


if __name__ == "__main__":
    raise SystemExit(main())