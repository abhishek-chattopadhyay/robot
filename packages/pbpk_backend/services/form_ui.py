from __future__ import annotations

from typing import Any, Dict, List, Optional

from pbpk_backend.services.form_spec import compile_pbpk_form_spec, compile_pbpk_form_registry
from pbpk_backend.services.hydrate import hydrate_pbpk_form, hydrate_pbpk_form_from_draft


def _widget_for_field(f: Dict[str, Any]) -> str:
    vt = f.get("value_type")
    card = f.get("cardinality", "one")
    allowed = f.get("allowed_values") or []
    vocab = f.get("vocabulary")

    if vt in ("text", "controlled_text"):
        return "textarea"

    if vt in ("controlled_term",):
        if vocab or allowed:
            return "multiselect" if card == "many" else "select"
        return "input"

    if vt == "ke_reference":
        return "ke_select"

    if vt == "uri":
        return "multi_url" if card == "many" else "url"

    if vt == "number":
        return "number"

    if vt == "object":
        return "group"

    # string and everything else
    return "multi_input" if card == "many" else "input"


def build_form_ui_pbpk(
    *,
    metadata: Optional[Dict[str, Any]] = None,
    draft_id: Optional[str] = None,
    include_helptexts: bool = False,
    include_vocabularies: bool = True,
) -> Dict[str, Any]:
    if (metadata is None) == (draft_id is None):
        raise ValueError("Provide exactly one of metadata or draft_id")

    spec = compile_pbpk_form_spec(include_helptexts=include_helptexts, include_vocabularies=include_vocabularies)
    reg = compile_pbpk_form_registry(include_helptexts=include_helptexts, include_vocabularies=include_vocabularies)

    if draft_id is not None:
        hydrated = hydrate_pbpk_form_from_draft(draft_id=draft_id, include_helptexts=include_helptexts)
    else:
        hydrated = hydrate_pbpk_form(metadata=metadata or {}, include_helptexts=include_helptexts)

    # index hydration by path for fast lookup
    hv_by_path = {f["path"]: f for f in hydrated["fields"]}

    ui_sections: List[Dict[str, Any]] = []
    for sec in spec.get("sections", []):
        out_sec = {
            "id": sec.get("id"),
            "title": sec.get("title"),
            "description": sec.get("description"),
            "fields": [],
        }

        for f in sec.get("fields", []):
            path = f.get("path")
            hv = hv_by_path.get(path, {})
            out_f = dict(f)

            out_f["widget"] = _widget_for_field(f)
            out_f["value"] = hv.get("value")
            out_f["missing"] = bool(hv.get("missing", False))

            # Add resolved vocabulary values (already resolved by registry)
            if f.get("vocabulary"):
                vocab_name = f["vocabulary"]
                out_f["vocabulary_values"] = (reg.get("vocabularies") or {}).get(vocab_name)

            out_sec["fields"].append(out_f)

        ui_sections.append(out_sec)

    return {
        "api_version": "v1",
        "kind": "pbpk.form_ui",
        "draft_id": draft_id,
        "sections": ui_sections,
        "helptexts": spec.get("helptexts") if include_helptexts else None,
        "registry_issues": (reg.get("registry") or {}).get("issues", []),
    }