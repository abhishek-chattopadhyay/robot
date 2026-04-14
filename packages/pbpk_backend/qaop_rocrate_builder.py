"""Build an RO-Crate from qAOP metadata.

Transforms validated qAOP metadata into a JSON-LD RO-Crate with KEs and KERs
as linked entities following the AOP ontology.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BuildResult:
    crate_dir: Path
    metadata_path: Path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _graph_index(graph: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for n in graph:
        if isinstance(n, dict) and isinstance(n.get("@id"), str):
            idx[n["@id"]] = n
    return idx


# Role -> JSON-LD @type mapping
_KE_TYPE_MAP = {
    "mie": "MolecularInitiatingEvent",
    "ao": "AdverseOutcome",
    "ke": "KeyEvent",
}

# Role -> which list on #qaop-model to add KE reference to
_KE_LIST_MAP = {
    "mie": "hasMolecularInitiatingEvent",
    "ao": "hasAdverseOutcome",
    "ke": "hasKeyEvent",
}


def build_rocrate_from_qaop_metadata(
    qaop_metadata: Dict[str, Any],
    crate_dir: Path,
    *,
    template_path: Path,
) -> BuildResult:
    """
    Build a qAOP RO-Crate from metadata.

    v1 policy:
    - KEs as separate JSON-LD nodes with role-based @type
    - KERs as separate nodes with @id cross-references
    - Dose-response parameters inlined on KER nodes
    - KE thresholds inlined on KE nodes
    - No file artifacts -- metadata-only crate
    """
    crate_dir = crate_dir.resolve()
    crate_dir.mkdir(parents=True, exist_ok=True)

    tpl = _load_json(template_path)
    if not isinstance(tpl, dict) or "@graph" not in tpl:
        raise ValueError(f"Template is not a JSON-LD object with @graph: {template_path}")

    graph: List[Dict[str, Any]] = tpl["@graph"]
    idx = _graph_index(graph)

    ds = idx.get("./")
    meta = idx.get("ro-crate-metadata.json")
    aop = idx.get("#qaop-model")
    if not ds or not meta or not aop:
        raise ValueError("Template must include nodes: './', 'ro-crate-metadata.json', '#qaop-model'")

    identity = qaop_metadata.get("identity", {})
    structure = qaop_metadata.get("structure", {})
    quantitative = qaop_metadata.get("quantitative", {})
    applicability = qaop_metadata.get("applicability", {})

    # ---- Dataset root ----
    ds["name"] = identity.get("title", "qAOP RO-Crate")
    ds["description"] = identity.get("description", "")
    ds["license"] = identity.get("license", "CC-BY-4.0")

    # Creators
    ds["creator"] = []
    for i, author in enumerate(identity.get("authors", []), start=1):
        pid = f"#person-{i}"
        person: Dict[str, Any] = {
            "@id": pid,
            "@type": "Person",
            "name": author.get("full_name", ""),
        }
        orcid = author.get("orcid")
        if isinstance(orcid, str) and orcid.strip():
            o = orcid.strip()
            person["identifier"] = o if o.startswith("http") else f"https://orcid.org/{o}"

        aff = author.get("affiliation")
        if isinstance(aff, str) and aff.strip():
            oid = f"#org-{i}"
            graph.append({"@id": oid, "@type": "Organization", "name": aff.strip()})
            person["affiliation"] = {"@id": oid}

        graph.append(person)
        ds["creator"].append({"@id": pid})

    # ---- AOP root (#qaop-model) ----
    aop["name"] = identity.get("title")
    aop["description"] = identity.get("description")
    aop["aopWikiId"] = identity.get("aop_wiki_id")

    # Reset KE/KER lists
    aop["hasMolecularInitiatingEvent"] = []
    aop["hasKeyEvent"] = []
    aop["hasAdverseOutcome"] = []
    aop["hasKeyEventRelationship"] = []

    # Build threshold lookup: ke_id -> threshold data
    thresholds_by_ke: Dict[int, Dict[str, Any]] = {}
    for t in quantitative.get("ke_thresholds", []):
        thresholds_by_ke[t["ke_id"]] = t

    # ---- KE nodes ----
    for i, ke in enumerate(structure.get("key_events", []), start=1):
        ke_id = ke.get("ke_id")
        node_id = f"#ke-{ke_id}" if ke_id is not None else f"#ke-idx-{i}"
        role = ke.get("role", "ke")
        ke_type = _KE_TYPE_MAP.get(role, "KeyEvent")

        node: Dict[str, Any] = {
            "@id": node_id,
            "@type": ke_type,
            "name": ke.get("title", ""),
            "keId": ke_id,
        }

        if ke.get("biological_organization_level"):
            node["biologicalOrganizationLevel"] = ke["biological_organization_level"]

        # Inline threshold if available
        threshold = thresholds_by_ke.get(ke_id)
        if threshold:
            node["thresholdValue"] = threshold["threshold_value"]
            node["unitText"] = threshold["threshold_unit"]
            node["thresholdBasis"] = threshold["threshold_basis"]
            if threshold.get("measurement_endpoint"):
                node["qaop:measurementEndpoint"] = threshold["measurement_endpoint"]
            if threshold.get("measurement_unit"):
                node["qaop:measurementUnit"] = threshold["measurement_unit"]

        graph.append(node)

        # Add reference to appropriate list on AOP root
        list_key = _KE_LIST_MAP.get(role, "hasKeyEvent")
        aop[list_key].append({"@id": node_id})

    # ---- KER nodes ----
    for i, ker in enumerate(structure.get("key_event_relationships", []), start=1):
        ker_id = ker.get("ker_id")
        node_id = f"#ker-{ker_id}" if ker_id is not None else f"#ker-idx-{i}"

        upstream_ke_id = ker.get("upstream_ke_id")
        downstream_ke_id = ker.get("downstream_ke_id")

        node: Dict[str, Any] = {
            "@id": node_id,
            "@type": "KeyEventRelationship",
            "kerId": ker_id,
            "hasUpstreamKeyEvent": {"@id": f"#ke-{upstream_ke_id}"},
            "hasDownstreamKeyEvent": {"@id": f"#ke-{downstream_ke_id}"},
        }

        # Inline response-response function
        rrf = ker.get("response_response_function")
        if rrf:
            node["responseResponseFunction"] = rrf

        # Inline provenance
        if ker.get("experimental_system"):
            node["experimentalSystem"] = ker["experimental_system"]
        if ker.get("species"):
            node["qaop:species"] = ker["species"]
        if ker.get("data_source"):
            node["qaop:dataSource"] = ker["data_source"]
        if ker.get("relationship_description"):
            node["description"] = ker["relationship_description"]

        graph.append(node)
        aop["hasKeyEventRelationship"].append({"@id": node_id})

    # ---- Applicability on AOP root ----
    species_list = applicability.get("species", [])
    if species_list:
        aop["qaop:taxonomicApplicability"] = species_list

    chem_stressors = applicability.get("chemical_stressors", [])
    if chem_stressors:
        aop["qaop:chemicalStressors"] = chem_stressors

    # ---- Write output files ----
    # Write source metadata
    qaop_meta_path = crate_dir / "qaop-metadata.json"
    _write_json(qaop_meta_path, qaop_metadata)

    # Write RO-Crate metadata
    _write_json(crate_dir / "ro-crate-metadata.json", tpl)

    return BuildResult(crate_dir=crate_dir, metadata_path=qaop_meta_path)
