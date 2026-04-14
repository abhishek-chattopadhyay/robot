"""Tests for qaop_validation package."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "packages" / "qaop-metadata-spec" / "tests" / "fixtures"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "packages" / "qaop_validation" / "schemas" / "qaop-metadata.schema.json"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "packages" / "qaop-metadata-spec" / "jsonld" / "qaop-core-template.jsonld"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestValidateQaopMetadata:
    def test_valid_cisplatin_returns_no_errors(self):
        from qaop_validation.validator import validate_qaop_metadata

        fixture = _load(FIXTURES_DIR / "valid-cisplatin-aop472.json")
        errors, warnings = validate_qaop_metadata(fixture, schema_path=SCHEMA_PATH)
        assert errors == [], f"Valid fixture should pass: {errors}"
        assert warnings == []

    def test_empty_object_returns_errors(self):
        from qaop_validation.validator import validate_qaop_metadata

        errors, warnings = validate_qaop_metadata({}, schema_path=SCHEMA_PATH)
        assert len(errors) > 0, "Empty metadata should fail validation"
        # Should include required field violations
        paths = [e["path"] for e in errors]
        assert "/" in paths  # root-level required fields

    def test_schema_only_no_domain_lint(self):
        from qaop_validation.validator import validate_qaop_metadata

        fixture = _load(FIXTURES_DIR / "valid-cisplatin-aop472.json")
        errors, warnings = validate_qaop_metadata(fixture, schema_path=SCHEMA_PATH)
        # v1: no domain lint, so warnings always empty
        assert warnings == []


class TestQaopCoreTemplate:
    def test_template_has_graph(self):
        tpl = _load(TEMPLATE_PATH)
        assert "@graph" in tpl

    def test_template_has_metadata_descriptor(self):
        tpl = _load(TEMPLATE_PATH)
        ids = {n["@id"] for n in tpl["@graph"]}
        assert "ro-crate-metadata.json" in ids

    def test_template_has_dataset_root(self):
        tpl = _load(TEMPLATE_PATH)
        ids = {n["@id"] for n in tpl["@graph"]}
        assert "./" in ids

    def test_template_has_qaop_model_node(self):
        tpl = _load(TEMPLATE_PATH)
        idx = {n["@id"]: n for n in tpl["@graph"]}
        assert "#qaop-model" in idx
        assert idx["#qaop-model"]["@type"] == "AdverseOutcomePathway"
