"""C06 / RF-09: review operations are reachable through the extraction API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.extraction.group_validator import validate_proposed_group
from backend.app.extraction.router import extraction_router


def _client():
    app = FastAPI()
    app.include_router(extraction_router)
    return TestClient(app)


def _group(name, quantity, snippet):
    group, defective = validate_proposed_group(
        {"name": name, "quantity": quantity, "unit_area_m2": 35, "source_fragment": snippet}
    )
    assert defective is None
    return group.model_dump(mode="json")


def _state(*groups):
    return {
        "original_text": "2 oficinas de 35 m² y otras 2 oficinas de 35 m²",
        "revisable_groups": list(groups),
        "defective_groups": [],
        "confirmed_groups": [],
        "discarded_groups": [],
    }


def test_review_actions_are_exposed_and_keep_provenance_and_confirmed_state():
    client = _client()
    first = _group("oficinas", 2, "2 oficinas de 35 m²")
    second = _group("oficinas", 2, "otras 2 oficinas de 35 m²")
    state = _state(first, second)

    merged = client.post(
        "/extraction/review/merge",
        json={"session": state, "action": {"group_id_1": first["id"], "group_id_2": second["id"]}},
    )
    assert merged.status_code == 200
    state = merged.json()
    assert len(state["revisable_groups"]) == 1
    merged_group = state["revisable_groups"][0]
    assert merged_group["attributes"]["quantity"]["source_fragment"]

    split = client.post(
        "/extraction/review/split",
        json={"session": state, "action": {"group_id": merged_group["id"], "split_quantities": [1, 3]}},
    )
    assert split.status_code == 200
    state = split.json()
    assert len(state["revisable_groups"]) == 2

    discard = client.post(
        "/extraction/review/discard",
        json={"session": state, "action": {"group_id": state["revisable_groups"][0]["id"]}},
    )
    assert discard.status_code == 200
    state = discard.json()
    assert len(state["discarded_groups"]) == 1
    assert len(state["revisable_groups"]) == 1

    remaining = state["revisable_groups"][0]
    corrected = client.post(
        "/extraction/review/correct",
        json={"session": state, "action": {"group_id": remaining["id"], "attribute_name": "quantity", "new_value": 3}},
    )
    assert corrected.status_code == 200
    state = corrected.json()
    assert state["revisable_groups"][0]["attributes"]["quantity"]["condition"] == "human_corrected"

    confirm = client.post(
        "/extraction/review/confirm",
        json={"session": state, "action": {"group_id": remaining["id"]}},
    )
    assert confirm.status_code == 200
    state = confirm.json()
    assert state["original_text"] == _state()["original_text"]
    assert len(state["confirmed_groups"]) == 1
    assert state["revisable_groups"] == []


def test_review_invalid_group_returns_client_error():
    response = _client().post(
        "/extraction/review/confirm",
        json={"session": _state(), "action": {"group_id": "missing"}},
    )
    assert response.status_code == 400
