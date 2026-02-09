from __future__ import annotations

import json
import shutil
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
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _graph_index(graph: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
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


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_text_if_missing(path: Path, text: str) -> None:
    if path.exists():
        return
    _ensure_parent_dir(path)
    path.write_text(text, encoding="utf-8")


def _write_sbml_scaffold_if_missing(path: Path) -> None:
    if path.exists():
        return
    _ensure_parent_dir(path)
    scaffold = """<?xml version="1.0" encoding="UTF-8"?>
<sbml xmlns="http://www.sbml.org/sbml/level3/version1/core" level="3" version="1">
  <model id="pbpk_placeholder" name="PBPK Placeholder Model">
    <listOfCompartments>
      <compartment id="Blood" name="Blood" constant="true"/>
      <compartment id="Liver" name="Liver" constant="true"/>
    </listOfCompartments>
  </model>
</sbml>
"""
    path.write_text(scaffold, encoding="utf-8")


def build_rocrate_from_pbpk_metadata(
    pbpk_metadata: Dict[str, Any],
    crate_dir: Path,
    *,
    template_path: Path,
    source_files_dir: Optional[Path] = None,
    context_path_for_examples: str = "../../packages/pbpk-metadata-spec/jsonld/pbpk-context.jsonld",
) -> BuildResult:
    """
    Build a RO-Crate JSON-LD metadata file from the domain PBPK metadata payload.

    v1 policy:
    - deterministic mapping (no inference)
    - dataset-only authorship
    - create one #pbpk-model node
    - create nodes for bio systems, chemicals, parameters, evaluation/calibration/suv if present
    - create File nodes for artifacts listed in electronic_files_and_reproducibility.digital_artifacts
    - materialize artifacts: copy-first from source_files_dir (if provided), else create placeholders
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
    model = idx.get("#pbpk-model")
    if not ds or not meta or not model:
        raise ValueError("Template must include nodes: './', 'ro-crate-metadata.json', '#pbpk-model'")

    gmi = pbpk_metadata["general_model_information"]

    # ---- Dataset root ----
    ds["name"] = gmi["model_name"]
    ds["description"] = gmi["model_description"]
    ds["license"] = gmi["license"]

    # creators (dataset-only) — reset any template persons/orgs
    ds["creator"] = []
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#person-"))]
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#org-"))]

    for i, author in enumerate(gmi.get("model_authors", []), start=1):
        pid = f"#person-{i}"
        oid = f"#org-{i}"

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
            org = {"@id": oid, "@type": "Organization", "name": aff.strip()}
            graph.append(org)
            person["affiliation"] = {"@id": oid}

        graph.append(person)
        ds["creator"].append({"@id": pid})

    # ---- Model node ----
    model["name"] = gmi["model_name"]
    model["version"] = gmi["model_version"]
    model["description"] = gmi["model_description"]
    model["applicationCategory"] = gmi["intended_application_category"]

    platforms = gmi.get("software_platform") or []
    model["programmingLanguage"] = platforms if isinstance(platforms, list) else [platforms]

    avail = gmi.get("model_availability") or []
    if isinstance(avail, list):
        if len(avail) == 1:
            model["codeRepository"] = avail[0]
        elif len(avail) > 1:
            model["codeRepository"] = avail
    elif isinstance(avail, str):
        model["codeRepository"] = avail

    if gmi.get("limitations_summary"):
        model["pbpk:limitationsSummary"] = gmi["limitations_summary"]
    else:
        model.pop("pbpk:limitationsSummary", None)

    # ---- Section 9: applicability/limitations ----
    mal = pbpk_metadata["model_applicability_and_limitations"]
    model["purpose"] = mal["intended_use"]
    model["pbpk:applicabilityDomain"] = mal["applicability_domain"]
    model["pbpk:confidenceStatement"] = mal["confidence_statement"]
    model["pbpk:limitations"] = mal["known_limitations"]
    if mal.get("misuse_risks"):
        model["pbpk:misuseRisks"] = mal["misuse_risks"]
    else:
        model.pop("pbpk:misuseRisks", None)

    # ---- Section 4: structure & representation ----
    msr = pbpk_metadata["model_structure_and_representation"]
    model["pbpk:modelStructureDescription"] = msr["model_structure_description"]
    model["pbpk:mathematicalRepresentation"] = msr["mathematical_representation"]

    model["pbpk:structuralCompartments"] = []
    for comp in msr.get("structural_compartments", []):
        obj: Dict[str, Any] = {
            "@type": "Thing",
            "name": comp["compartment_name"],
            "pbpk:biologicalReference": comp["biological_reference"],
        }
        if comp.get("compartment_description"):
            obj["description"] = comp["compartment_description"]
        model["pbpk:structuralCompartments"].append(obj)

    model["pbpk:connections"] = []
    for conn in msr.get("inter_compartmental_connections", []):
        model["pbpk:connections"].append(
            {
                "@type": "Thing",
                "pbpk:sourceCompartment": conn["source_compartment"],
                "pbpk:targetCompartment": conn["target_compartment"],
                "pbpk:connectionType": conn["connection_type"],
            }
        )

    # ---- Biological systems (Section 2) ----
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#biosys-"))]
    biosys_nodes: List[Dict[str, Any]] = []
    for i, bs in enumerate(pbpk_metadata["biological_system_description"]["biological_systems"], start=1):
        bid = f"#biosys-{i}"
        node: Dict[str, Any] = {
            "@id": bid,
            "@type": "BiologicalSystem",
            "name": f"{bs['species']} system",
            "pbpk:species": bs["species"],
            "pbpk:lifeStage": bs["life_stages"],
            "pbpk:physiologicalScope": bs["physiological_scope"],
            "pbpk:compartments": bs["compartments"],
        }
        if bs.get("population_description"):
            node["description"] = bs["population_description"]
        if bs.get("anatomical_assumptions"):
            node["pbpk:anatomicalAssumptions"] = bs["anatomical_assumptions"]
        biosys_nodes.append(node)
        graph.append(node)

    model["pbpk:hasBiologicalSystem"] = [{"@id": n["@id"]} for n in biosys_nodes]

    # ---- Chemicals (Section 3) ----
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#chem-"))]
    chem_nodes: List[Dict[str, Any]] = []
    for i, chem in enumerate(pbpk_metadata["chemical_description"]["chemicals"], start=1):
        cid = f"#chem-{i}"

        ids: List[Dict[str, Any]] = []
        for j, ident in enumerate(chem["chemical_identifiers"], start=1):
            iid = f"#chem-{i}-id-{j}"
            ids.append({"@id": iid})
            graph.append(
                {
                    "@id": iid,
                    "@type": "PropertyValue",
                    "name": ident["identifier_type"],
                    "value": ident["identifier_value"],
                }
            )

        node: Dict[str, Any] = {
            "@id": cid,
            "@type": "ChemicalSubstance",
            "name": chem["chemical_name"],
            "pbpk:chemicalRole": chem["chemical_role"],
            "identifier": ids,
        }

        if chem.get("molecular_weight") is not None:
            node["molecularWeight"] = {
                "@type": "QuantitativeValue",
                "value": chem["molecular_weight"],
                "unitText": "g/mol",
            }
        if chem.get("physicochemical_notes"):
            node["description"] = chem["physicochemical_notes"]

        chem_nodes.append(node)
        graph.append(node)

    model["pbpk:hasChemical"] = [{"@id": n["@id"]} for n in chem_nodes]

    # ---- Parameters (Section 5) ----
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#param-"))]
    param_nodes: List[Dict[str, Any]] = []
    for i, p in enumerate(pbpk_metadata["parameterisation"]["parameters"], start=1):
        pid = f"#param-{i}"
        node: Dict[str, Any] = {
            "@id": pid,
            "@type": "Parameter",
            "name": p["parameter_name"],
            "category": p["parameter_category"],
            "value": p["parameter_value"],
            "unitText": p["parameter_unit"],
            "pbpk:scope": p["parameter_scope"],
            "pbpk:parameterSource": p["parameter_source"],
        }
        if p.get("parameter_notes"):
            node["description"] = p["parameter_notes"]
        if p.get("source_reference"):
            node["citation"] = p["source_reference"]
        if p.get("applicable_species"):
            node["pbpk:appliesToSpecies"] = p["applicable_species"]
        if p.get("applicable_compartments"):
            node["pbpk:appliesToCompartments"] = p["applicable_compartments"]
        if p.get("applicable_chemicals"):
            node["pbpk:appliesToChemicals"] = p["applicable_chemicals"]

        param_nodes.append(node)
        graph.append(node)

    model["pbpk:hasParameter"] = [{"@id": n["@id"]} for n in param_nodes]

    # ---- Evaluation (Section 7) ----
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#evaluation-"))]
    eval_nodes: List[Dict[str, Any]] = []
    for i, e in enumerate(pbpk_metadata["model_evaluation_and_validation"]["evaluation_activities"], start=1):
        eid = f"#evaluation-{i}"
        node: Dict[str, Any] = {
            "@id": eid,
            "@type": "CreativeWork",
            "name": f"Evaluation activity {i}",
            "description": e["evaluation_description"],
            "pbpk:method": e["evaluation_method"],
            "pbpk:outcome": e["evaluation_outcome"],
        }
        if e.get("evaluation_data"):
            node["pbpk:evaluationData"] = e["evaluation_data"]
        if e.get("evaluation_limitations"):
            node["pbpk:limitations"] = e["evaluation_limitations"]

        metrics = e.get("performance_metrics") or []
        if metrics:
            node["pbpk:performanceMetrics"] = []
            for m in metrics:
                mv: Dict[str, Any] = {"@type": "PropertyValue", "name": m["metric_name"]}
                if "metric_value" in m and m["metric_value"] is not None:
                    mv["value"] = m["metric_value"]
                if m.get("metric_interpretation"):
                    mv["description"] = m["metric_interpretation"]
                node["pbpk:performanceMetrics"].append(mv)

        eval_nodes.append(node)
        graph.append(node)

    model["pbpk:hasEvaluation"] = [{"@id": n["@id"]} for n in eval_nodes]

    # ---- Optional calibration ----
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#calibration-"))]
    cal = pbpk_metadata.get("calibration_and_parameter_estimation", {})
    cal_acts = cal.get("calibration_activities") or []
    cal_nodes: List[Dict[str, Any]] = []
    for i, c in enumerate(cal_acts, start=1):
        cid = f"#calibration-{i}"
        node = {
            "@id": cid,
            "@type": "CreativeWork",
            "name": f"Calibration activity {i}",
            "description": c["calibration_description"],
            "pbpk:method": c["calibration_method"],
        }
        if c.get("calibration_data"):
            node["pbpk:calibrationData"] = c["calibration_data"]
        if c.get("calibrated_parameters"):
            node["pbpk:calibratedParameters"] = c["calibrated_parameters"]
        if c.get("optimization_criteria"):
            node["pbpk:optimizationCriteria"] = c["optimization_criteria"]
        if c.get("calibration_notes"):
            node["pbpk:notes"] = c["calibration_notes"]
        cal_nodes.append(node)
        graph.append(node)

    if cal_nodes:
        model["pbpk:hasCalibration"] = [{"@id": n["@id"]} for n in cal_nodes]
    else:
        model.pop("pbpk:hasCalibration", None)

    # ---- Optional SUV ----
    graph[:] = [n for n in graph if not (isinstance(n, dict) and str(n.get("@id", "")).startswith("#suv-"))]
    suv = pbpk_metadata.get("sensitivity_uncertainty_variability", {})
    suv_acts = suv.get("suv_analyses") or []
    suv_nodes: List[Dict[str, Any]] = []
    for i, s in enumerate(suv_acts, start=1):
        sid = f"#suv-{i}"
        node: Dict[str, Any] = {
            "@id": sid,
            "@type": "CreativeWork",
            "name": f"SUV analysis {i}",
            "pbpk:analysisType": s["analysis_type"],
            "description": s["analysis_results"],
        }
        if s.get("analysis_method"):
            node["pbpk:method"] = s["analysis_method"]
        if s.get("analyzed_parameters"):
            node["pbpk:analyzedParameters"] = s["analyzed_parameters"]
        if s.get("robustness_interpretation"):
            node["pbpk:robustnessInterpretation"] = s["robustness_interpretation"]
        if s.get("suv_notes"):
            node["pbpk:notes"] = s["suv_notes"]
        suv_nodes.append(node)
        graph.append(node)

    if suv_nodes:
        model["pbpk:hasSUVAnalysis"] = [{"@id": n["@id"]} for n in suv_nodes]
    else:
        model.pop("pbpk:hasSUVAnalysis", None)

    # ---- Files / artifacts (Section 10) ----
    graph[:] = [n for n in graph if not (isinstance(n, dict) and n.get("@type") == "File" and "pbpk:artifactType" in n)]

    efr = pbpk_metadata["electronic_files_and_reproducibility"]
    digital_artifacts = efr.get("digital_artifacts") or []

    file_nodes: List[Dict[str, Any]] = []
    for art in digital_artifacts:
        fid = art["artifact_location"]
        fnode: Dict[str, Any] = {
            "@id": fid,
            "@type": "File",
            "name": art["artifact_name"],
            "pbpk:artifactType": art["artifact_type"],
            "pbpk:artifactFormat": art["artifact_format"],
        }
        if art.get("artifact_description"):
            fnode["description"] = art["artifact_description"]
        file_nodes.append(fnode)
        graph.append(fnode)

    repro_text = efr.get("reproducibility_instructions")
    if isinstance(repro_text, str) and repro_text.strip():
        model["pbpk:reproducibilityInstructions"] = repro_text.strip()
    else:
        model.pop("pbpk:reproducibilityInstructions", None)

    if efr.get("documentation_practices"):
        model["pbpk:documentationPractices"] = efr["documentation_practices"]
    else:
        model.pop("pbpk:documentationPractices", None)

    # Ensure hasPart references include model + artifacts
    ds_has_part = [{"@id": "#pbpk-model"}] + [{"@id": fn["@id"]} for fn in file_nodes]
    ds["hasPart"] = ds_has_part
    model["hasPart"] = [{"@id": fn["@id"]} for fn in file_nodes]

    # ---- Materialize files: copy-first, else placeholder ----
    if source_files_dir is not None:
        source_files_dir = source_files_dir.resolve()

    for art in digital_artifacts:
        rel = art["artifact_location"]
        artifact_type = (art.get("artifact_type") or "").lower()
        artifact_format = (art.get("artifact_format") or "").lower()

        target = (crate_dir / rel).resolve()

        # 1) Copy if present in source_files_dir
        if source_files_dir is not None:
            src = (source_files_dir / rel).resolve()
            if src.exists() and src.is_file():
                _ensure_parent_dir(target)
                shutil.copy2(src, target)
                continue

        # 2) Otherwise create placeholder
        if artifact_format == "sbml" or rel.lower().endswith((".xml", ".sbml")):
            _write_sbml_scaffold_if_missing(target)
            continue

        if "repro" in artifact_type or "doc" in artifact_type or rel.lower().endswith((".md", ".txt")):
            _write_text_if_missing(
                target,
                "# Placeholder\n\nThis file was created by the RO-Crate builder because no uploaded file was provided.\n",
            )
            continue

        if rel.lower().endswith(".csv"):
            _write_text_if_missing(target, "placeholder_column\n")
            continue

        _write_text_if_missing(target, "")

    # Write crate metadata
    out_path = crate_dir / "ro-crate-metadata.json"
    _write_json(out_path, tpl)

    return BuildResult(crate_dir=crate_dir, metadata_path=out_path)