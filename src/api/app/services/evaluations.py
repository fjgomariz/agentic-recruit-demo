"""Run candidate evaluations and record recruiter decisions."""

import logging
from datetime import UTC, datetime, timedelta

from app.domain import (
    ApplicationDecision,
    ApplicationDecisionRequest,
    ApplicationEvaluation,
    EvaluationRecommendation,
    EvaluationScore,
    EvaluationStatus,
    JobApplication,
)
from app.services.agents import AgentInputRejectedError, AgentUnavailableError, CandidateEvaluationAgentService
from app.services.applications import ApplicationService

logger = logging.getLogger(__name__)

# An evaluation stuck "In progress" longer than this (for example after a restart) can be started again.
STALE_EVALUATION = timedelta(minutes=3)


class EvaluationInProgressError(ValueError):
    """Raised when an evaluation is already running for the application."""


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class EvaluationService:
    """Coordinate the candidate evaluator with application storage."""

    def __init__(self, applications: ApplicationService, agent: CandidateEvaluationAgentService) -> None:
        self._applications = applications
        self._agent = agent

    async def start(self, application_id: str) -> JobApplication:
        """Mark the application as being evaluated; the caller then schedules run()."""

        if not self._agent.configured:
            raise AgentUnavailableError("The candidate evaluator is not configured")
        application = await self._applications.get(application_id)
        current = application.evaluation
        if current and current.status == EvaluationStatus.IN_PROGRESS and datetime.now(UTC) - current.started_at < STALE_EVALUATION:
            raise EvaluationInProgressError("An evaluation is already running for this application")
        evaluation = ApplicationEvaluation(status=EvaluationStatus.IN_PROGRESS, started_at=datetime.now(UTC), agent_name=self._agent.agent_name)
        return await self._applications.set_evaluation(application, evaluation)

    async def start_and_run(self, application_id: str) -> None:
        """Background entry point for new applications: start and run, never raising."""

        if not self._agent.configured:
            logger.info("Candidate evaluator not configured; application=%s stays pending", application_id)
            return
        try:
            await self.start(application_id)
        except Exception:
            logger.exception("Automatic evaluation could not start application=%s", application_id)
            return
        await self.run(application_id)

    async def run(self, application_id: str) -> None:
        """Evaluate the application and store the outcome; never raises, so it is safe as a background task."""

        try:
            application = await self._applications.get(application_id)
        except Exception:
            logger.exception("Evaluation could not load application id=%s", application_id)
            return

        started_at = application.evaluation.started_at if application.evaluation else datetime.now(UTC)
        base = {"started_at": started_at, "completed_at": None, "agent_name": self._agent.agent_name}
        try:
            job = await self._applications.get_job(application.job_id)
            _, resume = await self._applications.get_resume(application.id)
            result = await self._agent.evaluate(job, application, resume)
            output = result.output
            needs_review = output.recommendation == EvaluationRecommendation.NEEDS_MANUAL_REVIEW
            evaluation = ApplicationEvaluation(
                **base,
                status=EvaluationStatus.NEEDS_REVIEW if needs_review else EvaluationStatus.COMPLETED,
                agent_version=result.run.agent_version,
                agent_execution_id=result.run.response_id,
                overall_score=_clamp(output.overall_score, 0, 100),
                recommendation=output.recommendation,
                summary=output.summary,
                strengths=output.strengths,
                considerations=output.considerations,
                scores=[
                    EvaluationScore(id=f"criterion-{index}", criterion=item.criterion, value=_clamp(item.score, 0, 5), maximum_value=5, rationale=item.rationale)
                    for index, item in enumerate(output.criteria, start=1)
                ],
            )
        except AgentInputRejectedError as error:
            evaluation = ApplicationEvaluation(
                **base,
                status=EvaluationStatus.NEEDS_REVIEW,
                recommendation=EvaluationRecommendation.NEEDS_MANUAL_REVIEW,
                summary=f"{error}. The resume was not scored automatically; review it manually.",
                considerations=[error.consideration],
                error_message=str(error),
            )
        except Exception as error:
            logger.exception("Evaluation failed application=%s", application_id)
            evaluation = ApplicationEvaluation(**base, status=EvaluationStatus.FAILED, error_message=str(error) or type(error).__name__)

        evaluation = evaluation.model_copy(update={"completed_at": datetime.now(UTC)})
        try:
            await self._applications.set_evaluation(application, evaluation)
            logger.info("Evaluation finished application=%s status=%s score=%s", application_id, evaluation.status, evaluation.overall_score)
        except Exception:
            logger.exception("Could not store evaluation for application=%s", application_id)

    async def decide(self, application_id: str, request: ApplicationDecisionRequest) -> JobApplication:
        application = await self._applications.get(application_id)
        decision = ApplicationDecision(status=request.status, comment=request.comment.strip(), decided_by=request.decided_by.strip(), decided_at=datetime.now(UTC))
        return await self._applications.set_decision(application, decision)

    async def clear_decision(self, application_id: str) -> JobApplication:
        application = await self._applications.get(application_id)
        return await self._applications.set_decision(application, None)
