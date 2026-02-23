from __future__ import annotations

from typing import Any, Dict


_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "biological_systems": {
        "species": "Homo sapiens",
        "life_stages": ["Adult"],
        "physiological_scope": "",
        "compartments": [],
        "population_description": "",
        "anatomical_assumptions": "",
    },
    "chemicals": {
        "chemical_name": "",
        "chemical_role": "Parent compound",
        "chemical_identifiers": [
            {"identifier_type": "CAS RN", "identifier_value": ""}
        ],
        "molecular_weight": None,
        "physicochemical_notes": "",
    },
    "evaluation_activities": {
        "evaluation_description": "",
        "evaluation_data": "",
        "evaluation_method": "Visual comparison",
        "performance_metrics": [],
        "evaluation_outcome": "",
        "evaluation_limitations": "",
    },
    "parameters": {
        "parameter_name": "",
        "parameter_category": "Physiological",
        "parameter_value": None,
        "parameter_unit": "",
        "parameter_scope": "Global",
        "applicable_species": [],
        "applicable_compartments": [],
        "applicable_chemicals": [],
        "parameter_source": "Literature",
        "source_reference": "",
        "parameter_notes": "",
    },
    "structural_compartments": {
        "compartment_name": "",
        "biological_reference": "",
        "compartment_description": "",
    },
    "inter_compartmental_connections": {
        "source_compartment": "",
        "target_compartment": "",
        "connection_type": "Blood flow",
    },
    "model_implementation_reference": {
        "implementation_type": "SBML",
        "implementation_location": "model/model.xml",
    },
    "digital_artifacts": {
        "artifact_name": "",
        "artifact_type": "Model code",
        "artifact_format": "SBML",
        "artifact_location": "",
        "artifact_description": "",
    },
}


def list_templates() -> Dict[str, Any]:
    return {
        "api_version": "v1",
        "kind": "pbpk.form_templates.index",
        "templates": sorted(list(_TEMPLATES.keys())),
    }


def get_template(name: str) -> Dict[str, Any]:
    if name not in _TEMPLATES:
        raise KeyError(name)
    return {
        "api_version": "v1",
        "kind": "pbpk.form_template",
        "name": name,
        "value": _TEMPLATES[name],
    }