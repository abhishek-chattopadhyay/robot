from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set


@dataclass
class LintWarning:
    code: str
    message: str
    path: str  # JSON pointer-ish path


_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{4}$")
_URLISH_RE = re.compile(r"^(https?://|doi:|DOI:)")


def _get(obj: Dict[str, Any], *keys: str, default=None):
    cur: Any = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def lint(pbpk: Dict[str, Any]) -> List[LintWarning]:
    warnings: List[LintWarning] = []

    # ---- Gather reference sets ----
    chemicals: Set[str] = set()
    for i, chem in enumerate(_get(pbpk, "chemical_description", "chemicals", default=[]) or []):
        name = chem.get("chemical_name")
        if isinstance(name, str) and name.strip():
            chemicals.add(name.strip())

    compartments: Set[str] = set()
    biosystems = _get(pbpk, "biological_system_description", "biological_systems", default=[]) or []
    for i, bs in enumerate(biosystems):
        for c in (bs.get("compartments") or []):
            if isinstance(c, str) and c.strip():
                compartments.add(c.strip())

    artifacts: Set[str] = set()
    for i, art in enumerate(_get(pbpk, "electronic_files_and_reproducibility", "digital_artifacts", default=[]) or []):
        loc = art.get("artifact_location")
        if isinstance(loc, str) and loc.strip():
            artifacts.add(loc.strip())

    impl_refs: Set[str] = set()
    for i, ref in enumerate(_get(pbpk, "model_structure_and_representation", "model_implementation_reference", default=[]) or []):
        loc = ref.get("implementation_location")
        if isinstance(loc, str) and loc.strip():
            impl_refs.add(loc.strip())

    # ---- W1: ORCID formatting ----
    authors = _get(pbpk, "general_model_information", "model_authors", default=[]) or []
    for i, a in enumerate(authors):
        orcid = a.get("orcid")
        if isinstance(orcid, str) and orcid.strip():
            if not _ORCID_RE.match(orcid.strip()):
                warnings.append(
                    LintWarning(
                        code="W1",
                        path=f"/general_model_information/model_authors/{i}/orcid",
                        message=f"ORCID '{orcid}' does not match expected pattern '0000-0000-0000-0000'."
                    )
                )

    # ---- W2: model availability looks like URL/DOI ----
    avail = _get(pbpk, "general_model_information", "model_availability", default=[]) or []
    for i, v in enumerate(avail):
        if isinstance(v, str) and v.strip():
            if not _URLISH_RE.match(v.strip()):
                warnings.append(
                    LintWarning(
                        code="W2",
                        path=f"/general_model_information/model_availability/{i}",
                        message=f"Model availability entry '{v}' does not look like a URL or DOI (expected to start with http(s):// or DOI:)."
                    )
                )

    # ---- W3/W4: parameters reference known chemicals/compartments ----
    params = _get(pbpk, "parameterisation", "parameters", default=[]) or []
    for i, p in enumerate(params):
        # chemicals
        for j, cname in enumerate(p.get("applicable_chemicals") or []):
            if isinstance(cname, str) and cname.strip():
                if chemicals and cname.strip() not in chemicals:
                    warnings.append(
                        LintWarning(
                            code="W3",
                            path=f"/parameterisation/parameters/{i}/applicable_chemicals/{j}",
                            message=f"Parameter references chemical '{cname}', but it is not listed in chemical_description.chemicals."
                        )
                    )
        # compartments
        for j, comp in enumerate(p.get("applicable_compartments") or []):
            if isinstance(comp, str) and comp.strip():
                if compartments and comp.strip() not in compartments:
                    warnings.append(
                        LintWarning(
                            code="W4",
                            path=f"/parameterisation/parameters/{i}/applicable_compartments/{j}",
                            message=f"Parameter references compartment '{comp}', but it is not listed in any biological system compartments."
                        )
                    )

    # ---- W5: implementation files should appear as artifacts ----
    # (only warn if both exist; avoid noise if user hasn't listed artifacts yet)
    if impl_refs and artifacts:
        missing = sorted(impl_refs - artifacts)
        for loc in missing:
            warnings.append(
                LintWarning(
                    code="W5",
                    path="/model_structure_and_representation/model_implementation_reference",
                    message=f"Implementation reference '{loc}' is not present in electronic_files_and_reproducibility.digital_artifacts.artifact_location."
                )
            )

    # ---- W6: evaluation activity missing evaluation_data ----
    evals = _get(pbpk, "model_evaluation_and_validation", "evaluation_activities", default=[]) or []
    for i, e in enumerate(evals):
        if not (isinstance(e.get("evaluation_data"), str) and e.get("evaluation_data").strip()):
            warnings.append(
                LintWarning(
                    code="W6",
                    path=f"/model_evaluation_and_validation/evaluation_activities/{i}/evaluation_data",
                    message="Evaluation activity has no evaluation_data. Consider adding dataset details or a reference."
                )
            )

    # ---- W7: multiple species but no species-scoped parameters (heuristic) ----
    if len(biosystems) > 1:
        any_species_scope = any(
            isinstance(p.get("parameter_scope"), str) and "species" in p.get("parameter_scope").lower()
            for p in params
        )
        if not any_species_scope:
            warnings.append(
                LintWarning(
                    code="W7",
                    path="/parameterisation/parameters",
                    message="Multiple biological systems (species contexts) declared, but no parameters appear to be species-specific (heuristic)."
                )
            )

    return warnings