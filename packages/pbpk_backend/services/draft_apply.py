from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services.drafts import get_draft, patch_draft
from pbpk_backend.services.jsonpatch import PatchError


class DraftApplyError(ValueError):
    pass


def _split_pointer(path: str) -> List[str]:
    """
    Minimal JSON Pointer splitter (RFC6901).
    """
    if path == "":
        return []
    if not path.startswith("/"):
        raise DraftApplyError(f"Invalid JSON pointer (must start with '/'): {path}")
    parts = path.split("/")[1:]
    return [p.replace("~1", "/").replace("~0", "~") for p in parts]


def _path_exists(doc: Any, path: str) -> bool:
    """
    Read-only traversal check.
    """
    parts = _split_pointer(path)
    cur = doc
    for tok in parts:
        if isinstance(cur, dict):
            if tok not in cur:
                return False
            cur = cur[tok]
        elif isinstance(cur, list):
            if tok == "-":
                return False
            try:
                idx = int(tok)
            except ValueError:
                return False
            if idx < 0 or idx >= len(cur):
                return False
            cur = cur[idx]
        else:
            return False
    return True


def _container_for_next_token(next_tok: str) -> Any:
    """
    Heuristic container creation:
    - numeric token => list
    - otherwise => dict
    """
    try:
        int(next_tok)
        return []
    except ValueError:
        return {}


def _ensure_parent_ops(doc: Any, target_path: str) -> List[Dict[str, Any]]:
    """
    Generate JSON Patch ops that create missing parent containers *in dicts*.
    We do NOT auto-create missing list elements (unsafe).
    """
    parts = _split_pointer(target_path)
    if len(parts) <= 1:
        return []

    ops: List[Dict[str, Any]] = []
    cur = doc
    built_prefix: List[str] = []

    # walk all parents (exclude last token)
    for i in range(len(parts) - 1):
        tok = parts[i]
        next_tok = parts[i + 1] if i + 1 < len(parts) else ""

        if isinstance(cur, dict):
            if tok not in cur:
                # create missing dict key as container (dict or list)
                container = _container_for_next_token(next_tok)
                prefix_path = "/" + "/".join(built_prefix + [tok])
                ops.append({"op": "add", "path": prefix_path, "value": container})
                cur[tok] = container
            cur = cur[tok]
            built_prefix.append(tok)
            continue

        if isinstance(cur, list):
            # Do not create list elements automatically
            if tok == "-":
                raise DraftApplyError("'-' is not valid in parent traversal")
            try:
                idx = int(tok)
            except ValueError:
                raise DraftApplyError(f"Expected list index in path, got: {tok}")
            if idx < 0 or idx >= len(cur):
                raise DraftApplyError(f"List index out of range while ensuring parents: {idx}")
            cur = cur[idx]
            built_prefix.append(tok)
            continue

        raise DraftApplyError(f"Cannot traverse into non-container while ensuring parents at token '{tok}'")

    return ops


def _edits_to_patch_ops(metadata: Dict[str, Any], edits: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert edits dict to JSON Patch ops.
    Rules:
      - value is None => remove (only if path exists)
      - otherwise:
          - replace if exists
          - add if missing (after ensuring parent containers exist)
    """
    if not isinstance(edits, dict):
        raise DraftApplyError("edits must be a dict")

    ops: List[Dict[str, Any]] = []

    for path, value in edits.items():
        if not isinstance(path, str) or not path.startswith("/"):
            raise DraftApplyError(f"Invalid edit path: {path}")

        if value is None:
            # remove only if present (avoid 'Path not found' hard failures)
            if _path_exists(metadata, path):
                ops.append({"op": "remove", "path": path})
            continue

        if _path_exists(metadata, path):
            ops.append({"op": "replace", "path": path, "value": value})
            continue

        # path missing: ensure parents (in dicts) exist, then add
        ops.extend(_ensure_parent_ops(metadata, path))
        ops.append({"op": "add", "path": path, "value": value})

    return ops


def apply_patch_to_draft(cfg: OrchestratorConfig, *, draft_id: str, patch_ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply raw JSON Patch ops to a draft's metadata.
    Returns updated draft envelope.
    """
    if not isinstance(patch_ops, list):
        raise DraftApplyError("patch_ops must be a list")

    # patch_draft writes + audits; it can raise ValueError(PatchError) and FileNotFoundError
    return patch_draft(cfg, draft_id=draft_id, patch_ops=patch_ops)


def apply_edits_to_draft(cfg: OrchestratorConfig, *, draft_id: str, edits: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply UI edits to draft, returning:
      {"api_version":"v1","kind":"pbpk.draft.apply_result","draft_id":...,"patch":[...],"draft":{...}}
    """
    env = get_draft(cfg, draft_id=draft_id)
    metadata = env.get("metadata")
    if not isinstance(metadata, dict):
        raise DraftApplyError("Draft metadata is not an object")

    try:
        # _ensure_parent_ops mutates metadata in-memory (safe), to build correct ops
        patch_ops = _edits_to_patch_ops(metadata, edits)
    except (DraftApplyError, PatchError) as e:
        raise DraftApplyError(str(e))

    # If no ops, just return current draft
    if not patch_ops:
        return {
            "api_version": "v1",
            "kind": "pbpk.draft.apply_result",
            "draft_id": draft_id,
            "patch": [],
            "draft": env,
        }

    updated = patch_draft(cfg, draft_id=draft_id, patch_ops=patch_ops)
    return {
        "api_version": "v1",
        "kind": "pbpk.draft.apply_result",
        "draft_id": draft_id,
        "patch": patch_ops,
        "draft": updated,
    }


def apply_array_op_to_draft(
    cfg: OrchestratorConfig,
    *,
    draft_id: str,
    array_path: str,
    action: str,
    value: Any = None,
    index: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Array actions: append|insert|remove_index|replace_index
    Returns apply_result envelope with patch + updated draft.
    """
    env = get_draft(cfg, draft_id=draft_id)
    metadata = env.get("metadata")
    if not isinstance(metadata, dict):
        raise DraftApplyError("Draft metadata is not an object")

    if not isinstance(array_path, str) or not array_path.startswith("/"):
        raise DraftApplyError("array_path must be a JSON pointer starting with '/'")
    if action not in {"append", "insert", "remove_index", "replace_index"}:
        raise DraftApplyError(f"Unsupported array action: {action}")

    ops: List[Dict[str, Any]] = []

    # If the array itself is missing and the action needs it, create it as []
    if action in {"append", "insert", "replace_index", "remove_index"} and not _path_exists(metadata, array_path):
        # Ensure parent containers for the array exist, then add []
        ops.extend(_ensure_parent_ops(metadata, array_path))
        ops.append({"op": "add", "path": array_path, "value": []})

    if action == "append":
        ops.append({"op": "add", "path": f"{array_path}/-", "value": value})

    elif action == "insert":
        if index is None:
            raise DraftApplyError("index is required for insert")
        ops.append({"op": "add", "path": f"{array_path}/{index}", "value": value})

    elif action == "remove_index":
        if index is None:
            raise DraftApplyError("index is required for remove_index")
        # If the element doesn't exist, no-op (avoid hard failure)
        if _path_exists(metadata, f"{array_path}/{index}"):
            ops.append({"op": "remove", "path": f"{array_path}/{index}"})

    elif action == "replace_index":
        if index is None:
            raise DraftApplyError("index is required for replace_index")
        if _path_exists(metadata, f"{array_path}/{index}"):
            ops.append({"op": "replace", "path": f"{array_path}/{index}", "value": value})
        else:
            # If index doesn't exist, treat as insert at index (JSON Patch "add")
            ops.append({"op": "add", "path": f"{array_path}/{index}", "value": value})

    if not ops:
        return {
            "api_version": "v1",
            "kind": "pbpk.draft.apply_result",
            "draft_id": draft_id,
            "patch": [],
            "draft": env,
        }

    updated = patch_draft(cfg, draft_id=draft_id, patch_ops=ops)
    return {
        "api_version": "v1",
        "kind": "pbpk.draft.apply_result",
        "draft_id": draft_id,
        "patch": ops,
        "draft": updated,
    }