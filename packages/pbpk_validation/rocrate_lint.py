from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set


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


def validate_rocrate(rocrate_metadata: Dict[str, Any]) -> List[CrateIssue]:
    """PBPK-domain checks only. Base RO-Crate spec compliance is handled by rocrate_validator."""
    issues: List[CrateIssue] = []

    # Minimal structural guard so PBPK checks can run
    graph = rocrate_metadata.get("@graph")
    if not isinstance(graph, list):
        return issues

    idx = _index_graph(graph)
    dataset = idx.get("./")
    if not dataset:
        return issues

    # C5: pbpk model exists
    model = idx.get("#pbpk-model")
    if not model:
        issues.append(CrateIssue("ERROR", "C5", "Missing PBPK model node with @id '#pbpk-model'.", node_id="#pbpk-model"))
        return issues

    model_types = set(_as_list(model.get("@type")))
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

    # Wc2: codeRepository exists on model
    if not isinstance(model.get("codeRepository"), str) or not model.get("codeRepository"):
        issues.append(CrateIssue("WARNING", "Wc2", "Model has no codeRepository.", node_id="#pbpk-model"))

    # Wc4: reproducibility file present
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

    return issues
