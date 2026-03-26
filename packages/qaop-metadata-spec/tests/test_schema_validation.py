"""Schema validation test suite for qAOP metadata.

Tests cover:
- SCHM-01: Valid qAOP JSON passes validation
- SCHM-02: Missing required fields rejected
- SCHM-03: Invalid controlled vocabulary values rejected
- JSON-LD context structure
- additionalProperties enforcement
"""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
JSONLD_PATH = Path(__file__).parent.parent / "jsonld" / "qaop-context.jsonld"


def load_fixture(name):
    return json.loads((FIXTURES_DIR / name).read_text())


# --- SCHM-01: Valid data passes ---


def test_valid_cisplatin_passes(validator, valid_cisplatin):
    errors = list(validator.iter_errors(valid_cisplatin))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


# --- SCHM-02: Required fields enforced ---


def test_missing_title_rejected(validator):
    instance = load_fixture("invalid-missing-title.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0
    messages = " ".join(e.message for e in errors)
    assert "title" in messages


def test_empty_kes_rejected(validator):
    instance = load_fixture("invalid-no-kes.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0


def test_empty_kers_rejected(validator):
    instance = load_fixture("invalid-no-kers.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0


def test_no_mie_rejected(validator):
    instance = load_fixture("invalid-no-mie.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0


def test_no_ao_rejected(validator):
    instance = load_fixture("invalid-no-ao.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0


# --- SCHM-03: Controlled vocabularies enforced ---


def test_invalid_bio_level_rejected(validator):
    instance = load_fixture("invalid-bad-bio-level.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0
    all_messages = " ".join(str(e.message) for e in errors)
    assert "subcellular" in all_messages


def test_invalid_function_type_rejected(validator):
    instance = load_fixture("invalid-bad-function-type.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0
    all_messages = " ".join(str(e.message) for e in errors)
    assert "exponential" in all_messages


def test_invalid_status_rejected(validator):
    instance = load_fixture("invalid-bad-status.json")
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0
    all_messages = " ".join(str(e.message) for e in errors)
    assert "draft" in all_messages


# --- JSON-LD context structure ---


def test_jsonld_context_structure():
    context_doc = json.loads(JSONLD_PATH.read_text())
    ctx = context_doc["@context"]
    assert isinstance(ctx, list), "@context should be an array"
    assert ctx[0] == "https://w3id.org/ro/crate/1.1/context"
    overlay = ctx[1]
    assert "aopo" in overlay, "AOPO namespace must be defined"
    assert "AdverseOutcomePathway" in overlay
    assert "KeyEvent" in overlay
    assert "KeyEventRelationship" in overlay


# --- additionalProperties enforcement ---


def test_additional_properties_rejected(validator, valid_cisplatin):
    invalid = {**valid_cisplatin, "unknown_field": "test"}
    errors = list(validator.iter_errors(invalid))
    assert len(errors) > 0
    all_messages = " ".join(str(e.message) for e in errors)
    assert "unknown_field" in all_messages
