from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_yaml(path: Path) -> Any:
    if yaml is None:
        raise RuntimeError(
            "Missing dependency: PyYAML. Install with: uv add pyyaml (or: pip install pyyaml)"
        )
    return yaml.safe_load(_read_text(path))


def _repo_root() -> Path:
    # .../pbpk-rocrate-metadata/packages/pbpk_backend/services/form_spec.py
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class FormSpecPaths:
    form_spec_root: Path
    sections_dir: Path
    logic_dir: Path
    helptexts_dir: Path
    vocab_dir: Path


def _paths() -> FormSpecPaths:
    rr = _repo_root()
    form_spec_root = rr / "packages" / "pbpk-form-spec"
    sections_dir = form_spec_root / "sections"
    logic_dir = form_spec_root / "logic"
    helptexts_dir = form_spec_root / "helptexts"
    vocab_dir = rr / "packages" / "pbpk-metadata-spec" / "vocabularies"
    return FormSpecPaths(
        form_spec_root=form_spec_root,
        sections_dir=sections_dir,
        logic_dir=logic_dir,
        helptexts_dir=helptexts_dir,
        vocab_dir=vocab_dir,
    )


def _list_yaml_files(d: Path) -> List[Path]:
    if not d.exists():
        return []
    return sorted(
        [p for p in d.iterdir() if p.is_file() and p.suffix in {".yaml", ".yml"}],
        key=lambda p: p.name,
    )


def _safe_read_yaml(path: Path) -> Any:
    try:
        return _read_yaml(path)
    except FileNotFoundError:
        return None


def _load_sections(sections_dir: Path) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    for f in _list_yaml_files(sections_dir):
        obj = _read_yaml(f)
        if not isinstance(obj, dict):
            # Skip non-dict sections, but do not crash.
            continue
        obj["_file"] = f.name
        sections.append(obj)
    return sections


def _load_logic(logic_dir: Path) -> Dict[str, Any]:
    conditions = _safe_read_yaml(logic_dir / "conditions.yaml")
    dependencies = _safe_read_yaml(logic_dir / "dependencies.yaml")
    out: Dict[str, Any] = {}
    if conditions is not None:
        out["conditions"] = conditions
    if dependencies is not None:
        out["dependencies"] = dependencies
    return out


def _load_helptexts(helptexts_dir: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not helptexts_dir.exists():
        return out
    for p in sorted(helptexts_dir.iterdir(), key=lambda x: x.name):
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
            out[p.name] = _read_text(p)
    return out


def _load_vocabularies(vocab_dir: Path) -> Dict[str, Any]:
    """
    Loads vocab YAML files into a dict keyed by filename (without extension).
    Example: compartments.yaml -> vocabularies["compartments"] = <yaml object>
    """
    out: Dict[str, Any] = {}
    for f in _list_yaml_files(vocab_dir):
        out[f.stem] = _read_yaml(f)
    return out


def compile_pbpk_form_spec(
    *,
    include_helptexts: bool = False,
    include_vocabularies: bool = False,
) -> Dict[str, Any]:
    p = _paths()

    if not p.sections_dir.exists():
        raise FileNotFoundError(f"sections dir not found: {p.sections_dir}")

    sections = _load_sections(p.sections_dir)
    logic = _load_logic(p.logic_dir)

    result: Dict[str, Any] = {
        "api_version": "v1",
        "kind": "pbpk.form_spec",
        "source": {
            "form_spec_root": str(p.form_spec_root),
            "sections_dir": str(p.sections_dir),
            "logic_dir": str(p.logic_dir),
        },
        "sections": sections,
        "logic": logic,
        "helptexts": None,
        "vocabularies": None,
    }

    if include_helptexts:
        result["helptexts"] = _load_helptexts(p.helptexts_dir)

    if include_vocabularies:
        result["vocabularies"] = _load_vocabularies(p.vocab_dir)

    return result


# ----------------------------
# Registry compilation (Step 7.1)
# ----------------------------

def _normalize_cardinality(card: Optional[str]) -> str:
    if not card:
        return "one"
    c = str(card).strip().lower()
    return "many" if c == "many" else "one"


def _flatten_fields(
    *,
    section_id: str,
    fields: List[Dict[str, Any]],
    out_by_path: Dict[str, Dict[str, Any]],
    out_by_key: Dict[str, Dict[str, Any]],
    issues: List[Dict[str, Any]],
    vocab_index: Dict[str, List[Any]],
) -> None:
    """
    Recursively flatten field trees.

    Unique field key = "{section_id}.{field_id}" for top-level,
    nested key = "{section_id}.{parent_id}.{child_id}".
    """

    def walk(parent_key: str, node: Dict[str, Any]) -> None:
        fid = node.get("id")
        path = node.get("path")

        if not isinstance(fid, str) or not fid:
            issues.append(
                {
                    "type": "invalid_field",
                    "section": section_id,
                    "message": "Field missing/invalid id",
                    "field": node,
                }
            )
            return

        if not isinstance(path, str) or not path.startswith("/"):
            issues.append(
                {
                    "type": "invalid_field",
                    "section": section_id,
                    "message": f"Field '{fid}' missing/invalid path",
                    "field": node,
                }
            )
            return

        key = f"{parent_key}.{fid}" if parent_key else f"{section_id}.{fid}"

        norm: Dict[str, Any] = {
            "key": key,
            "section_id": section_id,
            "id": fid,
            "path": path,
            "label": node.get("label"),
            "description": node.get("description"),
            "value_type": node.get("value_type"),
            "required": bool(node.get("required", False)),
            "cardinality": _normalize_cardinality(node.get("cardinality")),
            "allowed_values": node.get("allowed_values"),
            "vocabulary": node.get("vocabulary"),
            "ui": node.get("ui"),
        }

        # Resolve vocab reference -> allowed_values (only if allowed_values not set)
        vocab = norm.get("vocabulary")
        if vocab:
            vocab_name = str(vocab)
            vocab_vals = vocab_index.get(vocab_name)
            if isinstance(vocab_vals, list):
                if not norm.get("allowed_values"):
                    norm["allowed_values"] = vocab_vals
            else:
                issues.append(
                    {
                        "type": "missing_vocabulary",
                        "section": section_id,
                        "field_key": key,
                        "vocabulary": vocab_name,
                    }
                )

        # Collisions
        if path in out_by_path:
            issues.append(
                {
                    "type": "duplicate_path",
                    "path": path,
                    "existing": out_by_path[path]["key"],
                    "new": key,
                }
            )
        else:
            out_by_path[path] = norm

        if key in out_by_key:
            issues.append({"type": "duplicate_key", "key": key})
        else:
            out_by_key[key] = norm

        # Recurse children
        children = node.get("fields")
        if isinstance(children, list):
            for ch in children:
                if isinstance(ch, dict):
                    walk(key, ch)
                else:
                    issues.append(
                        {
                            "type": "invalid_child",
                            "section": section_id,
                            "parent_key": key,
                            "message": "Child field is not an object",
                        }
                    )

    for f in fields:
        if isinstance(f, dict):
            walk("", f)
        else:
            issues.append(
                {
                    "type": "invalid_field",
                    "section": section_id,
                    "message": "Top-level field is not an object",
                }
            )


def compile_pbpk_form_registry(
    *,
    include_helptexts: bool = False,
    include_vocabularies: bool = True,
) -> Dict[str, Any]:
    """
    Returns form spec + a flattened registry for frontend.

    IMPORTANT: This function is defensive: it should not throw just because a YAML
    file is empty or slightly malformed. Any problems are surfaced in registry.issues.
    """
    # If include_vocabularies is True, spec will attempt to load vocab files too.
    spec = compile_pbpk_form_spec(
        include_helptexts=include_helptexts,
        include_vocabularies=include_vocabularies,
    )

    issues: List[Dict[str, Any]] = []

    # Build a clean vocab index (only vocabularies that are lists)
    vocab_index: Dict[str, List[Any]] = {}
    vocab_raw = spec.get("vocabularies") if include_vocabularies else None

    if include_vocabularies:
        if isinstance(vocab_raw, dict):
            for k, v in vocab_raw.items():
                if isinstance(v, list):
                    vocab_index[k] = v
                elif v is None:
                    issues.append({"type": "empty_vocabulary", "vocabulary": k})
                else:
                    issues.append(
                        {
                            "type": "invalid_vocabulary_format",
                            "vocabulary": k,
                            "loaded_type": type(v).__name__,
                        }
                    )
        elif vocab_raw is None:
            issues.append({"type": "missing_vocabularies_container"})
        else:
            issues.append(
                {
                    "type": "invalid_vocab_container",
                    "loaded_type": type(vocab_raw).__name__,
                }
            )

    fields_by_path: Dict[str, Dict[str, Any]] = {}
    fields_by_key: Dict[str, Dict[str, Any]] = {}

    sections = spec.get("sections", [])
    if not isinstance(sections, list):
        issues.append({"type": "invalid_sections_container"})
        sections = []

    for sec in sections:
        if not isinstance(sec, dict):
            issues.append({"type": "invalid_section", "message": "Section is not an object"})
            continue
        sid = sec.get("id")
        if not isinstance(sid, str) or not sid:
            issues.append({"type": "invalid_section", "message": "Section missing id"})
            continue
        flds = sec.get("fields", [])
        if not isinstance(flds, list):
            issues.append({"type": "invalid_section_fields", "section": sid})
            continue

        _flatten_fields(
            section_id=sid,
            fields=flds,
            out_by_path=fields_by_path,
            out_by_key=fields_by_key,
            issues=issues,
            vocab_index=vocab_index,
        )

    return {
        "api_version": "v1",
        "kind": "pbpk.form_registry",
        "spec": spec,
        "registry": {
            "fields_by_path": fields_by_path,
            "fields_by_key": fields_by_key,
            "vocabulary_index": vocab_index if include_vocabularies else None,
            "issues": issues,
        },
    }