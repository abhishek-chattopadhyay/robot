"""Form spec validation test suite for qAOP YAML sections.

Tests cover:
- FORM-01: All 4 YAML sections load with id, title, fields
- FORM-02: Field paths align with JSON Schema properties
- FORM-03: KER ke_reference fields present
- FORM-04: show_when conditional visibility
- FORM-05: Help texts on domain-specific fields
- IDENT-01..07: Identity section field coverage
- STRUC-01..05: Structure section field coverage
- QUANT-01..07: Quantitative KER and KE threshold fields
- APPL-01, APPL-04: Applicability species and chemical stressors
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

SECTIONS_DIR = Path(__file__).parent.parent.parent / "qaop-form-spec" / "sections"
SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "qaop-metadata.schema.json"


@pytest.fixture
def qaop_form_sections():
    """Load all YAML form spec sections."""
    sections = {}
    for p in sorted(SECTIONS_DIR.glob("*.yaml")):
        data = yaml.safe_load(p.read_text())
        sections[data["id"]] = data
    return sections


@pytest.fixture
def qaop_schema():
    """Load the qAOP JSON Schema."""
    return json.loads(SCHEMA_PATH.read_text())


def _collect_fields(fields, result=None):
    """Recursively collect all fields into a flat list."""
    if result is None:
        result = []
    for f in fields:
        result.append(f)
        if "fields" in f:
            _collect_fields(f["fields"], result)
    return result


def _field_ids(fields):
    """Get set of field ids from a fields list (top-level only)."""
    return {f["id"] for f in fields}


def _find_field(fields, field_id):
    """Find a field by id in a (possibly nested) field list."""
    for f in fields:
        if f["id"] == field_id:
            return f
        if "fields" in f:
            found = _find_field(f["fields"], field_id)
            if found:
                return found
    return None


# --- FORM-01: All 4 YAML sections load ---


def test_sections_load(qaop_form_sections):
    """All 4 YAML sections load, each has id, title, fields."""
    assert len(qaop_form_sections) == 4
    for section_id in ("identity", "structure", "quantitative", "applicability"):
        sec = qaop_form_sections[section_id]
        assert "id" in sec
        assert "title" in sec
        assert "fields" in sec
        assert isinstance(sec["fields"], list)
        assert len(sec["fields"]) > 0


# --- FORM-02: Field paths align with JSON Schema ---


def test_field_schema_alignment(qaop_form_sections, qaop_schema):
    """Every non-virtual path in form spec maps to a schema property.
    Virtual paths (starting with /structure/_) map to key_event $def fields.
    """
    ke_def_props = set(qaop_schema["$defs"]["key_event"]["properties"].keys())
    ker_def_props = set(qaop_schema["$defs"]["key_event_relationship"]["properties"].keys())

    for section_id, section in qaop_form_sections.items():
        all_fields = _collect_fields(section["fields"])
        for field in all_fields:
            path = field.get("path", "")
            if not path:
                continue

            # Virtual paths for MIE/KE/AO map to key_event $def
            if path.startswith("/structure/_mie/"):
                prop = path.split("/")[-1]
                assert prop in ke_def_props, f"Virtual MIE field '{prop}' not in key_event $def"
            elif path.startswith("/structure/_key_events/"):
                prop = path.split("/")[-1]
                assert prop in ke_def_props, f"Virtual KE field '{prop}' not in key_event $def"
            elif path.startswith("/structure/_ao/"):
                prop = path.split("/")[-1]
                assert prop in ke_def_props, f"Virtual AO field '{prop}' not in key_event $def"
            elif path in ("/structure/_mie", "/structure/_key_events", "/structure/_ao"):
                # Container virtual paths - these are the parent objects
                continue
            else:
                # Non-virtual paths: resolve against schema
                parts = [p for p in path.strip("/").split("/") if p != "*"]
                _resolve_schema_path(qaop_schema, parts, path)


def _resolve_schema_path(schema, parts, full_path):
    """Walk the JSON Schema to verify a path exists."""
    node = schema
    for i, part in enumerate(parts):
        if "properties" in node and part in node["properties"]:
            node = node["properties"][part]
        elif "items" in node:
            # Array items - check properties inside items
            items = node["items"]
            if "$ref" in items:
                ref = items["$ref"]
                def_name = ref.split("/")[-1]
                node = schema["$defs"][def_name]
                if "properties" in node and part in node["properties"]:
                    node = node["properties"][part]
                else:
                    pytest.fail(f"Path '{full_path}': '{part}' not found in $def '{def_name}'")
            elif "properties" in items and part in items["properties"]:
                node = items["properties"][part]
            else:
                pytest.fail(f"Path '{full_path}': '{part}' not in array items properties")
        elif "$ref" in node:
            ref = node["$ref"]
            def_name = ref.split("/")[-1]
            node = schema["$defs"][def_name]
            if "properties" in node and part in node["properties"]:
                node = node["properties"][part]
            else:
                pytest.fail(f"Path '{full_path}': '{part}' not found in $def '{def_name}'")
        else:
            pytest.fail(f"Path '{full_path}': cannot resolve '{part}' at step {i}")


# --- IDENT-01..07: Identity section fields ---


def test_identity_fields(qaop_form_sections):
    """Identity section has fields for all IDENT requirements."""
    identity = qaop_form_sections["identity"]
    fields = identity["fields"]
    top_ids = _field_ids(fields)

    # IDENT-01: title, short_name
    assert "title" in top_ids
    assert "short_name" in top_ids
    title_field = _find_field(fields, "title")
    assert title_field["required"] is True

    # IDENT-02: aop_wiki_id
    assert "aop_wiki_id" in top_ids
    aop_field = _find_field(fields, "aop_wiki_id")
    assert aop_field["value_type"] == "number"
    assert aop_field["required"] is True

    # IDENT-03: authors with children
    assert "authors" in top_ids
    authors_field = _find_field(fields, "authors")
    assert authors_field["cardinality"] == "many"
    author_child_ids = _field_ids(authors_field["fields"])
    assert "full_name" in author_child_ids
    assert "orcid" in author_child_ids
    assert "affiliation" in author_child_ids

    # IDENT-04: description
    assert "description" in top_ids
    desc_field = _find_field(fields, "description")
    assert desc_field["value_type"] == "text"

    # IDENT-05: status
    assert "status" in top_ids
    status_field = _find_field(fields, "status")
    assert status_field["value_type"] == "controlled_term"
    assert len(status_field["allowed_values"]) == 5

    # IDENT-06: version, license
    assert "version" in top_ids
    assert "license" in top_ids

    # IDENT-07: publications with children
    assert "publications" in top_ids
    pub_field = _find_field(fields, "publications")
    assert pub_field["cardinality"] == "many"
    pub_child_ids = _field_ids(pub_field["fields"])
    assert "doi" in pub_child_ids
    assert "pmid" in pub_child_ids


# --- STRUC-01..05: Structure section fields ---


def test_structure_fields(qaop_form_sections):
    """Structure section covers STRUC-01 through STRUC-05."""
    structure = qaop_form_sections["structure"]
    fields = structure["fields"]
    top_ids = _field_ids(fields)

    # STRUC-01: MIE with ke_id, title, bio level, cell_type, organ, process_description
    assert "mie" in top_ids
    mie = _find_field(fields, "mie")
    mie_child_ids = _field_ids(mie["fields"])
    for expected in ("ke_id", "title", "biological_organization_level",
                     "cell_type", "organ", "process_description"):
        assert expected in mie_child_ids, f"MIE missing field: {expected}"

    # STRUC-02: KE with same fields plus measurement_endpoint, measurement_unit
    assert "key_events" in top_ids
    ke = _find_field(fields, "key_events")
    ke_child_ids = _field_ids(ke["fields"])
    for expected in ("ke_id", "title", "biological_organization_level",
                     "cell_type", "organ", "process_description",
                     "measurement_endpoint", "measurement_unit"):
        assert expected in ke_child_ids, f"KE missing field: {expected}"

    # STRUC-03: AO with regulatory_relevance, process_description, measurement fields
    assert "ao" in top_ids
    ao = _find_field(fields, "ao")
    ao_child_ids = _field_ids(ao["fields"])
    for expected in ("ke_id", "title", "biological_organization_level",
                     "regulatory_relevance", "process_description",
                     "measurement_endpoint", "measurement_unit"):
        assert expected in ao_child_ids, f"AO missing field: {expected}"

    # STRUC-04: KER with ker_id, upstream_ke_id (ke_reference), downstream_ke_id (ke_reference)
    assert "key_event_relationships" in top_ids
    ker = _find_field(fields, "key_event_relationships")
    ker_child_ids = _field_ids(ker["fields"])
    assert "ker_id" in ker_child_ids
    assert "upstream_ke_id" in ker_child_ids
    assert "downstream_ke_id" in ker_child_ids
    assert "relationship_description" in ker_child_ids

    upstream = _find_field(ker["fields"], "upstream_ke_id")
    downstream = _find_field(ker["fields"], "downstream_ke_id")
    assert upstream["value_type"] == "ke_reference"
    assert downstream["value_type"] == "ke_reference"

    # STRUC-05: No sequence_number field - KER topology defines ordering
    all_structure_fields = _collect_fields(fields)
    all_ids = {f["id"] for f in all_structure_fields}
    assert "sequence_number" not in all_ids, "No sequence_number field should exist"


# --- FORM-03: KE reference fields ---


def test_ke_reference_fields(qaop_form_sections):
    """KER upstream_ke_id and downstream_ke_id have value_type ke_reference."""
    structure = qaop_form_sections["structure"]
    ker = _find_field(structure["fields"], "key_event_relationships")
    upstream = _find_field(ker["fields"], "upstream_ke_id")
    downstream = _find_field(ker["fields"], "downstream_ke_id")
    assert upstream["value_type"] == "ke_reference"
    assert downstream["value_type"] == "ke_reference"


# --- FORM-04: show_when condition ---


def test_show_when_condition(qaop_form_sections):
    """custom_expression has show_when with field=function_type, equals=custom."""
    structure = qaop_form_sections["structure"]
    custom_expr = _find_field(structure["fields"], "custom_expression")
    assert custom_expr is not None, "custom_expression field must exist"
    assert "show_when" in custom_expr
    sw = custom_expr["show_when"]
    assert sw["field"] == "function_type"
    assert sw["equals"] == "custom"


# --- FORM-05: Help texts ---


def test_help_texts(qaop_form_sections):
    """At least 10 fields have non-empty help text."""
    help_count = 0
    for section in qaop_form_sections.values():
        all_fields = _collect_fields(section["fields"])
        for f in all_fields:
            if f.get("help"):
                help_count += 1
    assert help_count >= 10, f"Only {help_count} fields have help text, need >= 10"


# --- MIE/AO/KE roles map to key_events concept ---


def test_mie_ao_ke_roles(qaop_form_sections):
    """MIE, AO, KE sections are visually distinct but all map to key_events schema concept."""
    structure = qaop_form_sections["structure"]
    mie = _find_field(structure["fields"], "mie")
    ke = _find_field(structure["fields"], "key_events")
    ao = _find_field(structure["fields"], "ao")

    # All three share the core KE fields
    for group_name, group in [("mie", mie), ("ke", ke), ("ao", ao)]:
        child_ids = _field_ids(group["fields"])
        assert "ke_id" in child_ids, f"{group_name} missing ke_id"
        assert "title" in child_ids, f"{group_name} missing title"
        assert "biological_organization_level" in child_ids, f"{group_name} missing bio level"

    # MIE and AO are cardinality one, KE is cardinality many
    assert mie["cardinality"] == "one"
    assert ao["cardinality"] == "one"
    assert ke["cardinality"] == "many"


# --- QUANT-01..07: Quantitative KER and KE threshold fields ---


def test_quantitative_ker_fields(qaop_form_sections):
    """KER has response_response_function with parameters, units, and provenance fields."""
    structure = qaop_form_sections["structure"]
    ker = _find_field(structure["fields"], "key_event_relationships")
    ker_child_ids = _field_ids(ker["fields"])

    # QUANT-01: response_response_function with function_type and custom_expression
    rrf = _find_field(ker["fields"], "response_response_function")
    assert rrf is not None
    rrf_child_ids = _field_ids(rrf["fields"])
    assert "function_type" in rrf_child_ids
    ft = _find_field(rrf["fields"], "function_type")
    assert ft["value_type"] == "controlled_term"
    assert len(ft["allowed_values"]) == 7
    ce = _find_field(rrf["fields"], "custom_expression")
    assert "show_when" in ce

    # QUANT-02: parameters (cardinality many) with child fields
    assert "parameters" in rrf_child_ids
    params = _find_field(rrf["fields"], "parameters")
    assert params["cardinality"] == "many"
    param_child_ids = _field_ids(params["fields"])
    for expected in ("name", "value", "unit",
                     "confidence_interval_lower", "confidence_interval_upper"):
        assert expected in param_child_ids, f"parameters missing child: {expected}"

    # QUANT-03: upstream_unit and downstream_unit
    assert "upstream_unit" in rrf_child_ids
    assert "downstream_unit" in rrf_child_ids
    up = _find_field(rrf["fields"], "upstream_unit")
    down = _find_field(rrf["fields"], "downstream_unit")
    assert up["value_type"] == "string"
    assert down["value_type"] == "string"

    # QUANT-06: experimental_system and species as KER-level fields
    assert "experimental_system" in ker_child_ids
    es = _find_field(ker["fields"], "experimental_system")
    assert es["value_type"] == "controlled_term"
    assert len(es["allowed_values"]) == 3
    assert "species" in ker_child_ids
    sp = _find_field(ker["fields"], "species")
    assert sp["value_type"] == "string"

    # QUANT-07: data_source as KER-level field
    assert "data_source" in ker_child_ids
    ds = _find_field(ker["fields"], "data_source")
    assert ds["value_type"] == "string"

    # Collapsible flag on response_response_function
    assert rrf.get("collapsible") is True


def test_quantitative_ke_fields(qaop_form_sections):
    """KE thresholds and KE measurement fields are present."""
    structure = qaop_form_sections["structure"]
    ke = _find_field(structure["fields"], "key_events")
    ke_child_ids = _field_ids(ke["fields"])

    # QUANT-04: KE has measurement_endpoint and measurement_unit
    assert "measurement_endpoint" in ke_child_ids
    assert "measurement_unit" in ke_child_ids

    # QUANT-05: quantitative section has ke_thresholds
    quant = qaop_form_sections["quantitative"]
    kt = _find_field(quant["fields"], "ke_thresholds")
    assert kt is not None
    assert kt["cardinality"] == "many"
    kt_child_ids = _field_ids(kt["fields"])
    for expected in ("ke_id", "threshold_value", "threshold_unit",
                     "threshold_basis", "measurement_endpoint", "measurement_unit"):
        assert expected in kt_child_ids, f"ke_thresholds missing: {expected}"

    # ke_id should be ke_reference type
    ke_id = _find_field(kt["fields"], "ke_id")
    assert ke_id["value_type"] == "ke_reference"

    # threshold_basis should be controlled_term with 3 values
    tb = _find_field(kt["fields"], "threshold_basis")
    assert tb["value_type"] == "controlled_term"
    assert set(tb["allowed_values"]) == {"NOAEL", "BMDL", "EC10"}


# --- APPL-01, APPL-04: Applicability fields ---


def test_applicability_fields(qaop_form_sections):
    """Applicability section has species and chemical stressors."""
    appl = qaop_form_sections["applicability"]
    top_ids = _field_ids(appl["fields"])

    # APPL-01: species (cardinality many) with species_name and ncbi_taxonomy_id
    assert "species" in top_ids
    sp = _find_field(appl["fields"], "species")
    assert sp["cardinality"] == "many"
    sp_child_ids = _field_ids(sp["fields"])
    assert "species_name" in sp_child_ids
    assert "ncbi_taxonomy_id" in sp_child_ids

    # APPL-04: chemical_stressors (cardinality many) with name, cas_number, stressor_type
    assert "chemical_stressors" in top_ids
    cs = _find_field(appl["fields"], "chemical_stressors")
    assert cs["cardinality"] == "many"
    cs_child_ids = _field_ids(cs["fields"])
    assert "name" in cs_child_ids
    assert "cas_number" in cs_child_ids
    assert "stressor_type" in cs_child_ids


# --- Fixture validation ---


def test_cisplatin_fixture_validates(qaop_schema):
    """Cisplatin fixture validates against the JSON Schema."""
    fixture_path = Path(__file__).parent / "fixtures" / "valid-cisplatin-aop472.json"
    fixture = json.loads(fixture_path.read_text())
    jsonschema.validate(instance=fixture, schema=qaop_schema)


def test_cisplatin_fixture_has_data_source():
    """Cisplatin fixture KERs have data_source fields."""
    fixture_path = Path(__file__).parent / "fixtures" / "valid-cisplatin-aop472.json"
    fixture = json.loads(fixture_path.read_text())
    kers = fixture["structure"]["key_event_relationships"]
    for ker in kers:
        assert "data_source" in ker, f"KER {ker['ker_id']} missing data_source"
