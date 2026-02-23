from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pbpk_backend.services.hydrate import _parse_pointer


def _get_container_and_key(doc: Any, pointer: str) -> Tuple[bool, Any, str]:
    """
    Returns (ok, parent_container, last_key) for a pointer like /a/b/c.
    parent_container should be a dict, last_key is 'c'.
    """
    parts = _parse_pointer(pointer)
    if not parts:
        return (False, None, "")
    if any(p == "*" for p in parts):
        return (False, None, "")

    parent = doc
    for key in parts[:-1]:
        if not isinstance(parent, dict) or key not in parent:
            return (False, None, "")
        parent = parent[key]
    if not isinstance(parent, dict):
        return (False, None, "")
    return (True, parent, parts[-1])


def _get_array(doc: Any, array_path: str) -> Tuple[bool, List[Any]]:
    ok, parent, key = _get_container_and_key(doc, array_path)
    if not ok:
        return (False, [])
    arr = parent.get(key)
    if arr is None:
        # treat missing array as empty; caller can add it
        return (True, [])
    if not isinstance(arr, list):
        return (False, [])
    return (True, arr)


def build_array_patch(
    *,
    metadata: Dict[str, Any],
    array_path: str,
    action: str,
    index: int | None = None,
    value: Any | None = None,
) -> List[Dict[str, Any]]:
    """
    Build JSON Patch ops for array manipulations.
    """
    if not isinstance(array_path, str) or not array_path.startswith("/"):
        raise ValueError("array_path must be a JSON pointer starting with '/'")
    if "/*" in array_path:
        raise ValueError("array_path must not contain wildcards")

    ok_arr, arr = _get_array(metadata, array_path)
    if not ok_arr:
        raise ValueError("array_path does not point to an array (or is not reachable)")

    patch: List[Dict[str, Any]] = []

    # Ensure array exists if missing (arr==[] but missing in doc)
    # We only add the array container when needed (append/insert).
    ok_parent, parent, key = _get_container_and_key(metadata, array_path)
    if not ok_parent:
        raise ValueError("array_path parent does not exist (create parent objects first)")

    exists_in_doc = isinstance(parent.get(key, None), list)

    if action == "append":
        if value is None:
            raise ValueError("append requires value")
        if not exists_in_doc:
            patch.append({"op": "add", "path": array_path, "value": []})
        patch.append({"op": "add", "path": f"{array_path}/-", "value": value})
        return patch

    if action == "insert_index":
        if value is None:
            raise ValueError("insert_index requires value")
        if index is None or index < 0:
            raise ValueError("insert_index requires non-negative index")
        if not exists_in_doc:
            patch.append({"op": "add", "path": array_path, "value": []})
        patch.append({"op": "add", "path": f"{array_path}/{index}", "value": value})
        return patch

    if action == "remove_index":
        if index is None or index < 0:
            raise ValueError("remove_index requires non-negative index")
        if index >= len(arr):
            raise ValueError(f"index out of range (len={len(arr)})")
        patch.append({"op": "remove", "path": f"{array_path}/{index}"})
        return patch

    if action == "replace_index":
        if value is None:
            raise ValueError("replace_index requires value")
        if index is None or index < 0:
            raise ValueError("replace_index requires non-negative index")
        if index >= len(arr):
            raise ValueError(f"index out of range (len={len(arr)})")
        patch.append({"op": "replace", "path": f"{array_path}/{index}", "value": value})
        return patch

    raise ValueError(f"Unsupported action: {action}")