from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


def _ensure_dict(parent: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        parent[key] = {}
    return parent[key]


def _ensure_list(parent: Dict[str, Any], key: str) -> List[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        parent[key] = []
    return parent[key]


def migrate_pbpk_metadata(metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Normalize legacy / malformed PBPK metadata structures.

    Returns:
      (normalized_metadata, changed)

    Safe and idempotent:
    - can be run many times
    - never raises on malformed user content
    """
    if not isinstance(metadata, dict):
        return metadata, False

    md = deepcopy(metadata)
    changed = False

    # ------------------------------------------------------------------
    # Ensure top-level required containers exist
    # ------------------------------------------------------------------
    mal = _ensure_dict(md, "model_applicability_and_limitations")
    efr = _ensure_dict(md, "electronic_files_and_reproducibility")
    if "model_applicability_and_limitations" not in metadata or not isinstance(metadata.get("model_applicability_and_limitations"), dict):
        changed = True
    if "electronic_files_and_reproducibility" not in metadata or not isinstance(metadata.get("electronic_files_and_reproducibility"), dict):
        changed = True

    # Initialize expected keys so edit paths always have a sane parent
    mal_defaults = {
        "intended_use": "",
        "applicability_domain": "",
        "confidence_statement": "",
        "known_limitations": "",
    }
    for k, v in mal_defaults.items():
        if k not in mal:
            mal[k] = v
            changed = True

    if "digital_artifacts" not in efr or not isinstance(efr.get("digital_artifacts"), list):
        efr["digital_artifacts"] = []
        changed = True
    if "reproducibility_instructions" not in efr or not isinstance(efr.get("reproducibility_instructions"), str):
        efr["reproducibility_instructions"] = ""
        changed = True

    # ------------------------------------------------------------------
    # Chemical identifiers migration
    # Legacy bad shape:
    #   "chemical_identifiers": ["cisplatin"]
    # New shape:
    #   "chemical_identifiers": [{"identifier_type": "Other", "identifier_value": "cisplatin"}]
    # ------------------------------------------------------------------
    chem_desc = _ensure_dict(md, "chemical_description")
    chemicals = chem_desc.get("chemicals")
    if chemicals is None:
        chem_desc["chemicals"] = []
        chemicals = chem_desc["chemicals"]
        changed = True

    if isinstance(chemicals, list):
        normalized_chemicals: List[Any] = []
        for chem in chemicals:
            if not isinstance(chem, dict):
                normalized_chemicals.append(chem)
                continue

            chem_copy = dict(chem)

            ids = chem_copy.get("chemical_identifiers")

            # Missing identifiers -> initialize
            if ids is None:
                chem_copy["chemical_identifiers"] = []
                changed = True

            # Single dict -> wrap in list
            elif isinstance(ids, dict):
                chem_copy["chemical_identifiers"] = [ids]
                changed = True

            # Legacy list or mixed list -> normalize each item
            elif isinstance(ids, list):
                new_ids: List[Dict[str, Any]] = []
                local_changed = False

                for item in ids:
                    if isinstance(item, str):
                        new_ids.append(
                            {
                                "identifier_type": "Other",
                                "identifier_value": item,
                            }
                        )
                        local_changed = True
                    elif isinstance(item, dict):
                        new_item = dict(item)

                        if "identifier_type" not in new_item or not isinstance(new_item.get("identifier_type"), str):
                            new_item["identifier_type"] = "Other"
                            local_changed = True

                        if "identifier_value" not in new_item:
                            new_item["identifier_value"] = ""
                            local_changed = True
                        elif not isinstance(new_item.get("identifier_value"), str):
                            new_item["identifier_value"] = str(new_item.get("identifier_value"))
                            local_changed = True

                        new_ids.append(new_item)
                    else:
                        # Unknown type -> stringify into identifier_value
                        new_ids.append(
                            {
                                "identifier_type": "Other",
                                "identifier_value": str(item),
                            }
                        )
                        local_changed = True

                if local_changed or ids != new_ids:
                    chem_copy["chemical_identifiers"] = new_ids
                    changed = True

            # Any other bad type -> reset to []
            else:
                chem_copy["chemical_identifiers"] = []
                changed = True

            normalized_chemicals.append(chem_copy)

        if normalized_chemicals != chemicals:
            chem_desc["chemicals"] = normalized_chemicals
            changed = True

    return md, changed