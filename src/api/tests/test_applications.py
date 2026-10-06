"""Candidate application repository, service, and endpoint behavior."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import CosmosSettings
from app.dependencies.services import get_application_service
from app.domain import JobStatus
from app.main import app
from app.repositories import CosmosApplicationRepository, InMemoryRepository
from app.services import ApplicationService, CrudService
from app.services.applications import MAX_RESUME_BYTES, clean_file_name
from job_fixtures import create_sample_jobs

PDF = b"%PDF-1.7\n1 0 obj << >> endobj\n%%EOF"


class FakeApplicationsContainer:
    """Container double accepting only the arguments the Cosmos SDK honors."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self.fail_create = False

    async def create_item(self, body: dict[str, Any]) -> dict[str, Any]:
        if self.fail_create:
            raise RuntimeError("Cosmos DB unavailable")
        self.items.append(body.copy())
        return body.copy()

    def query_items(self, query: str, *, parameters: list[dict[str, Any]], partition_key: str | None = None) -> Any:
        value = parameters[0]["value"]
        if "c.jobId" in query:
            assert partition_key == value
            matches = sorted((i for i in self.items if i["jobId"] == value), key=lambda i: i["submittedAt"], reverse=True)
        else:
            assert partition_key is None
            matches = [i for i in self.items if i["id"] == value]

        async def results() -> Any:
            for item in matches:
                yield item.copy()

        return results()


class FakeResumeStore:
    container_name = "resumes"

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}

    async def upload(self, blob_name: str, data: bytes) -> None:
        assert blob_name not in self.blobs
        self.blobs[blob_name] = data

    async def download(self, blob_name: str) -> bytes:
        return self.blobs[blob_name]

    async def delete(self, blob_name: str) -> None:
        del self.blobs[blob_name]


def make_service() -> tuple[ApplicationService, CrudService, FakeApplicationsContainer, FakeResumeStore]:
    jobs = CrudService(InMemoryRepository(create_sample_jobs()), "Job")
    container = FakeApplicationsContainer()
    repository = CosmosApplicationRepository(client=None, settings=CosmosSettings(endpoint="https://example"))  # type: ignore[arg-type]
    repository._container = container
    resumes = FakeResumeStore()
    return ApplicationService(jobs, repository, resumes), jobs, container, resumes


@pytest.mark.asyncio
async def test_submit_stores_resume_and_application() -> None:
    service, jobs, container, resumes = make_service()
    before = (await jobs.get("senior-product-designer")).applicant_count

    application = await service.submit("senior-product-designer", " Ada Lovelace ", "ada@example.com", "Hello", "C:\\docs\\Ada CV.pdf", PDF)

    blob_name = f"{application.id}.pdf"
    assert resumes.blobs[blob_name] == PDF
    assert application.resume_blob_path == f"resumes/{blob_name}"
    assert application.resume_file_name == "Ada CV.pdf"
    assert application.candidate_name == "Ada Lovelace"
    assert container.items[0]["jobId"] == "senior-product-designer"
    assert "candidateEmail" in container.items[0]
    assert (await jobs.get("senior-product-designer")).applicant_count == before + 1
    assert await service.get(application.id) == application
    assert await service.list_for_job("senior-product-designer") == [application]
    assert await service.list_for_job("frontend-engineer") == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("job_id", "data", "message"),
    [
        ("ai-platform-engineer", PDF, "not accepting"),
        ("senior-product-designer", b"", "empty"),
        ("senior-product-designer", b"PK\x03\x04 not a pdf", "PDF"),
        ("senior-product-designer", b"%PDF-" + b"0" * MAX_RESUME_BYTES, "5 MB"),
    ],
    ids=["unpublished-job", "empty-file", "not-a-pdf", "too-large"],
)
async def test_submit_rejects_invalid_applications(job_id: str, data: bytes, message: str) -> None:
    service, _, container, resumes = make_service()
    with pytest.raises(ValueError, match=message):
        await service.submit(job_id, "Ada", "ada@example.com", "", "cv.pdf", data)
    assert container.items == [] and resumes.blobs == {}


@pytest.mark.asyncio
async def test_failed_record_removes_uploaded_resume() -> None:
    service, _, container, resumes = make_service()
    container.fail_create = True
    with pytest.raises(RuntimeError):
        await service.submit("senior-product-designer", "Ada", "ada@example.com", "", "cv.pdf", PDF)
    assert resumes.blobs == {}


def test_clean_file_name() -> None:
    assert clean_file_name("../../etc/passwd") == "passwd.pdf"
    assert clean_file_name(None) == "resume.pdf"
    assert clean_file_name("Résumé <final>.PDF") == "Résumé _final_.PDF"


def test_application_endpoints() -> None:
    service, _, _, _ = make_service()
    app.dependency_overrides[get_application_service] = lambda: service
    try:
        client = TestClient(app)
        form = {"candidateName": "Ada Lovelace", "candidateEmail": "ada@example.com", "message": "I would love to join."}
        created = client.post("/jobs/senior-product-designer/applications", data=form, files={"resume": ("ada.pdf", PDF, "application/pdf")})
        assert created.status_code == 201, created.text
        body = created.json()
        assert set(body) == {"id", "jobId", "candidateName", "candidateEmail", "message", "resumeFileName", "resumeBlobPath", "submittedAt"}

        listed = client.get("/jobs/senior-product-designer/applications")
        assert [item["id"] for item in listed.json()] == [body["id"]]
        assert client.get(f"/applications/{body['id']}").json()["candidateEmail"] == "ada@example.com"

        resume = client.get(f"/applications/{body['id']}/resume")
        assert resume.status_code == 200
        assert resume.content == PDF
        assert resume.headers["content-type"] == "application/pdf"
        assert "ada.pdf" in resume.headers["content-disposition"]

        assert client.get("/applications/missing").status_code == 404
        assert client.post("/jobs/missing/applications", data=form, files={"resume": ("a.pdf", PDF, "application/pdf")}).status_code == 404
        assert client.post("/jobs/ai-platform-engineer/applications", data=form, files={"resume": ("a.pdf", PDF, "application/pdf")}).status_code == 400
        assert client.post("/jobs/senior-product-designer/applications", data={**form, "candidateEmail": "nope"}, files={"resume": ("a.pdf", PDF, "application/pdf")}).status_code == 422
        assert client.post("/jobs/senior-product-designer/applications", data=form).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_sample_jobs_include_open_and_closed_roles() -> None:
    statuses = {job.id: job.status for job in create_sample_jobs()}
    assert statuses["senior-product-designer"] == JobStatus.PUBLISHED
    assert statuses["ai-platform-engineer"] != JobStatus.PUBLISHED
