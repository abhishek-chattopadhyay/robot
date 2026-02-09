from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class CrateIssue:
    level: str  # "ERROR" or "WARNING"
    code: str
    message: str
    node_id: str


def _index_graph(graph: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for n in graph:
        if isinstance(n, dict) and isinstance(n.get("@id"), str):
            idx[n["@id"]] = n
    return idx


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def validate_rocrate(rocrate_metadata: Dict[str, Any], crate_dir: Optional[Path] = None) -> List[CrateIssue]:
    issues: List[CrateIssue] = []

    graph = rocrate_metadata.get("@graph")
    if not isinstance(graph, list):
        issues.append(CrateIssue("ERROR", "C2", "@graph must be a list.", node_id="/"))
        return issues

    idx = _index_graph(graph)

    # C4: crate metadata node exists
    meta = idx.get("ro-crate-metadata.json")
    if not meta:
        issues.append(CrateIssue("ERROR", "C4", "Missing ro-crate-metadata.json node.", node_id="ro-crate-metadata.json"))
        return issues

    about = meta.get("about")
    about_id = about.get("@id") if isinstance(about, dict) else None
    if about_id != "./":
        issues.append(CrateIssue("ERROR", "C4", "ro-crate-metadata.json.about must reference './'.", node_id="ro-crate-metadata.json"))

    # C3: dataset root exists
    dataset = idx.get("./")
    if not dataset:
        issues.append(CrateIssue("ERROR", "C3", "Missing Dataset root node with @id './'.", node_id="./"))
        return issues

    ds_type = set(_as_list(dataset.get("@type")))
    if "Dataset" not in ds_type:
        issues.append(CrateIssue("ERROR", "C3", "Root './' node must have @type including 'Dataset'.", node_id="./"))

    # C5: pbpk model exists
    model = idx.get("#pbpk-model")
    if not model:
        issues.append(CrateIssue("ERROR", "C5", "Missing PBPK model node with @id '#pbpk-model'.", node_id="#pbpk-model"))
        return issues

    model_types = set(_as_list(model.get("@type")))
    # With your context alias, it will usually be "ComputationalModel" in the JSON,
    # but expanded semantics correspond to SoftwareSourceCode. Accept either.
    if not (("SoftwareSourceCode" in model_types) or ("ComputationalModel" in model_types)):
        issues.append(
            CrateIssue(
                "ERROR",
                "C5",
                "PBPK model node should have @type 'ComputationalModel' or 'SoftwareSourceCode'.",
                node_id="#pbpk-model",
            )
        )

    # C6: dataset hasPart includes model
    has_part = _as_list(dataset.get("hasPart"))
    has_part_ids: Set[str] = set()
    for hp in has_part:
        if isinstance(hp, dict) and isinstance(hp.get("@id"), str):
            has_part_ids.add(hp["@id"])
    if "#pbpk-model" not in has_part_ids:
        issues.append(CrateIssue("ERROR", "C6", "Dataset './'.hasPart must include '#pbpk-model'.", node_id="./"))

    # Wc1: dataset creator exists
    creators = _as_list(dataset.get("creator"))
    if not creators:
        issues.append(CrateIssue("WARNING", "Wc1", "Dataset has no creator listed.", node_id="./"))

    # Wc2: codeRepository exists on model
    if not isinstance(model.get("codeRepository"), str) or not model.get("codeRepository"):
        issues.append(CrateIssue("WARNING", "Wc2", "Model has no codeRepository.", node_id="#pbpk-model"))

    # Wc4: reproducibility file present (heuristic: any File with reproducibilityInstructions or docs/reproducibility)
    repro_found = False
    for n in graph:
        if not isinstance(n, dict):
            continue
        nid = n.get("@id")
        if not isinstance(nid, str):
            continue
        if nid.endswith("docs/reproducibility.md"):
            repro_found = True
        if "pbpk:reproducibilityInstructions" in n:
            repro_found = True
    if not repro_found:
        issues.append(CrateIssue("WARNING", "Wc4", "No reproducibility file detected.", node_id="./"))

    # Wc5: pbpk linkouts exist (chemicals + biological systems)
    if "pbpk:hasChemical" not in model:
        issues.append(CrateIssue("WARNING", "Wc5", "Model has no pbpk:hasChemical links.", node_id="#pbpk-model"))
    if "pbpk:hasBiologicalSystem" not in model:
        issues.append(CrateIssue("WARNING", "Wc5", "Model has no pbpk:hasBiologicalSystem links.", node_id="#pbpk-model"))

    # Wc3: check referenced files exist on disk if crate_dir is provided
    if crate_dir is not None:
        for ref_id in has_part_ids:
            # Only check file-like ids (heuristic: contains "/" and not starting with "#")
            if ref_id.startswith("#") or ref_id in ("./", "ro-crate-metadata.json"):
                continue
            if "/" in ref_id or "." in ref_id:
                p = (crate_dir / ref_id).resolve()
                if not p.exists():
                    issues.append(
                        CrateIssue(
                            "WARNING",
                            "Wc3",
                            f"hasPart references '{ref_id}' but file does not exist at: {p}",
                            node_id="./",
                        )
                    )

    return issues
