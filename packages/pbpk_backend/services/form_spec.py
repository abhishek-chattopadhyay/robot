from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Keep dependency minimal: PyYAML
try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    yaml = None
    _yaml_import_error = e


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_yaml(path: Path) -> Any:
    if yaml is None:
        raise RuntimeError(
            "Missing dependency: PyYAML. Install with: uv add pyyaml  (or: pip install pyyaml)"
        )
    return yaml.safe_load(_read_text(path))


def _repo_root() -> Path:
    # services/form_spec.py -> packages/pbpk_backend/services -> repo root is parents[3]
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
    return sorted([p for p in d.iterdir() if p.is_file() and p.suffix in {".yaml", ".yml"}], key=lambda p: p.name)


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
            continue
        obj["_file"] = f.name
        sections.append(obj)
    return sections


def _load_logic(logic_dir: Path) -> Dict[str, Any]:
    # Optional files
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
        key = f.stem
        out[key] = _read_yaml(f)
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