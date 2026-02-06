#!/usr/bin/env python3
"""
Check consistency between:
- reporting/tan2020-mapping.md
- jsonld/pbpk-context.jsonld
- jsonld/pbpk-core-template.jsonld

Rules:
1) Every pbpk:* property used in mapping.md must be defined in pbpk-context.jsonld.
2) Every pbpk:* property used in template.jsonld must be defined in pbpk-context.jsonld.
3) Report unused pbpk:* context terms (optional hygiene check).

Exit code:
- 0 if consistent
- 1 if missing terms or parse errors
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Set, Tuple

#print("script started")
ROOT = Path(__file__).resolve().parents[1]  # packages/pbpk-metadata-spec
MAPPING_MD = ROOT / "reporting" / "tan2020-mapping.md"
CONTEXT_JSONLD = ROOT / "jsonld" / "pbpk-context.jsonld"
TEMPLATE_JSONLD = ROOT / "jsonld" / "pbpk-core-template.jsonld"

#print("script started")

PBPK_PREFIX = "pbpk:"
PBPK_TERM_RE = re.compile(r"\bpbpk:([A-Za-z_][A-Za-z0-9_]*)\b")


def die(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"File not found: {path}")
    except json.JSONDecodeError as e:
        die(f"Invalid JSON in {path}: {e}")


def extract_pbpk_terms_from_mapping(md_text: str) -> Set[str]:
    # Extract full tokens like "pbpk:hasChemical" from markdown.
    return {f"{PBPK_PREFIX}{m.group(1)}" for m in PBPK_TERM_RE.finditer(md_text)}


def extract_pbpk_terms_from_json(obj: Any) -> Set[str]:
    """
    Extract any pbpk:* strings found as:
    - keys like "pbpk:hasChemical"
    - values like "pbpk:hasChemical" or "pbpk:foo"
    - embedded in strings (rare, but we handle it)
    """
    found: Set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(k, str) and k.startswith(PBPK_PREFIX):
                    found.add(k)
                if isinstance(k, str):
                    for m in PBPK_TERM_RE.finditer(k):
                        found.add(f"{PBPK_PREFIX}{m.group(1)}")
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)
        elif isinstance(x, str):
            for m in PBPK_TERM_RE.finditer(x):
                found.add(f"{PBPK_PREFIX}{m.group(1)}")

    walk(obj)
    return found


def extract_defined_pbpk_terms_from_context(context_jsonld: Dict[str, Any]) -> Set[str]:
    """
    In our context, pbpk terms are defined as:
    "hasChemical": "pbpk:hasChemical"
    i.e., keys are shortnames, values include pbpk:*.
    Also allow keys like "pbpk:hasChemical": "pbpk:hasChemical" (if ever used).
    """
    ctx = context_jsonld.get("@context")
    if ctx is None:
        die(f"{CONTEXT_JSONLD} has no @context.")

    # @context can be a list (we use that) or dict; normalize to list.
    ctx_list = ctx if isinstance(ctx, list) else [ctx]

    defined: Set[str] = set()

    for entry in ctx_list:
        if isinstance(entry, dict):
            for k, v in entry.items():
                # If key itself is pbpk:term
                if isinstance(k, str) and k.startswith(PBPK_PREFIX):
                    defined.add(k)
                # If value is pbpk:term
                if isinstance(v, str) and v.startswith(PBPK_PREFIX):
                    defined.add(v)
                # If value contains pbpk:term inside
                if isinstance(v, str):
                    for m in PBPK_TERM_RE.finditer(v):
                        defined.add(f"{PBPK_PREFIX}{m.group(1)}")

    return defined


def report_set(title: str, items: Set[str]) -> None:
    print(f"\n{title} ({len(items)}):")
    for x in sorted(items):
        print(f"  - {x}")


def main() -> None:
    # Load inputs
    mapping_text = MAPPING_MD.read_text(encoding="utf-8") if MAPPING_MD.exists() else die(
        f"Missing mapping file: {MAPPING_MD}"
    )
    context_jsonld = load_json(CONTEXT_JSONLD)
    template_jsonld = load_json(TEMPLATE_JSONLD)

    # Extract
    mapping_terms = extract_pbpk_terms_from_mapping(mapping_text)
    template_terms = extract_pbpk_terms_from_json(template_jsonld)
    defined_terms = extract_defined_pbpk_terms_from_context(context_jsonld)

    # Check
    missing_in_context = (mapping_terms | template_terms) - defined_terms
    unused_in_context = defined_terms - (mapping_terms | template_terms)

    print("PBPK Context Consistency Check")
    print(f"- mapping:  {MAPPING_MD}")
    print(f"- context:  {CONTEXT_JSONLD}")
    print(f"- template: {TEMPLATE_JSONLD}")

    print("\nSummary")
    print(f"- pbpk terms in mapping:   {len(mapping_terms)}")
    print(f"- pbpk terms in template:  {len(template_terms)}")
    print(f"- pbpk terms in context:   {len(defined_terms)}")
    print(f"- missing in context:      {len(missing_in_context)}")
    print(f"- unused in context:       {len(unused_in_context)}")

    if missing_in_context:
        report_set("Missing pbpk terms (used but not defined in context)", missing_in_context)
        die("Context is missing one or more pbpk:* terms. Please update pbpk-context.jsonld.", 1)

    # Not an error, but useful hygiene output
    if unused_in_context:
        report_set("Unused pbpk terms (defined in context but not used)", unused_in_context)

    print("\n[OK] Context, mapping, and template are consistent.")
    sys.exit(0)


if __name__ == "__main__":
    #print("script started")
    main()