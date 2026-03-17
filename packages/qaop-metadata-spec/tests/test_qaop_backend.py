"""Backend integration tests for qAOP form spec compilation."""

from __future__ import annotations

import pytest

from pbpk_backend.services.form_spec import (
    compile_form_spec,
    compile_form_registry,
    compile_pbpk_form_spec,
)
from pbpk_backend.services.form_ui import _widget_for_field


# --- compile_form_spec dispatch ---


def test_compile_qaop_form_spec():
    """compile_form_spec(model_type='qaop') returns spec with 4 sections."""
    spec = compile_form_spec(model_type="qaop")
    assert spec["api_version"] == "v1"
    assert spec["kind"] == "qaop.form_spec"
    section_ids = [s["id"] for s in spec["sections"]]
    assert section_ids == ["identity", "structure", "quantitative", "applicability"]


def test_compile_pbpk_unchanged():
    """compile_form_spec(model_type='pbpk') returns same result as compile_pbpk_form_spec()."""
    generic = compile_form_spec(model_type="pbpk")
    original = compile_pbpk_form_spec()
    assert generic["kind"] == original["kind"]
    assert generic["sections"] == original["sections"]
    assert generic["logic"] == original["logic"]


def test_compile_default_is_pbpk():
    """compile_form_spec() with no model_type defaults to pbpk."""
    default = compile_form_spec()
    pbpk = compile_form_spec(model_type="pbpk")
    assert default["kind"] == pbpk["kind"]
    assert default["sections"] == pbpk["sections"]


# --- compile_form_registry dispatch ---


def test_qaop_registry():
    """compile_form_registry(model_type='qaop') returns registry with ke_reference fields."""
    result = compile_form_registry(model_type="qaop")
    assert result["api_version"] == "v1"
    assert result["kind"] == "qaop.form_registry"
    reg = result["registry"]
    # Find fields with ke_reference value_type
    ke_ref_fields = [
        f for f in reg["fields_by_key"].values() if f.get("value_type") == "ke_reference"
    ]
    assert len(ke_ref_fields) >= 2, "Expected at least upstream_ke_id and downstream_ke_id"


# --- _widget_for_field extension ---


def test_widget_ke_reference():
    """_widget_for_field with value_type=ke_reference returns 'ke_select'."""
    field = {"value_type": "ke_reference"}
    assert _widget_for_field(field) == "ke_select"


def test_widget_show_when_not_crash():
    """_widget_for_field handles fields with show_when property without error."""
    field = {
        "value_type": "string",
        "show_when": {"field": "function_type", "equals": "custom"},
    }
    widget = _widget_for_field(field)
    assert isinstance(widget, str)
