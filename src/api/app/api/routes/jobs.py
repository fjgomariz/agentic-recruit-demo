"""Job REST endpoints."""

from fastapi import APIRouter, Response, status

from app.api.errors import execute
from app.dependencies.services import JobService
from app.domain import Job

router = APIRouter()


@router.get("", response_model=list[Job], summary="List jobs")
async def list_jobs(service: JobService) -> list[Job]:
    return await service.list()


@router.get("/{job_id}", response_model=Job, summary="Get a job")
async def get_job(job_id: str, service: JobService) -> Job:
    return await execute(lambda: service.get(job_id))


@router.post("", response_model=Job, status_code=status.HTTP_201_CREATED, summary="Create a job")
async def create_job(job: Job, service: JobService) -> Job:
    return await execute(lambda: service.create(job))


@router.put("/{job_id}", response_model=Job, summary="Update a job")
async def update_job(job_id: str, job: Job, service: JobService) -> Job:
    return await execute(lambda: service.update(job_id, job))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a job")
async def delete_job(job_id: str, service: JobService) -> Response:
    await execute(lambda: service.delete(job_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)