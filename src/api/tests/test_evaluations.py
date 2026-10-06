"""Candidate evaluation agent, evaluation workflow, decisions, and agent run records."""

import base64
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import AgentSettings
from app.dependencies.services import get_agent_execution_log, get_application_service, get_evaluation_service
from app.domain import AgentExecution, AgentExecutionStatus, EvaluationRecommendation, EvaluationStatus
from app.main import app
from app.services import CandidateEvaluationAgentService, EvaluationService, JobDescriptionAgentService
from app.services.agents import CandidateEvaluationOutput, build_evaluation_input
from test_applications import PDF, make_service

AGENTS = Path(__file__).resolve().parents[3] / "agents"

EVALUATION = {
    "overallScore": 91,
    "recommendation": "Strong match",
    "summary": "Experienced product designer.",
    "strengths": ["Led design end to end"],
    "considerations": ["Portfolio not linked"],
    "criteria": [{"criterion": "Product design experience", "score": 7, "rationale": "Nine years."}],
}


class FakeResponses:
    def __init__(self, output_text: str = json.dumps(EVALUATION), error: Exception | None = None) -> None:
        self.output_text = output_text
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            id="resp_eval",
            output_text=self.output_text,
            agent_reference={"name": "candidate-evaluator", "version": "4"},
            usage=SimpleNamespace(input_tokens=1200, output_tokens=300),
        )


class Recorder:
    def __init__(self) -> None:
        self.executions: list[AgentExecution] = []

    async def record(self, execution: AgentExecution) -> None:
        self.executions.append(execution)


class ContentFilterError(Exception):
    code = "content_filter"
    status_code = 400
    body = {"content_filters": [{"content_filter_results": {"jailbreak": {"detected": True, "filtered": True}}}]}


def make_evaluation(responses: FakeResponses | None = None, configured: bool = True):
    service, jobs, container, resumes = make_service()
    recorder = Recorder()
    client = SimpleNamespace(responses=responses or FakeResponses()) if configured else None
    agent = CandidateEvaluationAgentService(AgentSettings(project_endpoint="https://example"), client, recorder)
    return EvaluationService(service, agent), service, recorder, (responses or (client.responses if client else None))


async def submit(service) -> Any:
    return await service.submit("senior-product-designer", "Ada Lovelace", "ada@example.com", "Hello", "ada.pdf", PDF)


@pytest.mark.asyncio
async def test_evaluation_sends_pdf_and_job_and_stores_report() -> None:
    evaluations, service, recorder, responses = make_evaluation()
    application = await submit(service)

    await evaluations.start_and_run(application.id)

    call = responses.calls[0]
    assert call["extra_body"]["agent_reference"]["name"] == "candidate-evaluator"
    text, file_part = call["input"][0]["content"]
    assert "Required qualifications:" in text["text"] and "Hello" in text["text"]
    assert file_part["type"] == "input_file" and file_part["filename"] == "ada.pdf"
    assert base64.b64decode(file_part["file_data"].split(",", 1)[1]) == PDF

    evaluation = (await service.get(application.id)).evaluation
    assert evaluation.status == EvaluationStatus.COMPLETED
    assert evaluation.overall_score == 91
    assert evaluation.recommendation == EvaluationRecommendation.STRONG_MATCH
    assert evaluation.agent_version == "4" and evaluation.agent_execution_id == "resp_eval"
    assert evaluation.scores[0].value == 5 and evaluation.scores[0].maximum_value == 5
    assert evaluation.completed_at is not None

    run = recorder.executions[0]
    assert run.status == AgentExecutionStatus.COMPLETED
    assert run.related_entity_ids == [application.id, "senior-product-designer"]
    assert (run.input_tokens, run.output_tokens, run.configuration_version) == (1200, 300, "v4")
    assert "Ada" not in (run.output_summary or "")


@pytest.mark.asyncio
async def test_prompt_injection_blocked_by_content_safety_needs_manual_review() -> None:
    evaluations, service, recorder, _ = make_evaluation(FakeResponses(error=ContentFilterError("blocked")))
    application = await submit(service)

    await evaluations.start_and_run(application.id)

    evaluation = (await service.get(application.id)).evaluation
    assert evaluation.status == EvaluationStatus.NEEDS_REVIEW
    assert evaluation.recommendation == EvaluationRecommendation.NEEDS_MANUAL_REVIEW
    assert evaluation.overall_score is None
    assert "prompt injection" in evaluation.summary
    assert recorder.executions[0].status == AgentExecutionStatus.NEEDS_REVIEW


@pytest.mark.asyncio
async def test_unreadable_pdf_needs_manual_review() -> None:
    class InvalidFileError(Exception):
        code = "invalid_file"
        status_code = 400
        body = {"message": "The file you uploaded is badly formatted or corrupted."}

    evaluations, service, recorder, _ = make_evaluation(FakeResponses(error=InvalidFileError("bad pdf")))
    application = await submit(service)

    await evaluations.start_and_run(application.id)

    evaluation = (await service.get(application.id)).evaluation
    assert evaluation.status == EvaluationStatus.NEEDS_REVIEW
    assert evaluation.recommendation == EvaluationRecommendation.NEEDS_MANUAL_REVIEW
    assert "could not be read" in evaluation.summary and "scanned" in evaluation.considerations[0]
    assert recorder.executions[0].status == AgentExecutionStatus.NEEDS_REVIEW


def test_sdk_client_instrumentor_is_not_enabled() -> None:
    """azure-ai-projects 2.7.0's instrumentor fails agent calls on non-recording spans."""

    source = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert "AIProjectInstrumentor()" not in source


@pytest.mark.asyncio
async def test_invalid_output_marks_evaluation_failed() -> None:
    evaluations, service, recorder, _ = make_evaluation(FakeResponses(output_text='{"overallScore": 50}'))
    application = await submit(service)

    await evaluations.start_and_run(application.id)

    evaluation = (await service.get(application.id)).evaluation
    assert evaluation.status == EvaluationStatus.FAILED and evaluation.error_message
    assert recorder.executions[0].status == AgentExecutionStatus.FAILED


@pytest.mark.asyncio
async def test_unconfigured_agent_leaves_application_pending() -> None:
    evaluations, service, _, _ = make_evaluation(configured=False)
    application = await submit(service)
    await evaluations.start_and_run(application.id)
    assert (await service.get(application.id)).evaluation is None


@pytest.mark.asyncio
async def test_job_description_runs_are_recorded() -> None:
    recorder = Recorder()
    draft = {"summary": "s", "description": "d", "responsibilities": ["r"], "qualifications": ["q"], "preferredQualifications": []}
    responses = FakeResponses(output_text=json.dumps(draft))
    agent = JobDescriptionAgentService(AgentSettings(project_endpoint="https://example"), SimpleNamespace(responses=responses), recorder)
    from app.domain import JobDescriptionRequest

    await agent.generate(JobDescriptionRequest(title="Designer", notes="n"))
    assert recorder.executions[0].agent_name == "job-description-writer"
    assert recorder.executions[0].status == AgentExecutionStatus.COMPLETED


def test_evaluation_input_includes_job_requirements() -> None:
    from job_fixtures import create_sample_jobs
    from app.domain import JobApplication

    job = create_sample_jobs()[0]
    application = JobApplication.model_validate({"id": "a", "jobId": job.id, "candidateName": "X", "candidateEmail": "x@example.com", "resumeFileName": "x.pdf", "resumeBlobPath": "resumes/a.pdf", "submittedAt": "2026-10-06T10:00:00Z"})
    text = build_evaluation_input(job, application)
    assert job.title in text and job.qualifications[0] in text and "(untrusted)" in text
    assert "X" not in text.split("Candidate message")[0]


def test_output_schema_matches_api_model() -> None:
    schema = json.loads((AGENTS / "candidate-evaluator" / "output-schema.json").read_text(encoding="utf-8"))
    fields = {field.alias for field in CandidateEvaluationOutput.model_fields.values()}
    assert set(schema["properties"]) == fields == set(schema["required"])
    assert set(schema["properties"]["recommendation"]["enum"]) == {item.value for item in EvaluationRecommendation}


def test_evaluation_and_decision_endpoints() -> None:
    evaluations, service, recorder, _ = make_evaluation()
    app.dependency_overrides[get_application_service] = lambda: service
    app.dependency_overrides[get_evaluation_service] = lambda: evaluations

    class Log:
        async def list_recent(self, limit: int) -> list[AgentExecution]:
            return recorder.executions[:limit]

    app.dependency_overrides[get_agent_execution_log] = lambda: Log()
    try:
        client = TestClient(app)
        form = {"candidateName": "Ada Lovelace", "candidateEmail": "ada@example.com"}
        created = client.post("/jobs/senior-product-designer/applications", data=form, files={"resume": ("ada.pdf", PDF, "application/pdf")}).json()
        evaluated = client.get(f"/applications/{created['id']}").json()
        assert evaluated["evaluation"]["status"] == "Completed" and evaluated["evaluation"]["overallScore"] == 91

        restarted = client.post(f"/applications/{created['id']}/evaluation")
        assert restarted.status_code == 202
        assert client.get(f"/applications/{created['id']}").json()["evaluation"]["status"] == "Completed"

        decided = client.put(f"/applications/{created['id']}/decision", json={"status": "Advanced", "comment": " Great fit ", "decidedBy": "Jordan Lee"})
        assert decided.status_code == 200
        assert decided.json()["decision"]["status"] == "Advanced" and decided.json()["decision"]["comment"] == "Great fit"
        assert decided.json()["evaluation"]["overallScore"] == 91
        assert client.put(f"/applications/{created['id']}/decision", json={"status": "Maybe"}).status_code == 422
        assert client.delete(f"/applications/{created['id']}/decision").json()["decision"] is None

        runs = client.get("/agent-executions?limit=5").json()
        assert len(runs) == 2 and runs[0]["inputTokens"] == 1200
        assert client.post("/applications/missing/evaluation").status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_running_evaluation_cannot_be_started_twice() -> None:
    evaluations, service, _, _ = make_evaluation()
    application = await submit(service)
    await evaluations.start(application.id)
    with pytest.raises(ValueError, match="already running"):
        await evaluations.start(application.id)
