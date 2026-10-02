"""Job description agent service and endpoint behavior."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import AgentSettings
from app.dependencies.agents import get_job_description_agent
from app.domain import JobDescriptionDraft, JobDescriptionRequest
from app.main import app
from app.services import AgentResponseError, AgentUnavailableError, JobDescriptionAgentService
from app.services.agents import build_agent_input

AGENT_FOLDER = Path(__file__).resolve().parents[3] / "agents" / "job-description-writer"

DRAFT = {
    "summary": "Build the platform behind our AI recruiting products.",
    "description": "You will own our Azure platform.\n\nYou will work with product teams.",
    "responsibilities": ["Operate Azure Container Apps", "Automate deployments"],
    "qualifications": ["5+ years with Azure"],
    "preferredQualifications": [],
}


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(id="resp_123", output_text=self.output_text, agent_reference={"name": "job-description-writer", "version": "3"})


def make_service(output_text: str) -> tuple[JobDescriptionAgentService, FakeResponses]:
    responses = FakeResponses(output_text)
    return JobDescriptionAgentService(AgentSettings(project_endpoint="https://example"), SimpleNamespace(responses=responses)), responses


@pytest.mark.asyncio
async def test_generate_calls_agent_reference_and_parses_draft() -> None:
    service, responses = make_service(json.dumps(DRAFT))
    request = JobDescriptionRequest(title="Cloud Engineer", department="Engineering", experience_level="Senior", notes="Azure, IaC")

    result = await service.generate(request)

    assert result.execution_id == "resp_123"
    assert result.agent_version == "3"
    assert result.draft.responsibilities == DRAFT["responsibilities"]
    call = responses.calls[0]
    assert call["extra_body"] == {"agent_reference": {"name": "job-description-writer", "type": "agent_reference"}}
    assert "model" not in call
    assert "- Title: Cloud Engineer" in call["input"]
    assert "Azure, IaC" in call["input"]


@pytest.mark.asyncio
async def test_generate_rejects_malformed_output() -> None:
    service, _ = make_service('{"summary": "only one field"}')
    with pytest.raises(AgentResponseError):
        await service.generate(JobDescriptionRequest(title="Cloud Engineer"))


@pytest.mark.asyncio
async def test_generate_without_client_is_unavailable() -> None:
    service = JobDescriptionAgentService(AgentSettings(project_endpoint=None), client=None)
    with pytest.raises(AgentUnavailableError):
        await service.generate(JobDescriptionRequest(title="Cloud Engineer"))


def test_agent_input_omits_missing_facts() -> None:
    text = build_agent_input(JobDescriptionRequest(title="Designer"))
    assert "Department" not in text
    assert "(none)" in text


def test_output_schema_matches_api_model() -> None:
    schema = json.loads((AGENT_FOLDER / "output-schema.json").read_text(encoding="utf-8"))
    api_fields = {field.alias or name for name, field in JobDescriptionDraft.model_fields.items()}
    assert set(schema["properties"]) == api_fields
    assert set(schema["required"]) == api_fields
    assert schema["additionalProperties"] is False


def test_endpoint_returns_camel_case_draft_and_maps_errors() -> None:
    service, _ = make_service(json.dumps(DRAFT))
    app.dependency_overrides[get_job_description_agent] = lambda: service
    try:
        client = TestClient(app)
        response = client.post("/job-description-drafts", json={"title": "Cloud Engineer", "experienceLevel": "Senior", "notes": "Azure"})
        assert response.status_code == 200
        body = response.json()
        assert body["executionId"] == "resp_123"
        assert body["draft"]["preferredQualifications"] == []

        assert client.post("/job-description-drafts", json={"title": ""}).status_code == 422

        app.dependency_overrides[get_job_description_agent] = lambda: JobDescriptionAgentService(AgentSettings(project_endpoint=None), None)
        assert client.post("/job-description-drafts", json={"title": "Cloud Engineer"}).status_code == 503
    finally:
        app.dependency_overrides.clear()
