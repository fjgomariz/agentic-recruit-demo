"""Candidate assessment workflow: evaluator, reviewer, recruiter approval, and agent run records."""

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import AgentSettings
from app.dependencies.services import get_agent_execution_log, get_application_service, get_evaluation_service
from app.domain import AgentExecution, AgentExecutionStatus, ApplicationDecisionRequest, EvaluationRecommendation, EvaluationStatus, ReviewAgreement
from app.main import app
from app.services import CandidateEvaluationAgentService, CandidateReviewAgentService, EvaluationService, JobDescriptionAgentService
from app.services.agents import CandidateEvaluationOutput, CandidateReviewOutput, build_evaluation_input
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

REVIEW = {
    "validatedScore": 84,
    "finalRecommendation": "Strong match",
    "agreement": "Partially agrees",
    "confidence": "Medium",
    "summary": "Mostly reliable, slightly generous.",
    "comments": ["Verify portfolio depth in the interview."],
    "inconsistencies": [{"type": "Overconfidence", "severity": "Medium", "description": "Score of 91 is high given no portfolio."}],
}

REVIEWER = "candidate-evaluation-reviewer"


class FakeResponses:
    """Responses API double serving both agents, like the shared production client."""

    def __init__(self, output_text: str = json.dumps(EVALUATION), error: Exception | None = None, review_text: str = json.dumps(REVIEW), review_error: Exception | None = None) -> None:
        self.output_text = output_text
        self.error = error
        self.review_text = review_text
        self.review_error = review_error
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        agent = kwargs["extra_body"]["agent_reference"]["name"]
        if agent == REVIEWER:
            if self.review_error:
                raise self.review_error
            return SimpleNamespace(id="resp_review", output_text=self.review_text, model="gpt-5.4", agent_reference={"name": agent, "version": "2"}, usage=SimpleNamespace(input_tokens=1800, output_tokens=700))
        if self.error:
            raise self.error
        return SimpleNamespace(
            id="resp_eval",
            output_text=self.output_text,
            model="gpt-5.4-mini",
            agent_reference={"name": agent, "version": "4"},
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
    responses = responses or FakeResponses()
    client = SimpleNamespace(responses=responses) if configured else None
    settings = AgentSettings(project_endpoint="https://example")
    evaluator = CandidateEvaluationAgentService(settings, client, recorder)
    reviewer = CandidateReviewAgentService(settings, client, recorder)
    return EvaluationService(service, evaluator, reviewer), service, recorder, responses


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
    assert evaluation.agent_version == "4" and evaluation.agent_execution_id == "resp_eval" and evaluation.model == "gpt-5.4-mini"
    assert evaluation.scores[0].value == 5 and evaluation.scores[0].maximum_value == 5
    assert evaluation.completed_at is not None

    run = recorder.executions[0]
    assert run.status == AgentExecutionStatus.COMPLETED
    assert run.related_entity_ids == [application.id, "senior-product-designer"]
    assert (run.input_tokens, run.output_tokens, run.configuration_version, run.model) == (1200, 300, "v4", "gpt-5.4-mini")
    assert "Ada" not in (run.output_summary or "")


@pytest.mark.asyncio
async def test_reviewer_checks_the_evaluation_with_the_same_evidence() -> None:
    evaluations, service, recorder, responses = make_evaluation()
    application = await submit(service)

    await evaluations.start_and_run(application.id)

    review_call = responses.calls[1]
    assert review_call["extra_body"]["agent_reference"]["name"] == REVIEWER
    text, file_part = review_call["input"][0]["content"]
    assert "Evaluation from the Candidate Evaluator (untrusted JSON)" in text["text"]
    assert '"overallScore": 91' in text["text"] and "Required qualifications:" in text["text"]
    assert base64.b64decode(file_part["file_data"].split(",", 1)[1]) == PDF

    stored = await service.get(application.id)
    review = stored.review
    assert stored.evaluation.status == EvaluationStatus.COMPLETED
    assert review.status == EvaluationStatus.COMPLETED
    assert (review.original_score, review.validated_score) == (91, 84)
    assert review.agreement == ReviewAgreement.PARTIALLY_AGREES
    assert review.final_recommendation == EvaluationRecommendation.STRONG_MATCH
    assert review.inconsistencies[0].type == "Overconfidence"
    assert review.reviewed_evaluation_id == "resp_eval" and review.agent_execution_id == "resp_review"
    assert review.model == "gpt-5.4" and review.agent_version == "2"

    reviewer_run = recorder.executions[1]
    assert reviewer_run.agent_name == REVIEWER and reviewer_run.model == "gpt-5.4"
    assert "91 → 84" in reviewer_run.output_summary


@pytest.mark.asyncio
async def test_reviewer_failure_keeps_the_evaluation_and_can_be_retried() -> None:
    responses = FakeResponses(review_error=RuntimeError("model overloaded"))
    evaluations, service, recorder, _ = make_evaluation(responses)
    application = await submit(service)

    await evaluations.start_and_run(application.id)
    stored = await service.get(application.id)
    assert stored.evaluation.status == EvaluationStatus.COMPLETED
    assert stored.review.status == EvaluationStatus.FAILED

    responses.review_error = None
    started = await evaluations.start_review(application.id)
    assert started.review.status == EvaluationStatus.IN_PROGRESS and started.evaluation.overall_score == 91
    await evaluations.run_review(application.id)
    assert (await service.get(application.id)).review.status == EvaluationStatus.COMPLETED
    assert [run.agent_name for run in recorder.executions] == ["candidate-evaluator", REVIEWER, REVIEWER]


@pytest.mark.asyncio
async def test_review_is_skipped_when_evaluation_needs_manual_review_and_cleared_on_reevaluation() -> None:
    evaluations, service, _, responses = make_evaluation(FakeResponses(error=ContentFilterError("blocked")))
    application = await submit(service)
    await evaluations.start_and_run(application.id)
    assert (await service.get(application.id)).review is None
    assert len(responses.calls) == 1
    with pytest.raises(ValueError, match="completed evaluation"):
        await evaluations.start_review(application.id)

    responses.error = None
    await evaluations.start_and_run(application.id)
    assert (await service.get(application.id)).review.status == EvaluationStatus.COMPLETED
    restarted = await evaluations.start(application.id)
    assert restarted.review is None and restarted.evaluation.status == EvaluationStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_approval_snapshots_ai_advice_and_feeds_back_without_personal_data() -> None:
    evaluations, service, _, _ = make_evaluation()
    application = await submit(service)
    await evaluations.start_and_run(application.id)

    decided = await evaluations.decide(application.id, ApplicationDecisionRequest(status="Advanced", comment=" Invite ", decided_by="Jordan Lee", ai_rating="Partially accurate", agent_feedback=" Reviewer was right about the portfolio. "))
    decision = decided.decision
    assert (decision.ai_recommendation, decision.ai_score, decision.followed_ai) == (EvaluationRecommendation.STRONG_MATCH, 84, True)
    assert (decision.evaluation_execution_id, decision.review_execution_id) == ("resp_eval", "resp_review")
    assert decision.agent_feedback == "Reviewer was right about the portfolio." and decision.comment == "Invite"

    feedback = (await evaluations.list_feedback())[0]
    assert feedback.application_id == application.id and feedback.followed_ai is True
    assert (feedback.evaluation_score, feedback.validated_score, feedback.reviewer_agreement) == (91, 84, ReviewAgreement.PARTIALLY_AGREES)
    assert (feedback.evaluator_version, feedback.reviewer_version) == ("4", "2")
    dumped = feedback.model_dump_json()
    assert "Ada" not in dumped and "ada@example.com" not in dumped

    rejected = await evaluations.decide(application.id, ApplicationDecisionRequest(status="Rejected"))
    assert rejected.decision.followed_ai is False and rejected.decision.ai_rating is None


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


def test_reviewer_schema_matches_api_model_and_uses_a_different_model() -> None:
    folder = AGENTS / REVIEWER
    schema = json.loads((folder / "output-schema.json").read_text(encoding="utf-8"))
    fields = {field.alias for field in CandidateReviewOutput.model_fields.values()}
    assert set(schema["properties"]) == fields == set(schema["required"])
    assert set(schema["properties"]["finalRecommendation"]["enum"]) == {item.value for item in EvaluationRecommendation}
    assert set(schema["properties"]["agreement"]["enum"]) == {item.value for item in ReviewAgreement}
    reviewer_model = json.loads((folder / "agent.json").read_text(encoding="utf-8"))["modelDeployment"]
    evaluator_model = json.loads((AGENTS / "candidate-evaluator" / "agent.json").read_text(encoding="utf-8")).get("modelDeployment", "gpt-5.4-mini")
    assert reviewer_model != evaluator_model


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
        assert evaluated["review"]["validatedScore"] == 84 and evaluated["review"]["inconsistencies"][0]["severity"] == "Medium"

        restarted = client.post(f"/applications/{created['id']}/evaluation")
        assert restarted.status_code == 202 and restarted.json()["review"] is None
        assert client.get(f"/applications/{created['id']}").json()["review"]["status"] == "Completed"
        assert client.post(f"/applications/{created['id']}/review").status_code == 202

        decided = client.put(f"/applications/{created['id']}/decision", json={"status": "Advanced", "comment": " Great fit ", "decidedBy": "Jordan Lee", "aiRating": "Accurate", "agentFeedback": "Spot on."})
        assert decided.status_code == 200
        body = decided.json()["decision"]
        assert body["status"] == "Advanced" and body["comment"] == "Great fit" and body["aiRating"] == "Accurate"
        assert body["aiScore"] == 84 and body["followedAi"] is True
        assert decided.json()["evaluation"]["overallScore"] == 91
        assert client.put(f"/applications/{created['id']}/decision", json={"status": "Maybe"}).status_code == 422
        assert client.put(f"/applications/{created['id']}/decision", json={"status": "Advanced", "aiRating": "Great"}).status_code == 422

        feedback = client.get("/agent-feedback").json()
        assert feedback[0]["agentFeedback"] == "Spot on." and "candidateName" not in feedback[0]
        assert client.delete(f"/applications/{created['id']}/decision").json()["decision"] is None
        assert client.get("/agent-feedback").json() == []

        runs = client.get("/agent-executions?limit=10").json()
        assert [run["agentName"] for run in runs].count(REVIEWER) == 3 and runs[0]["inputTokens"] == 1200
        assert client.post("/applications/missing/evaluation").status_code == 404
        assert client.post("/applications/missing/review").status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_running_evaluation_cannot_be_started_twice() -> None:
    evaluations, service, _, _ = make_evaluation()
    application = await submit(service)
    await evaluations.start(application.id)
    with pytest.raises(ValueError, match="already running"):
        await evaluations.start(application.id)


@pytest.mark.asyncio
async def test_late_results_of_a_superseded_run_are_discarded() -> None:
    evaluations, service, recorder, responses = make_evaluation()
    application = await submit(service)
    await evaluations.start(application.id)
    original_create = responses.create

    async def restarted_meanwhile(**kwargs: Any) -> Any:
        # A newer run (e.g. a restart after the stale timeout) replaces the step while this agent call is in flight.
        current = await service.get(application.id)
        await service.update_assessment(current, evaluation=current.evaluation.model_copy(update={"started_at": datetime.now(UTC) + timedelta(seconds=1)}))
        return await original_create(**kwargs)

    responses.create = restarted_meanwhile
    await evaluations.run(application.id)
    stored = await service.get(application.id)
    assert stored.evaluation.status == EvaluationStatus.IN_PROGRESS and stored.review is None
    assert [run.agent_name for run in recorder.executions] == ["candidate-evaluator"]

    responses.create = original_create
    await evaluations.run(application.id)
    reviewed = await service.get(application.id)
    assert reviewed.review.status == EvaluationStatus.COMPLETED
    await evaluations.start_review(application.id)

    async def review_restarted_meanwhile(**kwargs: Any) -> Any:
        current = await service.get(application.id)
        await service.update_assessment(current, review=current.review.model_copy(update={"started_at": datetime.now(UTC) + timedelta(seconds=1)}))
        return await original_create(**kwargs)

    responses.create = review_restarted_meanwhile
    await evaluations.run_review(application.id)
    assert (await service.get(application.id)).review.status == EvaluationStatus.IN_PROGRESS
