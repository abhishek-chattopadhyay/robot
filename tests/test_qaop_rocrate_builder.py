"""Tests for qAOP RO-Crate builder."""

import json
import tempfile
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "packages" / "qaop-metadata-spec" / "tests" / "fixtures"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "packages" / "qaop-metadata-spec" / "jsonld" / "qaop-core-template.jsonld"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _build_crate(fixture_name="valid-cisplatin-aop472.json"):
    from pbpk_backend.qaop_rocrate_builder import build_rocrate_from_qaop_metadata

    fix = _load(FIXTURES_DIR / fixture_name)
    td = tempfile.mkdtemp()
    res = build_rocrate_from_qaop_metadata(fix, Path(td), template_path=TEMPLATE_PATH)
    crate = _load(Path(td) / "ro-crate-metadata.json")
    graph = {n["@id"]: n for n in crate["@graph"]}
    return res, crate, graph, Path(td)


class TestBuildResult:
    def test_produces_rocrate_metadata(self):
        res, crate, graph, td = _build_crate()
        assert (td / "ro-crate-metadata.json").exists()

    def test_produces_qaop_metadata(self):
        res, crate, graph, td = _build_crate()
        assert (td / "qaop-metadata.json").exists()

    def test_returns_build_result(self):
        res, crate, graph, td = _build_crate()
        assert res.crate_dir == td
        assert res.metadata_path == td / "qaop-metadata.json"


class TestAOPRoot:
    def test_aop_type(self):
        _, _, graph, _ = _build_crate()
        assert graph["#qaop-model"]["@type"] == "AdverseOutcomePathway"

    def test_aop_name_from_identity(self):
        _, _, graph, _ = _build_crate()
        assert graph["#qaop-model"]["name"] == "DNA adduct formation leading to kidney failure"


class TestKENodes:
    def test_mie_has_correct_type(self):
        _, _, graph, _ = _build_crate()
        # KE 1194 is MIE
        assert graph["#ke-1194"]["@type"] == "MolecularInitiatingEvent"

    def test_regular_ke_has_correct_type(self):
        _, _, graph, _ = _build_crate()
        # KE 1670 is regular KE
        assert graph["#ke-1670"]["@type"] == "KeyEvent"

    def test_ao_has_correct_type(self):
        _, _, graph, _ = _build_crate()
        # KE 2208 is AO
        assert graph["#ke-2208"]["@type"] == "AdverseOutcome"

    def test_ke_id_derived_from_aopwiki(self):
        _, _, graph, _ = _build_crate()
        assert "#ke-1194" in graph
        assert "#ke-1670" in graph
        assert "#ke-2208" in graph

    def test_ke_threshold_inlined(self):
        _, _, graph, _ = _build_crate()
        # KE 1670 has threshold data
        ke = graph["#ke-1670"]
        assert ke["thresholdValue"] == 10.0
        assert ke["unitText"] == "uM"
        assert ke["thresholdBasis"] == "EC10"


class TestKERNodes:
    def test_ker_exists(self):
        _, _, graph, _ = _build_crate()
        ker_nodes = [n for nid, n in graph.items() if nid.startswith("#ker-")]
        assert len(ker_nodes) > 0

    def test_ker_references_upstream_ke(self):
        _, _, graph, _ = _build_crate()
        ker = graph["#ker-1001"]
        assert ker["hasUpstreamKeyEvent"] == {"@id": "#ke-1194"}

    def test_ker_references_downstream_ke(self):
        _, _, graph, _ = _build_crate()
        ker = graph["#ker-1001"]
        assert ker["hasDownstreamKeyEvent"] == {"@id": "#ke-1670"}

    def test_ker_has_response_response_function(self):
        _, _, graph, _ = _build_crate()
        ker = graph["#ker-1001"]
        assert "responseResponseFunction" in ker

    def test_ker_has_provenance(self):
        _, _, graph, _ = _build_crate()
        ker = graph["#ker-1001"]
        assert ker["experimentalSystem"] == "in vitro"
        assert ker["qaop:species"] == "human"


class TestApplicability:
    def test_applicability_on_aop_root(self):
        _, _, graph, _ = _build_crate()
        aop = graph["#qaop-model"]
        assert "qaop:taxonomicApplicability" in aop
        assert "qaop:chemicalStressors" in aop
