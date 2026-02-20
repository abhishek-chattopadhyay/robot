from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


class PatchError(ValueError):
    pass


def _unescape(token: str) -> str:
    # RFC6901 JSON Pointer unescaping
    return token.replace("~1", "/").replace("~0", "~")


def _split_pointer(path: str) -> List[str]:
    if path == "":
        return []
    if not path.startswith("/"):
        raise PatchError(f"Invalid JSON pointer (must start with '/'): {path}")
    parts = path.split("/")[1:]
    return [_unescape(p) for p in parts]


def _get_parent(doc: Any, parts: List[str]) -> Tuple[Any, str]:
    """
    Returns (parent_container, last_token).
    """
    if not parts:
        raise PatchError("Cannot operate on document root with this helper")

    cur = doc
    for token in parts[:-1]:
        if isinstance(cur, dict):
            if token not in cur:
                raise PatchError(f"Path not found: /{'/'.join(parts)}")
            cur = cur[token]
        elif isinstance(cur, list):
            if token == "-":
                raise PatchError("'-' is only valid for add at the last path token")
            try:
                idx = int(token)
            except ValueError:
                raise PatchError(f"Expected list index, got: {token}")
            if idx < 0 or idx >= len(cur):
                raise PatchError(f"List index out of range: {idx}")
            cur = cur[idx]
        else:
            raise PatchError(f"Cannot traverse into non-container at token '{token}'")

    return cur, parts[-1]


def apply_patch(doc: Any, patch_ops: List[Dict[str, Any]]) -> Any:
    """
    Apply minimal JSON Patch ops to a JSON-like structure (dict/list/scalars).
    Mutates doc in place and also returns it.
    Supports: add, replace, remove.
    """
    if not isinstance(patch_ops, list):
        raise PatchError("patch must be a list of operations")

    for op in patch_ops:
        if not isinstance(op, dict):
            raise PatchError("each patch operation must be an object")

        action = op.get("op")
        path = op.get("path")

        if action not in {"add", "replace", "remove"}:
            raise PatchError(f"Unsupported op: {action}")
        if not isinstance(path, str):
            raise PatchError("op.path must be a string")

        parts = _split_pointer(path)

        # Root operations (rare) — allow replace of whole document
        if parts == []:
            if action in {"add", "replace"}:
                if "value" not in op:
                    raise PatchError("op.value required for add/replace")
                doc = op["value"]
                continue
            if action == "remove":
                raise PatchError("Cannot remove document root")
            continue

        parent, last = _get_parent(doc, parts)

        if action == "remove":
            if isinstance(parent, dict):
                if last not in parent:
                    raise PatchError(f"Path not found for remove: {path}")
                del parent[last]
            elif isinstance(parent, list):
                if last == "-":
                    raise PatchError("'-' invalid for remove")
                try:
                    idx = int(last)
                except ValueError:
                    raise PatchError(f"Expected list index for remove, got: {last}")
                if idx < 0 or idx >= len(parent):
                    raise PatchError(f"List index out of range for remove: {idx}")
                parent.pop(idx)
            else:
                raise PatchError(f"Remove target parent is not a container: {path}")
            continue

        # add/replace need value
        if "value" not in op:
            raise PatchError("op.value required for add/replace")
        value = op["value"]

        if isinstance(parent, dict):
            # add and replace behave the same for dicts (replace overwrites, add inserts/overwrites)
            parent[last] = value
        elif isinstance(parent, list):
            if last == "-":
                # append
                parent.append(value)
            else:
                try:
                    idx = int(last)
                except ValueError:
                    raise PatchError(f"Expected list index, got: {last}")
                if action == "add":
                    if idx < 0 or idx > len(parent):
                        raise PatchError(f"List index out of range for add: {idx}")
                    parent.insert(idx, value)
                else:  # replace
                    if idx < 0 or idx >= len(parent):
                        raise PatchError(f"List index out of range for replace: {idx}")
                    parent[idx] = value
        else:
            raise PatchError(f"Add/replace target parent is not a container: {path}")

    return doc