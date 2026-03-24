from __future__ import annotations

import json
from pathlib import Path


def test_ui_is_public_but_pbpk_editor_is_protected(app_client):
    resp = app_client.get("/ui", follow_redirects=False)
    assert resp.status_code == 200

    resp2 = app_client.get("/ui/pbpk", follow_redirects=False)
    assert resp2.status_code in (302, 307)
    assert "/v1/auth/login" in resp2.headers["location"]


def test_migration_normalizes_legacy_chemical_identifiers():
    from pbpk_backend.services.migrations import migrate_pbpk_metadata

    legacy = {
        "general_model_information": {
            "model_name": "x",
            "model_version": "1",
            "model_description": "x",
            "model_authors": [],
            "software_platform": ["SBML"],
            "model_availability": [],
            "license": "CC-BY-4.0",
            "intended_application_category": "x",
        },
        "biological_system_description": {"biological_systems": []},
        "chemical_description": {
            "chemicals": [
                {
                    "chemical_name": "cisplatin",
                    "chemical_role": "Parent compound",
                    "chemical_identifiers": ["cisplatin"],
                }
            ]
        },
        "model_structure_and_representation": {
            "model_structure_description": "x",
            "structural_compartments": [],
            "inter_compartmental_connections": [],
            "mathematical_representation": "x",
            "model_implementation_reference": [],
        },
        "parameterisation": {"parameters": []},
        "model_evaluation_and_validation": {"evaluation_activities": []},
    }

    migrated, changed = migrate_pbpk_metadata(legacy)

    assert changed is True
    ids = migrated["chemical_description"]["chemicals"][0]["chemical_identifiers"]
    assert isinstance(ids, list)
    assert ids[0]["identifier_type"] == "Other"
    assert ids[0]["identifier_value"] == "cisplatin"

    assert "model_applicability_and_limitations" in migrated
    assert "electronic_files_and_reproducibility" in migrated


def test_draft_creation_is_user_scoped(app_client, client_for_user, sample_metadata):
    client_a = client_for_user("0000-0001-1111-1111", "User A")
    resp = client_a.post("/v1/drafts", json=sample_metadata)
    assert resp.status_code == 200, resp.text
    draft_id = resp.json()["draft_id"]

    list_a = client_a.get("/v1/drafts")
    assert list_a.status_code == 200, list_a.text
    items_a = list_a.json()["items"]
    assert any(x["draft_id"] == draft_id for x in items_a)

    client_b = client_for_user("0000-0002-2222-2222", "User B")
    list_b = client_b.get("/v1/drafts")
    assert list_b.status_code == 200, list_b.text
    items_b = list_b.json()["items"]
    assert all(x["draft_id"] != draft_id for x in items_b)


def test_build_from_draft_assigns_crate_owner(temp_data_root, app_client, client_for_user, sample_metadata):
    client_a = client_for_user("0000-0003-3333-3333", "Builder A")

    create_resp = client_a.post("/v1/drafts", json=sample_metadata)
    assert create_resp.status_code == 200, create_resp.text
    draft_id = create_resp.json()["draft_id"]

    build_resp = client_a.post(f"/v1/drafts/{draft_id}/build")
    assert build_resp.status_code == 200, build_resp.text
    crate_id = build_resp.json()["build"]["crate_id"]

    audit_path = temp_data_root / "crates" / crate_id / "audit.json"
    assert audit_path.exists()

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["owner_orcid"] == "0000-0003-3333-3333"

    crates_resp = client_a.get("/v1/crates")
    assert crates_resp.status_code == 200, crates_resp.text
    crates = crates_resp.json()["crates"]
    assert any(x["crate_id"] == crate_id for x in crates)


def test_non_owner_cannot_deposit_someone_elses_crate(app_client, client_for_user, sample_metadata):
    owner_client = client_for_user("0000-0004-4444-4444", "Owner")
    create_resp = owner_client.post("/v1/drafts", json=sample_metadata)
    assert create_resp.status_code == 200, create_resp.text
    draft_id = create_resp.json()["draft_id"]

    build_resp = owner_client.post(f"/v1/drafts/{draft_id}/build")
    assert build_resp.status_code == 200, build_resp.text
    crate_id = build_resp.json()["build"]["crate_id"]

    other_client = client_for_user("0000-0005-5555-5555", "Intruder")
    deposit_resp = other_client.post(
        "/v1/deposit/zenodo",
        json={
            "crate_id": crate_id,
            "token": "fake-token",
            "sandbox": True,
            "publish": False,
        },
    )

    assert deposit_resp.status_code == 403, deposit_resp.text
    assert "access to this crate" in deposit_resp.text.lower()