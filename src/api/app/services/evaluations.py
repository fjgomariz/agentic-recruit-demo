"""Candidate assessment workflow: evaluator (maker) → reviewer (checker) → recruiter approval."""

import logging
from datetime import UTC, datetime, timedelta

from app.domain import (
    AgentFeedback,
    ApplicationDecision,
    ApplicationDecisionRequest,
    ApplicationEvaluation,
    ApplicationReview,
    EvaluationRecommendation,
    EvaluationScore,
    EvaluationStatus,
    Job,
    JobApplication,
    ReviewFinding,
)
from app.services.agents import (
    AgentInputRejectedError,
    AgentUnavailableError,
    CandidateEvaluationAgentService,
    CandidateReviewAgentService,
)
from app.services.applications import ApplicationService

logger = logging.getLogger(__name__)

# A step stuck "In progress" longer than this (for example after a restart) can be started again.
STALE_EVALUATION = timedelta(minutes=3)


class EvaluationInProgressError(ValueError):
    """Raised when an evaluation or review is already running for the application."""


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _running(step: ApplicationEvaluation | ApplicationReview | None) -> bool:
    return bool(step and step.status == EvaluationStatus.IN_PROGRESS and datetime.now(UTC) - step.started_at < STALE_EVALUATION)


def _same_run(current: ApplicationEvaluation | ApplicationReview | None, started: ApplicationEvaluation | ApplicationReview | None) -> bool:
    """The step a background task started is still the one stored, i.e. it was not restarted or cleared meanwhile."""

    return bool(current and started and current.status == EvaluationStatus.IN_PROGRESS and current.started_at == started.started_at)


def final_ai_advice(application: JobApplication) -> tuple[EvaluationRecommendation | None, int | None]:
    """The AI recommendation the recruiter sees: the reviewer's when available, otherwise the evaluator's."""

    review, evaluation = application.review, application.evaluation
    if review and review.status == EvaluationStatus.COMPLETED:
        return review.final_recommendation, review.validated_score
    if evaluation and evaluation.status in (EvaluationStatus.COMPLETED, EvaluationStatus.NEEDS_REVIEW):
        return evaluation.recommendation, evaluation.overall_score
    return None, None


def _followed_ai(recommendation: EvaluationRecommendation | None, decision: str) -> bool | None:
    """Only clear-cut recommendations count; 'Possible match' and manual review leave the call to the recruiter."""

    if recommendation == EvaluationRecommendation.STRONG_MATCH:
        return decision == "Advanced"
    if recommendation == EvaluationRecommendation.NOT_A_MATCH:
        return decision == "Rejected"
    return None


class EvaluationService:
    """Orchestrate the two-agent assessment and the recruiter's approval."""

    def __init__(self, applications: ApplicationService, evaluator: CandidateEvaluationAgentService, reviewer: CandidateReviewAgentService) -> None:
        self._applications = applications
        self._evaluator = evaluator
        self._reviewer = reviewer

    # Step 1: evaluation (maker) -------------------------------------------------------------

    async def start(self, application_id: str) -> JobApplication:
        """Mark the application as being evaluated and clear the old review; the caller then schedules run()."""

        if not self._evaluator.configured:
            raise AgentUnavailableError("The candidate evaluator is not configured")
        application = await self._applications.get(application_id)
        if _running(application.evaluation) or _running(application.review):
            raise EvaluationInProgressError("An evaluation is already running for this application")
        evaluation = ApplicationEvaluation(status=EvaluationStatus.IN_PROGRESS, started_at=datetime.now(UTC), agent_name=self._evaluator.agent_name)
        return await self._applications.update_assessment(application, evaluation=evaluation, review=None)

    async def start_and_run(self, application_id: str) -> None:
        """Background entry point for new applications: start and run, never raising."""

        if not self._evaluator.configured:
            logger.info("Candidate evaluator not configured; application=%s stays pending", application_id)
            return
        try:
            await self.start(application_id)
        except Exception:
            logger.exception("Automatic evaluation could not start application=%s", application_id)
            return
        await self.run(application_id)

    async def run(self, application_id: str) -> None:
        """Evaluate, then hand over to the reviewer when the evaluation succeeded. Never raises."""

        try:
            application = await self._applications.get(application_id)
            job = await self._applications.get_job(application.job_id)
            _, resume = await self._applications.get_resume(application.id)
        except Exception as error:
            logger.exception("Evaluation could not load application id=%s", application_id)
            await self._store_failed_evaluation(application_id, error)
            return

        evaluation = await self._evaluate(application, job, resume)
        hand_over = evaluation.status == EvaluationStatus.COMPLETED and self._reviewer.configured
        review = self._new_review(evaluation) if hand_over else None
        try:
            current = await self._applications.get(application_id)
            if not _same_run(current.evaluation, application.evaluation):
                logger.info("Discarding evaluation of a superseded run application=%s", application_id)
                return
            application = await self._applications.update_assessment(current, evaluation=evaluation, review=review)
            logger.info("Evaluation finished application=%s status=%s score=%s", application_id, evaluation.status, evaluation.overall_score)
        except Exception:
            logger.exception("Could not store evaluation for application=%s", application_id)
            return
        if hand_over:
            await self._review(application, job, resume)

    async def _evaluate(self, application: JobApplication, job: Job, resume: bytes) -> ApplicationEvaluation:
        started_at = application.evaluation.started_at if application.evaluation else datetime.now(UTC)
        base = {"started_at": started_at, "agent_name": self._evaluator.agent_name}
        try:
            result = await self._evaluator.evaluate(job, application, resume)
            output = result.output
            needs_review = output.recommendation == EvaluationRecommendation.NEEDS_MANUAL_REVIEW
            evaluation = ApplicationEvaluation(
                **base,
                status=EvaluationStatus.NEEDS_REVIEW if needs_review else EvaluationStatus.COMPLETED,
                agent_version=result.run.agent_version,
                agent_execution_id=result.run.response_id,
                model=result.run.model,
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
            logger.exception("Evaluation failed application=%s", application.id)
            evaluation = ApplicationEvaluation(**base, status=EvaluationStatus.FAILED, error_message=str(error) or type(error).__name__)
        return evaluation.model_copy(update={"completed_at": datetime.now(UTC)})

    async def _store_failed_evaluation(self, application_id: str, error: Exception) -> None:
        try:
            application = await self._applications.get(application_id)
            started_at = application.evaluation.started_at if application.evaluation else datetime.now(UTC)
            failed = ApplicationEvaluation(status=EvaluationStatus.FAILED, started_at=started_at, completed_at=datetime.now(UTC), agent_name=self._evaluator.agent_name, error_message=str(error) or type(error).__name__)
            await self._applications.update_assessment(application, evaluation=failed)
        except Exception:
            logger.exception("Could not store the failed evaluation for application=%s", application_id)

    # Step 2: review (checker) ---------------------------------------------------------------

    def _new_review(self, evaluation: ApplicationEvaluation) -> ApplicationReview:
        return ApplicationReview(
            status=EvaluationStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
            agent_name=self._reviewer.agent_name,
            reviewed_evaluation_id=evaluation.agent_execution_id,
            original_score=evaluation.overall_score,
        )

    async def start_review(self, application_id: str) -> JobApplication:
        """Run (or re-run) only the review of the current evaluation; the caller then schedules run_review()."""

        if not self._reviewer.configured:
            raise AgentUnavailableError("The evaluation reviewer is not configured")
        application = await self._applications.get(application_id)
        if not application.evaluation or application.evaluation.status != EvaluationStatus.COMPLETED:
            raise ValueError("Only a completed evaluation can be reviewed")
        if _running(application.evaluation) or _running(application.review):
            raise EvaluationInProgressError("A review is already running for this application")
        return await self._applications.update_assessment(application, review=self._new_review(application.evaluation))

    async def run_review(self, application_id: str) -> None:
        """Background entry point for a review-only run. Never raises."""

        try:
            application = await self._applications.get(application_id)
            job = await self._applications.get_job(application.job_id)
            _, resume = await self._applications.get_resume(application.id)
        except Exception:
            logger.exception("Review could not load application id=%s", application_id)
            return
        await self._review(application, job, resume)

    async def _review(self, application: JobApplication, job: Job, resume: bytes) -> None:
        evaluation = application.evaluation
        pending = application.review or self._new_review(evaluation)
        base = pending.model_dump(include={"started_at", "agent_name", "reviewed_evaluation_id", "original_score"})
        try:
            result = await self._reviewer.review(job, application, resume, evaluation)
            output = result.output
            review = ApplicationReview(
                **base,
                status=EvaluationStatus.COMPLETED,
                agent_version=result.run.agent_version,
                agent_execution_id=result.run.response_id,
                model=result.run.model,
                validated_score=_clamp(output.validated_score, 0, 100),
                final_recommendation=output.final_recommendation,
                agreement=output.agreement,
                confidence=output.confidence,
                summary=output.summary,
                comments=output.comments,
                inconsistencies=[ReviewFinding(type=item.type, severity=item.severity, description=item.description) for item in output.inconsistencies],
            )
        except AgentInputRejectedError as error:
            review = ApplicationReview(**base, status=EvaluationStatus.NEEDS_REVIEW, summary=f"{error}. The evaluation was not reviewed automatically.", error_message=str(error))
        except Exception as error:
            logger.exception("Review failed application=%s", application.id)
            review = ApplicationReview(**base, status=EvaluationStatus.FAILED, error_message=str(error) or type(error).__name__)

        review = review.model_copy(update={"completed_at": datetime.now(UTC)})
        try:
            current = await self._applications.get(application.id)
            if not _same_run(current.review, application.review):
                logger.info("Discarding review of a superseded run application=%s", application.id)
                return
            await self._applications.update_assessment(current, review=review)
            logger.info("Review finished application=%s status=%s agreement=%s", application.id, review.status, review.agreement)
        except Exception:
            logger.exception("Could not store review for application=%s", application.id)

    # Step 3: recruiter approval -------------------------------------------------------------

    async def decide(self, application_id: str, request: ApplicationDecisionRequest) -> JobApplication:
        """Record the recruiter's decision with a snapshot of the AI advice it was based on."""

        application = await self._applications.get(application_id)
        recommendation, score = final_ai_advice(application)
        decision = ApplicationDecision(
            status=request.status,
            comment=request.comment.strip(),
            decided_by=request.decided_by.strip(),
            decided_at=datetime.now(UTC),
            ai_rating=request.ai_rating,
            agent_feedback=request.agent_feedback.strip(),
            ai_recommendation=recommendation,
            ai_score=score,
            followed_ai=_followed_ai(recommendation, request.status),
            evaluation_execution_id=application.evaluation.agent_execution_id if application.evaluation else None,
            review_execution_id=application.review.agent_execution_id if application.review else None,
        )
        return await self._applications.update_assessment(application, decision=decision)

    async def clear_decision(self, application_id: str) -> JobApplication:
        application = await self._applications.get(application_id)
        return await self._applications.update_assessment(application, decision=None)

    async def list_feedback(self) -> list[AgentFeedback]:
        """Recruiter feedback on the AI workflow, newest first, without candidate personal data."""

        feedback = []
        for application in await self._applications.list_all():
            decision = application.decision
            if not decision:
                continue
            evaluation, review = application.evaluation, application.review
            feedback.append(AgentFeedback(
                application_id=application.id,
                job_id=application.job_id,
                decided_at=decision.decided_at,
                decision=decision.status,
                ai_recommendation=decision.ai_recommendation,
                followed_ai=decision.followed_ai,
                ai_rating=decision.ai_rating,
                agent_feedback=decision.agent_feedback,
                evaluation_score=evaluation.overall_score if evaluation else None,
                validated_score=review.validated_score if review else None,
                reviewer_agreement=review.agreement if review else None,
                evaluator_version=evaluation.agent_version if evaluation else None,
                reviewer_version=review.agent_version if review else None,
            ))
        return sorted(feedback, key=lambda item: item.decided_at, reverse=True)
