"""API contract behavior checks."""

import pytest
from fastapi.testclient import TestClient

from app.dependencies.services import get_job_service
from app.main import app
from app.repositories import InMemoryRepository
from job_fixtures import create_sample_jobs
from app.services import CrudService

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_in_memory_job_service() -> None:
    """Keep API behavior tests independent of a live Cosmos DB account."""

    service = CrudService(InMemoryRepository(create_sample_jobs()), "Job")
    app.dependency_overrides[get_job_service] = lambda: service
    yield
    app.dependency_overrides.clear()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_openapi_contract() -> None:
    assert len(client.get("/jobs").json()) >= 1
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    assert {"get", "post"} <= paths["/jobs"].keys()
    assert {"get", "put", "delete"} <= paths["/jobs/{job_id}"].keys()
    assert {"get", "post"} <= paths["/jobs/{job_id}/applications"].keys()
    assert "get" in paths["/applications"]
    assert "get" in paths["/applications/{application_id}"]
    assert "get" in paths["/applications/{application_id}/resume"]
    assert "/candidates" not in paths and "/evaluations" not in paths
    job_properties = openapi.json()["components"]["schemas"]["Job"]["properties"]
    assert "employmentType" in job_properties
    assert "employment_type" not in job_properties


def test_job_crud_and_error_responses() -> None:
    job = create_sample_jobs()[0].model_copy(update={"id": "principal-designer"})
    payload = job.model_dump(mode="json", by_alias=True, exclude_none=True)

    created = client.post("/jobs", json=payload)
    assert created.status_code == 201
    assert client.get("/jobs/principal-designer").json()["title"] == job.title

    payload["title"] = "Principal Product Designer"
    updated = client.put("/jobs/principal-designer", json=payload)
    assert updated.status_code == 200
    assert updated.json()["title"] == "Principal Product Designer"

    assert client.delete("/jobs/principal-designer").status_code == 204
    assert client.get("/jobs/principal-designer").status_code == 404
    assert client.delete("/jobs/principal-designer").status_code == 404