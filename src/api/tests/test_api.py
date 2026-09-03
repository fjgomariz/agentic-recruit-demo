"""Behavior checks for the initial in-memory API."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_seeded_collections_and_openapi() -> None:
    assert len(client.get("/jobs").json()) >= 1
    assert len(client.get("/candidates").json()) >= 1
    assert len(client.get("/evaluations").json()) >= 1
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    for resource in ("jobs", "candidates", "evaluations"):
        assert {"get", "post"} <= paths[f"/{resource}"].keys()
        assert {"get", "put"} <= paths[f"/{resource}/{{{resource[:-1]}_id}}"].keys()
    job_properties = openapi.json()["components"]["schemas"]["Job"]["properties"]
    assert "employmentType" in job_properties
    assert "employment_type" not in job_properties


def test_candidate_crud_and_error_responses() -> None:
    candidate = {"id": "alex-rivera", "firstName": "Alex", "lastName": "Rivera", "email": "alex@example.demo", "location": "Madrid, ES"}
    created = client.post("/candidates", json=candidate)
    assert created.status_code == 201
    candidate["location"] = "Barcelona, ES"
    updated = client.put("/candidates/alex-rivera", json=candidate)
    assert updated.status_code == 200
    assert updated.json()["location"] == "Barcelona, ES"
    assert client.get("/candidates/missing").status_code == 404
    assert client.post("/candidates", json=candidate).status_code == 409