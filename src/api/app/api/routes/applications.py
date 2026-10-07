"""Candidate application, evaluation, and decision endpoints."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, Response, UploadFile, status

from app.api.errors import execute
from app.dependencies.services import AgentExecutionLogDependency, ApplicationServiceDependency, EvaluationServiceDependency
from app.domain import AgentExecution, AgentFeedback, ApplicationDecisionRequest, JobApplication
from app.services.applications import MAX_RESUME_BYTES

router = APIRouter()


@router.post(
    "/jobs/{job_id}/applications",
    response_model=JobApplication,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a job with a PDF resume; the AI evaluation starts in the background",
)
async def submit_application(
    job_id: str,
    service: ApplicationServiceDependency,
    evaluations: EvaluationServiceDependency,
    background_tasks: BackgroundTasks,
    candidate_name: Annotated[str, Form(alias="candidateName", min_length=1, max_length=120)],
    candidate_email: Annotated[str, Form(alias="candidateEmail", max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")],
    resume: Annotated[UploadFile, File(description="PDF resume, 5 MB maximum")],
    message: Annotated[str, Form(max_length=2000)] = "",
) -> JobApplication:
    data = await resume.read(MAX_RESUME_BYTES + 1)
    # ApplicationNotAllowedError is a ValueError, which execute() maps to 400.
    application = await execute(lambda: service.submit(job_id, candidate_name, candidate_email, message, resume.filename, data))
    background_tasks.add_task(evaluations.start_and_run, application.id)
    return application


@router.get(
    "/jobs/{job_id}/applications",
    response_model=list[JobApplication],
    summary="List applications for a job, newest first",
)
async def list_job_applications(job_id: str, service: ApplicationServiceDependency) -> list[JobApplication]:
    return await service.list_for_job(job_id)


@router.get("/applications", response_model=list[JobApplication], summary="List all applications, newest first")
async def list_applications(service: ApplicationServiceDependency) -> list[JobApplication]:
    return await service.list_all()


@router.get("/applications/{application_id}", response_model=JobApplication, summary="Get an application")
async def get_application(application_id: str, service: ApplicationServiceDependency) -> JobApplication:
    return await execute(lambda: service.get(application_id))


@router.get(
    "/applications/{application_id}/resume",
    summary="Download the application's PDF resume",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def download_resume(application_id: str, service: ApplicationServiceDependency) -> Response:
    application, content = await execute(lambda: service.get_resume(application_id))
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(application.resume_file_name)}"},
    )


@router.post(
    "/applications/{application_id}/evaluation",
    response_model=JobApplication,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start (or restart) the AI assessment: evaluation, then review; poll the application for the result",
)
async def evaluate_application(application_id: str, evaluations: EvaluationServiceDependency, background_tasks: BackgroundTasks) -> JobApplication:
    application = await execute(lambda: evaluations.start(application_id))
    background_tasks.add_task(evaluations.run, application_id)
    return application


@router.post(
    "/applications/{application_id}/review",
    response_model=JobApplication,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-run only the reviewer agent on the current evaluation",
)
async def review_application(application_id: str, evaluations: EvaluationServiceDependency, background_tasks: BackgroundTasks) -> JobApplication:
    application = await execute(lambda: evaluations.start_review(application_id))
    background_tasks.add_task(evaluations.run_review, application_id)
    return application


@router.put("/applications/{application_id}/decision", response_model=JobApplication, summary="Record the recruiter's approval decision and feedback for the agents")
async def decide_application(application_id: str, request: ApplicationDecisionRequest, evaluations: EvaluationServiceDependency) -> JobApplication:
    return await execute(lambda: evaluations.decide(application_id, request))


@router.delete("/applications/{application_id}/decision", response_model=JobApplication, summary="Clear the recruiter's decision")
async def clear_application_decision(application_id: str, evaluations: EvaluationServiceDependency) -> JobApplication:
    return await execute(lambda: evaluations.clear_decision(application_id))


@router.get("/agent-executions", response_model=list[AgentExecution], tags=["AI operations"], summary="Recent Foundry agent runs, newest first")
async def list_agent_executions(log: AgentExecutionLogDependency, limit: Annotated[int, Query(ge=1, le=200)] = 50) -> list[AgentExecution]:
    return await log.list_recent(limit)


@router.get("/agent-feedback", response_model=list[AgentFeedback], tags=["AI operations"], summary="Recruiter feedback on the AI workflow, newest first, without candidate personal data")
async def list_agent_feedback(evaluations: EvaluationServiceDependency) -> list[AgentFeedback]:
    return await evaluations.list_feedback()
