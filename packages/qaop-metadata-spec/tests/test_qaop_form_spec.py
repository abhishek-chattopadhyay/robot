"""Form spec validation test suite for qAOP YAML sections.

Tests cover:
- FORM-01: All 4 YAML sections load with id, title, fields
- FORM-02: Field paths align with JSON Schema properties
- FORM-03: KER ke_reference fields present
- FORM-04: show_when conditional visibility
- FORM-05: Help texts on domain-specific fields
- IDENT-01..07: Identity section field coverage
- STRUC-01..05: Structure section field coverage
"""

import json
from pathlib import Path

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
