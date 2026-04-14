from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


from pbpk_backend.services.form_spec import compile_pbpk_form_registry, compile_form_registry


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _data_root() -> Path:
    rr = _repo_root()
    return Path(os.environ.get("PBPK_DATA_ROOT", str(rr / "var"))).resolve()


def _is_empty_value(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    if isinstance(v, dict) and len(v) == 0:
        return True
    return False


def _parse_pointer(path: str) -> List[str]:
    if not path or not path.startswith("/"):
        return []
    return [p for p in path.split("/") if p]


def _extract_values(metadata: Any, pointer: str) -> List[Any]:
    """
    Returns list of matches. If pointer has no wildcard, the return is typically [value].
    If pointer includes '*', return is flattened across matches.
    """
    parts = _parse_pointer(pointer)
    if not parts:
        return []

    def walk(node: Any, idx: int) -> List[Any]:
        if idx >= len(parts):
            return [node]

        key = parts[idx]

        if key == "*":
            if isinstance(node, list):
                out: List[Any] = []
                for item in node:
                    out.extend(walk(item, idx + 1))
                return out
            return []

        if isinstance(node, dict):
            if key not in node:
                return []
            return walk(node[key], idx + 1)

        return []

    return walk(metadata, 0)


def _unwrap_single_list(values: List[Any]) -> Any:
    """
    If values == [<list>], return <list> to avoid double nesting in cardinality=many fields.
    Otherwise return values as-is.
    """
    if len(values) == 1 and isinstance(values[0], list):
        return values[0]
    return values


def _load_draft_metadata(draft_id: str) -> Dict[str, Any]:
    """
    Tries hard to locate the stored draft on disk without assuming a single layout.

    Searches under PBPK_DATA_ROOT for JSON files whose name contains the draft_id,
    and also common draft locations (var/drafts, var/state, etc).
    """
    root = _data_root()
    search_roots = [
        root / "drafts",
        root / "state",
        root,  # last resort
    ]

    candidates: List[Path] = []

    # Common patterns
    for sr in search_roots:
        if sr.exists():
            candidates.extend(list(sr.glob(f"**/{draft_id}.json")))
            candidates.extend(list(sr.glob(f"**/{draft_id}/*.json")))
            candidates.extend(list(sr.glob(f"**/*{draft_id}*.json")))

    # De-dup + stable order
    seen = set()
    uniq: List[Path] = []
    for p in sorted(candidates, key=lambda x: str(x)):
        if str(p) not in seen and p.is_file():
            uniq.append(p)
            seen.add(str(p))

    for p in uniq:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Draft file could be the draft object itself, or nested.
        if isinstance(obj, dict):
            if obj.get("draft_id") == draft_id and isinstance(obj.get("metadata"), dict):
                return obj["metadata"]

            md = obj.get("metadata")
            if isinstance(md, dict) and obj.get("draft_id") in (draft_id, None):
                # accept metadata payload if it's obviously a draft container
                return md

    raise FileNotFoundError(f"Draft not found: {draft_id} (searched under {root})")


def hydrate_pbpk_form(*, metadata: Dict[str, Any], include_helptexts: bool = False) -> Dict[str, Any]:
    reg = compile_pbpk_form_registry(include_helptexts=include_helptexts, include_vocabularies=True)
    fields_by_path: Dict[str, Dict[str, Any]] = reg["registry"]["fields_by_path"]

    hydrated: List[Dict[str, Any]] = []

    for path, fdef in fields_by_path.items():
        values = _extract_values(metadata, path)

        has_wildcard = "/*/" in path or path.endswith("/*")
        cardinality = fdef.get("cardinality", "one")
        required = bool(fdef.get("required", False))

        # Output rules:
        # - If wildcard OR cardinality=many => output list-like value
        # - Else output scalar
        if has_wildcard or cardinality == "many":
            value_out: Any = _unwrap_single_list(values)
            missing = required and _is_empty_value(value_out)
        else:
            value_out = values[0] if values else None
            missing = required and _is_empty_value(value_out)

        hydrated.append(
            {
                "key": fdef.get("key"),
                "path": path,
                "section_id": fdef.get("section_id"),
                "id": fdef.get("id"),
                "label": fdef.get("label"),
                "description": fdef.get("description"),
                "value_type": fdef.get("value_type"),
                "required": required,
                "cardinality": cardinality,
                "allowed_values": fdef.get("allowed_values"),
                "vocabulary": fdef.get("vocabulary"),
                "value": value_out,
                "missing": bool(missing),
            }
        )

    hydrated.sort(key=lambda x: (str(x.get("section_id") or ""), str(x.get("path") or "")))

    return {
        "api_version": "v1",
        "kind": "pbpk.form_hydration",
        "fields": hydrated,
        "registry_issues": reg["registry"].get("issues", []),
    }


def hydrate_pbpk_form_from_draft(*, draft_id: str, include_helptexts: bool = False) -> Dict[str, Any]:
    md = _load_draft_metadata(draft_id)
    out = hydrate_pbpk_form(metadata=md, include_helptexts=include_helptexts)
    out["draft_id"] = draft_id
    return out


def _restructure_qaop_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-process qAOP metadata so that virtual paths (_mie, _key_events, _ao)
    can be resolved by the standard _extract_values walker.

    The form spec uses:
      /structure/_mie/...         -> the KE with role="mie"
      /structure/_key_events/*/.. -> KEs with role="key_event"
      /structure/_ao/...          -> the KE with role="ao"

    But actual metadata stores everything in structure.key_events[] with a role field.
    This function splits key_events by role into _mie, _key_events, _ao.
    """
    out = {}
    for k, v in metadata.items():
        if k == "structure" and isinstance(v, dict):
            s = dict(v)
            key_events = s.get("key_events", [])

            mie = None
            ao = None
            kes: List[Dict[str, Any]] = []

            for ke in key_events:
                if not isinstance(ke, dict):
                    continue
                role = ke.get("role", "key_event")
                if role == "mie":
                    mie = ke
                elif role == "ao":
                    ao = ke
                else:
                    kes.append(ke)

            s["_mie"] = mie or {}
            s["_key_events"] = kes
            s["_ao"] = ao or {}
            out["structure"] = s
        else:
            out[k] = v
    return out


def hydrate_qaop_form(*, metadata: Dict[str, Any], include_helptexts: bool = False) -> Dict[str, Any]:
    reg = compile_form_registry(model_type="qaop", include_helptexts=include_helptexts, include_vocabularies=True)
    fields_by_path: Dict[str, Dict[str, Any]] = reg["registry"]["fields_by_path"]

    # Restructure metadata so virtual paths resolve
    rmd = _restructure_qaop_metadata(metadata)

    hydrated: List[Dict[str, Any]] = []

    for path, fdef in fields_by_path.items():
        values = _extract_values(rmd, path)

        has_wildcard = "/*/" in path or path.endswith("/*")
        cardinality = fdef.get("cardinality", "one")
        required = bool(fdef.get("required", False))

        if has_wildcard or cardinality == "many":
            value_out: Any = _unwrap_single_list(values)
            missing = required and _is_empty_value(value_out)
        else:
            value_out = values[0] if values else None
            missing = required and _is_empty_value(value_out)

        hydrated.append(
            {
                "key": fdef.get("key"),
                "path": path,
                "section_id": fdef.get("section_id"),
                "id": fdef.get("id"),
                "label": fdef.get("label"),
                "description": fdef.get("description"),
                "value_type": fdef.get("value_type"),
                "required": required,
                "cardinality": cardinality,
                "allowed_values": fdef.get("allowed_values"),
                "vocabulary": fdef.get("vocabulary"),
                "value": value_out,
                "missing": bool(missing),
            }
        )

    hydrated.sort(key=lambda x: (str(x.get("section_id") or ""), str(x.get("path") or "")))

    return {
        "api_version": "v1",
        "kind": "qaop.form_hydration",
        "fields": hydrated,
        "registry_issues": reg["registry"].get("issues", []),
    }


def hydrate_qaop_form_from_draft(*, draft_id: str, include_helptexts: bool = False) -> Dict[str, Any]:
    md = _load_draft_metadata(draft_id)
    out = hydrate_qaop_form(metadata=md, include_helptexts=include_helptexts)
    out["draft_id"] = draft_id
    return out