from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pbpk_validation.validator import validate_pbpk_metadata


@dataclass
class Suggestion:
    op: str
    path: str
    value: Any


@dataclass
class Question:
    id: str
    path: str
    question: str


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _repo_root() -> Path:
    # engine.py -> packages/pbpk_ai_assistant/engine.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[2]


def _default_schema_path() -> Path:
    rr = _repo_root()
    return rr / "packages" / "pbpk_validation" / "schemas" / "pbpk-metadata.schema.json"


def _lint_warnings(metadata: Dict[str, Any], schema_path: Optional[Path] = None) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Reuse the same validator as the backend.
    Returns (errors, warnings) in the same shape as validate_pbpk_metadata uses.
    """
    sp = schema_path or _default_schema_path()
    errors, warnings = validate_pbpk_metadata(metadata, schema_path=sp)
    return errors, warnings


def _missing_required_from_schema_errors(errors: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Convert jsonschema errors into a 'missing_required' list.
    We keep it simple: any error becomes a missing/invalid item the user should address.
    """
    missing: List[Dict[str, str]] = []
    for e in errors:
        missing.append({"path": e.get("path", "/"), "message": e.get("message", "Invalid or missing value.")})
    return missing


def _questions_from_issues(missing_required: List[Dict[str, str]], warnings: List[Dict[str, str]]) -> List[Question]:
    """
    Deterministic question generation (no LLM required).
    For v1, we produce short questions for the most important issues.
    """
    questions: List[Question] = []

    # Ask about missing/invalid required first
    for i, m in enumerate(missing_required[:10], start=1):
        questions.append(
            Question(
                id=f"req_{i}",
                path=m["path"],
                question=f"Please provide a value for {m['path']} (required).",
            )
        )

    # Then soft warnings that are actionable
    for i, w in enumerate([w for w in warnings if w.get("code")][:10], start=1):
        code = w.get("code", "W")
        path = w.get("path", "/")
        if code == "W6":
            questions.append(
                Question(
                    id=f"{code.lower()}_{i}",
                    path=path,
                    question="Do you have evaluation dataset details or a reference you can add for this evaluation activity?",
                )
            )
        else:
            questions.append(
                Question(
                    id=f"{code.lower()}_{i}",
                    path=path,
                    question=f"Can you address warning {code} at {path}?",
                )
            )

    return questions


def _patches_from_warnings(metadata: Dict[str, Any], warnings: List[Dict[str, str]]) -> List[Suggestion]:
    """
    Produce SAFE JSON Patch suggestions.
    Rule: never invent factual content. We only add placeholders that prompt the user,
    or structure that is clearly missing and non-factual.
    """
    patches: List[Suggestion] = []
    for w in warnings:
        if w.get("code") == "W6":
            # We can suggest adding an empty string or template text.
            # But better is to suggest a placeholder note rather than fake a DOI.
            path = w.get("path", "")
            if path:
                patches.append(
                    Suggestion(
                        op="add",
                        path=path,
                        value="TODO: add evaluation dataset details or a persistent reference (DOI/URL).",
                    )
                )
    return patches


def suggest(
    *,
    metadata: Dict[str, Any],
    schema_path: Optional[Path] = None,
    draft_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main entrypoint for /ai/suggest (v1).
    Returns a structured response that the frontend can act on.
    """
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object")

    errors, warnings = _lint_warnings(metadata, schema_path=schema_path)
    missing_required = _missing_required_from_schema_errors(errors)

    questions = _questions_from_issues(missing_required, warnings)
    patches = _patches_from_warnings(metadata, warnings) if not errors else []

    return {
        "api_version": "v1",
        "kind": "pbpk.ai.suggestions",
        "draft_id": draft_id,
        "missing_required": missing_required,
        "soft_warnings": warnings,
        "suggested_patches": [{"op": p.op, "path": p.path, "value": p.value} for p in patches],
        "clarifying_questions": [{"id": q.id, "path": q.path, "question": q.question} for q in questions],
    }


def explain(*, field_id: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
    """
    Minimal helptext endpoint.
    For v1, we return:
      - examples
      - Tan 2020 excerpts
    Later: map field_id/path -> specific section/field help.
    """
    rr = _repo_root()
    help_dir = rr / "packages" / "pbpk-form-spec" / "helptexts"

    examples_md = ""
    excerpts_md = ""
    if (help_dir / "examples.md").exists():
        examples_md = _load_text(help_dir / "examples.md")
    if (help_dir / "tan2020-excerpts.md").exists():
        excerpts_md = _load_text(help_dir / "tan2020-excerpts.md")

    return {
        "api_version": "v1",
        "kind": "pbpk.ai.explain",
        "field_id": field_id,
        "path": path,
        "helptexts": {
            "examples_md": examples_md,
            "tan2020_excerpts_md": excerpts_md,
        },
    }