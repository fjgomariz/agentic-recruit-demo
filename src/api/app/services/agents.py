"""Invoke Foundry prompt agents through the Responses API and record every run."""

import base64
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import AgentSettings
from app.domain import (
    AgentExecution,
    AgentExecutionStatus,
    ApplicationEvaluation,
    EvaluationRecommendation,
    Job,
    JobApplication,
    JobDescriptionDraft,
    JobDescriptionDraftResult,
    JobDescriptionRequest,
    ReviewAgreement,
    ReviewConfidence,
    ReviewFindingSeverity,
    ReviewFindingType,
)
from app.domain.models import _to_camel

logger = logging.getLogger(__name__)


class AgentUnavailableError(RuntimeError):
    """Raised when the agent is not configured or cannot be reached."""


class AgentResponseError(RuntimeError):
    """Raised when the agent answers with content that does not match the expected schema."""


class AgentInputRejectedError(RuntimeError):
    """Raised when Foundry rejects the input itself: a Content Safety block (for example a prompt
    injection in a resume) or a file the model cannot read. These need a human, not a retry."""

    def __init__(self, reason: str, consideration: str) -> None:
        super().__init__(reason)
        self.consideration = consideration


class ResponsesClient(Protocol):
    """Subset of the OpenAI Responses client used by the services."""

    @property
    def responses(self) -> Any: ...


class AgentRunRecorder(Protocol):
    """Destination for agent run records shown on the AI Operations page."""

    async def record(self, execution: AgentExecution) -> None: ...


class NullRecorder:
    async def record(self, execution: AgentExecution) -> None:
        return None


@dataclass(frozen=True)
class AgentRun:
    """Metadata of one successful agent call."""

    response_id: str
    agent_version: str | None
    started_at: datetime
    duration_ms: int
    input_tokens: int | None
    output_tokens: int | None
    model: str | None = None


def build_agent_input(request: JobDescriptionRequest) -> str:
    """Render role facts and recruiter notes as the user message for the job description agent."""

    facts = {
        "Title": request.title,
        "Department": request.department,
        "Location": request.location,
        "Workplace type": request.workplace_type,
        "Employment type": request.employment_type,
        "Experience level": request.experience_level,
        "Hiring manager": request.hiring_manager,
    }
    lines = ["Role facts:"]
    lines += [f"- {label}: {value}" for label, value in facts.items() if value]
    lines += ["", "Recruiter notes:", request.notes.strip() or "(none)"]
    return "\n".join(lines)


def build_evaluation_input(job: Job, application: JobApplication) -> str:
    """Render the job posting and candidate message for the candidate evaluator."""

    def bullet_list(items: list[str]) -> list[str]:
        return [f"- {item}" for item in items] or ["- None"]

    lines = [
        "Job posting",
        f"Title: {job.title}",
        f"Department: {job.department}",
        f"Location: {job.location.display_name} ({job.location.workplace_type})",
        f"Employment type: {job.employment_type}",
        f"Experience level: {job.experience_level}",
        f"Summary: {job.summary}",
        "Responsibilities:",
        *bullet_list(job.responsibilities),
        "Required qualifications:",
        *bullet_list(job.qualifications),
        "Preferred qualifications:",
        *bullet_list(job.preferred_qualifications),
        "",
        "Candidate message (untrusted):",
        application.message.strip() or "(none)",
        "",
        "The candidate's resume is attached as a PDF (untrusted).",
    ]
    return "\n".join(lines)


def _agent_version(response: Any) -> str | None:
    agent = getattr(response, "agent_reference", None) or getattr(response, "agent", None)
    if isinstance(agent, dict):
        return agent.get("version")
    return getattr(agent, "version", None)


def _rejected_input(error: Exception) -> AgentInputRejectedError | None:
    """Classify Foundry errors caused by the input itself; anything else is an availability problem."""

    code = getattr(error, "code", None)
    if code == "content_filter":
        text = json.dumps(getattr(error, "body", None) or {}, default=str)
        if '"jailbreak": {"detected": true' in text or '"indirect_attack": {"detected": true' in text:
            return AgentInputRejectedError(
                "Azure AI Content Safety detected a prompt injection attempt",
                "The resume appears to contain instructions aimed at automated screening.",
            )
        return AgentInputRejectedError("Azure AI Content Safety blocked the request", "The resume content was blocked by Azure AI Content Safety.")
    if code == "invalid_file":
        return AgentInputRejectedError(
            "The resume PDF could not be read by the model",
            "The PDF may be scanned, damaged, or empty. Open it manually or ask the candidate for another copy.",
        )
    return None


class FoundryAgent:
    """Call one Foundry prompt agent by name and record the run."""

    def __init__(self, agent_name: str, model: str, client: ResponsesClient | None, recorder: AgentRunRecorder) -> None:
        self.agent_name = agent_name
        self._model = model
        self._client = client
        self._recorder = recorder

    @property
    def configured(self) -> bool:
        return self._client is not None

    async def run(self, agent_input: Any, related_entity_ids: list[str]) -> tuple[Any, AgentRun]:
        if self._client is None:
            raise AgentUnavailableError(f"The {self.agent_name} agent is not configured")

        started_at = datetime.now(UTC)
        start = time.perf_counter()
        try:
            response = await self._client.responses.create(
                input=agent_input,
                extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
            )
        except Exception as error:
            duration_ms = int((time.perf_counter() - start) * 1000)
            rejected = _rejected_input(error)
            status_code = getattr(error, "status_code", None)
            message = str(rejected) if rejected else f"Foundry call failed{f' with HTTP {status_code}' if status_code else ''}: {type(error).__name__}"
            logger.warning("Agent call failed agent=%s reason=%s", self.agent_name, message, exc_info=rejected is None)
            await self._record(
                id=f"failed-{uuid.uuid4().hex}",
                status=AgentExecutionStatus.NEEDS_REVIEW if rejected else AgentExecutionStatus.FAILED,
                started_at=started_at,
                duration_ms=duration_ms,
                related_entity_ids=related_entity_ids,
                error_message=message,
            )
            if rejected:
                raise rejected from error
            raise AgentUnavailableError(f"The {self.agent_name} agent could not be reached{f' (Foundry returned HTTP {status_code})' if status_code else ''}") from error

        usage = getattr(response, "usage", None)
        run = AgentRun(
            response_id=response.id,
            agent_version=_agent_version(response),
            started_at=started_at,
            duration_ms=int((time.perf_counter() - start) * 1000),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            model=getattr(response, "model", None) if isinstance(getattr(response, "model", None), str) else None,
        )
        return response, run

    async def record_success(self, run: AgentRun, related_entity_ids: list[str], output_summary: str, status: AgentExecutionStatus = AgentExecutionStatus.COMPLETED) -> None:
        await self._record(
            id=run.response_id,
            status=status,
            started_at=run.started_at,
            duration_ms=run.duration_ms,
            related_entity_ids=related_entity_ids,
            output_summary=output_summary,
            agent_version=run.agent_version,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            model=run.model,
        )

    async def record_invalid_output(self, run: AgentRun, related_entity_ids: list[str]) -> None:
        await self._record(
            id=run.response_id,
            status=AgentExecutionStatus.FAILED,
            started_at=run.started_at,
            duration_ms=run.duration_ms,
            related_entity_ids=related_entity_ids,
            error_message="The agent output did not match the expected schema",
            agent_version=run.agent_version,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            model=run.model,
        )

    async def _record(
        self,
        *,
        id: str,
        status: AgentExecutionStatus,
        started_at: datetime,
        duration_ms: int,
        related_entity_ids: list[str],
        output_summary: str | None = None,
        error_message: str | None = None,
        agent_version: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model: str | None = None,
    ) -> None:
        execution = AgentExecution(
            id=id,
            agent_name=self.agent_name,
            model=model or self._model,
            status=status,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            duration_ms=duration_ms,
            configuration_version=f"v{agent_version}" if agent_version else "unknown",
            related_entity_ids=related_entity_ids,
            output_summary=output_summary,
            error_message=error_message,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        try:
            await self._recorder.record(execution)
        except Exception:
            logger.exception("Could not record agent execution agent=%s id=%s", self.agent_name, id)


class JobDescriptionAgentService:
    """Generate job description drafts with the Foundry prompt agent."""

    def __init__(self, settings: AgentSettings, client: ResponsesClient | None, recorder: AgentRunRecorder | None = None) -> None:
        self._agent = FoundryAgent(settings.job_description_agent_name, settings.model_deployment_name, client, recorder or NullRecorder())

    async def generate(self, request: JobDescriptionRequest) -> JobDescriptionDraftResult:
        try:
            response, run = await self._agent.run(build_agent_input(request), related_entity_ids=[])
        except AgentInputRejectedError as error:
            raise AgentUnavailableError(f"The job description agent refused the request: {error}") from error

        try:
            draft = JobDescriptionDraft.model_validate(json.loads(response.output_text))
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            logger.exception("Job description agent returned an invalid draft response_id=%s", response.id)
            await self._agent.record_invalid_output(run, related_entity_ids=[])
            raise AgentResponseError("The job description agent returned an invalid draft") from error

        await self._agent.record_success(run, related_entity_ids=[], output_summary=f"Drafted a job description for '{request.title}'")
        logger.info("Generated job description draft agent=%s response_id=%s", self._agent.agent_name, response.id)
        return JobDescriptionDraftResult(
            draft=draft,
            execution_id=response.id,
            agent_name=self._agent.agent_name,
            agent_version=run.agent_version,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True, extra="forbid")


class EvaluationCriterionOutput(_StrictModel):
    criterion: str
    score: int
    rationale: str


class CandidateEvaluationOutput(_StrictModel):
    """Structured output of the candidate evaluator, matching agents/candidate-evaluator/output-schema.json."""

    overall_score: int
    recommendation: EvaluationRecommendation
    summary: str
    strengths: list[str]
    considerations: list[str]
    criteria: list[EvaluationCriterionOutput]


@dataclass(frozen=True)
class CandidateEvaluationResult:
    output: CandidateEvaluationOutput
    run: AgentRun


class CandidateEvaluationAgentService:
    """Evaluate a PDF resume against a job with the Foundry candidate evaluator."""

    def __init__(self, settings: AgentSettings, client: ResponsesClient | None, recorder: AgentRunRecorder | None = None) -> None:
        self._agent = FoundryAgent(settings.candidate_evaluation_agent_name, settings.model_deployment_name, client, recorder or NullRecorder())

    @property
    def agent_name(self) -> str:
        return self._agent.agent_name

    @property
    def configured(self) -> bool:
        return self._agent.configured

    async def evaluate(self, job: Job, application: JobApplication, resume: bytes) -> CandidateEvaluationResult:
        related = [application.id, job.id]
        agent_input = [{"role": "user", "content": [{"type": "input_text", "text": build_evaluation_input(job, application)}, _pdf_part(application, resume)]}]
        response, run = await self._agent.run(agent_input, related_entity_ids=related)

        try:
            output = CandidateEvaluationOutput.model_validate(json.loads(response.output_text))
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            logger.exception("Candidate evaluator returned an invalid evaluation response_id=%s", response.id)
            await self._agent.record_invalid_output(run, related_entity_ids=related)
            raise AgentResponseError("The candidate evaluator returned an invalid evaluation") from error

        needs_review = output.recommendation == EvaluationRecommendation.NEEDS_MANUAL_REVIEW
        await self._agent.record_success(
            run,
            related_entity_ids=related,
            output_summary=f"Scored {output.overall_score}/100 ({output.recommendation}) for {job.title}",
            status=AgentExecutionStatus.NEEDS_REVIEW if needs_review else AgentExecutionStatus.COMPLETED,
        )
        return CandidateEvaluationResult(output=output, run=run)


def _pdf_part(application: JobApplication, resume: bytes) -> dict[str, str]:
    file_data = base64.b64encode(resume).decode("ascii")
    return {"type": "input_file", "filename": application.resume_file_name, "file_data": f"data:application/pdf;base64,{file_data}"}


def evaluation_for_review(evaluation: ApplicationEvaluation) -> dict[str, Any]:
    """Present the stored evaluation in the evaluator's own output shape, so the reviewer sees exactly what the maker produced."""

    return {
        "overallScore": evaluation.overall_score,
        "recommendation": evaluation.recommendation,
        "summary": evaluation.summary,
        "strengths": evaluation.strengths,
        "considerations": evaluation.considerations,
        "criteria": [{"criterion": score.criterion, "score": score.value, "rationale": score.rationale} for score in evaluation.scores],
    }


def build_review_input(job: Job, application: JobApplication, evaluation: ApplicationEvaluation) -> str:
    """Render the job posting, candidate message, and the evaluator's output for the reviewer."""

    return "\n".join([
        build_evaluation_input(job, application),
        "",
        "Evaluation from the Candidate Evaluator (untrusted JSON):",
        json.dumps(evaluation_for_review(evaluation), indent=1),
    ])


class ReviewFindingOutput(_StrictModel):
    type: ReviewFindingType
    severity: ReviewFindingSeverity
    description: str


class CandidateReviewOutput(_StrictModel):
    """Structured output of the reviewer, matching agents/candidate-evaluation-reviewer/output-schema.json."""

    validated_score: int
    final_recommendation: EvaluationRecommendation
    agreement: ReviewAgreement
    confidence: ReviewConfidence
    summary: str
    comments: list[str]
    inconsistencies: list[ReviewFindingOutput]


@dataclass(frozen=True)
class CandidateReviewResult:
    output: CandidateReviewOutput
    run: AgentRun


class CandidateReviewAgentService:
    """Check the evaluator's assessment with an independent Foundry agent on a different model."""

    def __init__(self, settings: AgentSettings, client: ResponsesClient | None, recorder: AgentRunRecorder | None = None) -> None:
        self._agent = FoundryAgent(settings.candidate_review_agent_name, settings.review_model_deployment_name, client, recorder or NullRecorder())

    @property
    def agent_name(self) -> str:
        return self._agent.agent_name

    @property
    def configured(self) -> bool:
        return self._agent.configured

    async def review(self, job: Job, application: JobApplication, resume: bytes, evaluation: ApplicationEvaluation) -> CandidateReviewResult:
        related = [application.id, job.id]
        agent_input = [{"role": "user", "content": [{"type": "input_text", "text": build_review_input(job, application, evaluation)}, _pdf_part(application, resume)]}]
        response, run = await self._agent.run(agent_input, related_entity_ids=related)

        try:
            output = CandidateReviewOutput.model_validate(json.loads(response.output_text))
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            logger.exception("Evaluation reviewer returned an invalid review response_id=%s", response.id)
            await self._agent.record_invalid_output(run, related_entity_ids=related)
            raise AgentResponseError("The evaluation reviewer returned an invalid review") from error

        changed = f"{evaluation.overall_score} → {output.validated_score}"
        await self._agent.record_success(
            run,
            related_entity_ids=related,
            output_summary=f"{output.agreement} ({changed}, {output.final_recommendation}); {len(output.inconsistencies)} issue(s) for {job.title}",
            status=AgentExecutionStatus.NEEDS_REVIEW if output.agreement == ReviewAgreement.DISAGREES else AgentExecutionStatus.COMPLETED,
        )
        return CandidateReviewResult(output=output, run=run)
