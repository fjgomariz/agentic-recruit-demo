"""Candidate application endpoints."""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.api.errors import execute
from app.dependencies.services import ApplicationServiceDependency
from app.domain import JobApplication
from app.services.applications import MAX_RESUME_BYTES

router = APIRouter()


@router.post(
    "/jobs/{job_id}/applications",
    response_model=JobApplication,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a job with a PDF resume",
)
async def submit_application(
    job_id: str,
    service: ApplicationServiceDependency,
    candidate_name: Annotated[str, Form(alias="candidateName", min_length=1, max_length=120)],
    candidate_email: Annotated[str, Form(alias="candidateEmail", max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")],
    resume: Annotated[UploadFile, File(description="PDF resume, 5 MB maximum")],
    message: Annotated[str, Form(max_length=2000)] = "",
) -> JobApplication:
    data = await resume.read(MAX_RESUME_BYTES + 1)
    # ApplicationNotAllowedError is a ValueError, which execute() maps to 400.
    return await execute(lambda: service.submit(job_id, candidate_name, candidate_email, message, resume.filename, data))


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
