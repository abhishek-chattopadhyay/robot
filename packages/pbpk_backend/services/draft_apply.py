from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pbpk_backend.services.orchestrator import OrchestratorConfig
from pbpk_backend.services import drafts as draft_svc


class DraftApplyError(ValueError):
    pass


# ----------------------------
# JSON Pointer helpers (RFC6901)
# ----------------------------

def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _split_pointer(path: str) -> List[str]:
    if path == "":
        return []
    if not path.startswith("/"):
        raise DraftApplyError(f"Invalid JSON pointer (must start with '/'): {path}")
    return [_unescape(p) for p in path.split("/")[1:]]


def _try_get_parent(doc: Any, parts: List[str]) -> Tuple[Optional[Any], Optional[str], bool]:
    """
    Best-effort traversal to parent container.
    Returns (parent, last_token, ok).
    ok=False means path can't be traversed (missing intermediate parts, bad indices, etc.)
    """
    if not parts:
        return None, None, False

    cur = doc
    for token in parts[:-1]:
        if isinstance(cur, dict):
            if token not in cur:
                return None, None, False
            cur = cur[token]
        elif isinstance(cur, list):
            if token == "-":
                return None, None, False
            try:
                idx = int(token)
            except ValueError:
                return None, None, False
            if idx < 0 or idx >= len(cur):
                return None, None, False
            cur = cur[idx]
        else:
            return None, None, False

    return cur, parts[-1], True


def _path_exists(doc: Any, path: str) -> bool:
    parts = _split_pointer(path)
    if parts == []:
        return True
    parent, last, ok = _try_get_parent(doc, parts)
    if not ok or parent is None or last is None:
        return False

    if isinstance(parent, dict):
        return last in parent
    if isinstance(parent, list):
        if last == "-":
            return False
        try:
            idx = int(last)
        except ValueError:
            return False
        return 0 <= idx < len(parent)
    return False


# ----------------------------
# Patch builders
# ----------------------------

def build_patch_from_edits(metadata: Dict[str, Any], edits: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    edits: { "/json/pointer": value, ... }
    Convention:
      - value is None -> remove (if exists)
      - otherwise -> replace if exists, else add
    """
    if not isinstance(edits, dict):
        raise DraftApplyError("edits must be an object")
    ops: List[Dict[str, Any]] = []

    for path, value in edits.items():
        if not isinstance(path, str) or not path.startswith("/"):
            raise DraftApplyError(f"Invalid edit path (must be JSON pointer starting with '/'): {path}")

        exists = _path_exists(metadata, path)

        if value is None:
            if exists:
                ops.append({"op": "remove", "path": path})
            # if it doesn't exist, do nothing (idempotent)
            continue

        if exists:
            ops.append({"op": "replace", "path": path, "value": value})
        else:
            ops.append({"op": "add", "path": path, "value": value})

    return ops


def build_array_patch(
    *,
    array_path: str,
    action: str,
    value: Optional[Any] = None,
    index: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Build JSON Patch ops for array operations.
    Supported:
      - append:       add  <array_path>/-         value required
      - insert:       add  <array_path>/<index>   value+index required
      - remove_index: remove <array_path>/<index> index required
      - replace_index: replace <array_path>/<index> value+index required
    """
    if not isinstance(array_path, str) or not array_path.startswith("/"):
        raise DraftApplyError("array_path must be a JSON pointer starting with '/'")
    if action not in {"append", "insert", "remove_index", "replace_index"}:
        raise DraftApplyError(f"Unsupported array action: {action}")

    if action == "append":
        if value is None:
            raise DraftApplyError("append requires value")
        return [{"op": "add", "path": f"{array_path}/-", "value": value}]

    if action == "insert":
        if value is None or index is None:
            raise DraftApplyError("insert requires value and index")
        return [{"op": "add", "path": f"{array_path}/{index}", "value": value}]

    if action == "remove_index":
        if index is None:
            raise DraftApplyError("remove_index requires index")
        return [{"op": "remove", "path": f"{array_path}/{index}"}]

    # replace_index
    if value is None or index is None:
        raise DraftApplyError("replace_index requires value and index")
    return [{"op": "replace", "path": f"{array_path}/{index}", "value": value}]


# ----------------------------
# Apply functions (call existing drafts.patch_draft)
# ----------------------------

def apply_patch_to_draft(cfg: OrchestratorConfig, *, draft_id: str, patch_ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(patch_ops, list):
        raise DraftApplyError("patch_ops must be a list")
    return draft_svc.patch_draft(cfg, draft_id=draft_id, patch_ops=patch_ops)


def apply_edits_to_draft(cfg: OrchestratorConfig, *, draft_id: str, edits: Dict[str, Any]) -> Dict[str, Any]:
    d = draft_svc.get_draft(cfg, draft_id=draft_id)
    metadata = d.get("metadata", {})
    if not isinstance(metadata, dict):
        raise DraftApplyError("draft metadata is not an object")

    patch_ops = build_patch_from_edits(metadata, edits)
    new_d = draft_svc.patch_draft(cfg, draft_id=draft_id, patch_ops=patch_ops)
    return {
        "api_version": "v1",
        "kind": "pbpk.draft.apply_result",
        "draft_id": draft_id,
        "patch": patch_ops,
        "draft": new_d,
    }


def apply_array_op_to_draft(
    cfg: OrchestratorConfig,
    *,
    draft_id: str,
    array_path: str,
    action: str,
    value: Optional[Any] = None,
    index: Optional[int] = None,
) -> Dict[str, Any]:
    patch_ops = build_array_patch(array_path=array_path, action=action, value=value, index=index)
    new_d = draft_svc.patch_draft(cfg, draft_id=draft_id, patch_ops=patch_ops)
    return {
        "api_version": "v1",
        "kind": "pbpk.draft.apply_result",
        "draft_id": draft_id,
        "patch": patch_ops,
        "draft": new_d,
    }