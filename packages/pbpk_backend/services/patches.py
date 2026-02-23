from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pbpk_backend.services.hydrate import _parse_pointer  # reuse pointer parsing


def _get_at_pointer(doc: Any, pointer: str) -> Tuple[bool, Any]:
    """
    Returns (exists, value) for a JSON-pointer-like path without wildcards.
    If wildcard '*' is in pointer, we report exists=False (v1).
    """
    parts = _parse_pointer(pointer)
    if any(p == "*" for p in parts):
        return (False, None)

    node = doc
    for i, key in enumerate(parts):
        if not isinstance(node, dict):
            return (False, None)
        if key not in node:
            return (False, None)
        node = node[key]
    return (True, node)


def _is_effectively_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    if isinstance(v, dict) and len(v) == 0:
        return True
    return False


def build_json_patch_from_edits(*, metadata: Dict[str, Any], edits: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    edits maps absolute JSON pointer (e.g. "/general_model_information/model_name") -> desired value.
    Returns a JSON Patch list.
    """
    patch: List[Dict[str, Any]] = []

    for path, value in edits.items():
        if not isinstance(path, str) or not path.startswith("/"):
            continue
        # v1: disallow wildcard edits through this endpoint
        if "/*" in path:
            continue

        exists, _old = _get_at_pointer(metadata, path)

        if _is_effectively_empty(value):
            if exists:
                patch.append({"op": "remove", "path": path})
            continue

        if exists:
            patch.append({"op": "replace", "path": path, "value": value})
        else:
            patch.append({"op": "add", "path": path, "value": value})

    return patch