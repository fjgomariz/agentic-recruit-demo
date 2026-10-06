"""Application-scoped repository and service dependencies."""

import asyncio
import contextlib
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.config import CosmosSettings, StorageSettings
from app.domain import Job
from app.repositories import CosmosApplicationRepository, CosmosJobRepository
from app.services import ApplicationService, CrudService
from app.storage import BlobResumeStore

logger = logging.getLogger(__name__)

COSMOS_RETRY_SECONDS = 10

_job_repository: CosmosJobRepository | None = None
_job_service: CrudService[Job] | None = None
_application_repository: CosmosApplicationRepository | None = None
_resume_store: BlobResumeStore | None = None
_job_service_task: asyncio.Task[None] | None = None


async def _connect_job_service(settings: CosmosSettings) -> None:
    """Connect to the Cosmos DB jobs and applications containers."""

    global _job_repository, _job_service, _application_repository
    repository = CosmosJobRepository(settings)
    try:
        await repository.initialize()
        applications = CosmosApplicationRepository(repository.client, settings)
        await applications.initialize()
    except BaseException:
        await repository.close()
        raise
    _job_repository = repository
    _job_service = CrudService(repository, "Job")
    _application_repository = applications


async def _connect_job_service_with_retry(settings: CosmosSettings) -> None:
    """Keep retrying so transient network or RBAC propagation delays never crash the API."""

    while True:
        try:
            await _connect_job_service(settings)
            return
        except Exception:
            logger.exception("Cosmos DB is not reachable yet; retrying in %s seconds", COSMOS_RETRY_SECONDS)
            await asyncio.sleep(COSMOS_RETRY_SECONDS)


async def initialize_job_service() -> None:
    """Validate configuration, open the resume store, and connect to Cosmos DB in the background."""

    global _job_service_task, _resume_store
    settings = CosmosSettings.from_environment()
    storage_settings = StorageSettings.from_environment()
    if storage_settings.blob_endpoint:
        _resume_store = BlobResumeStore(storage_settings)
    else:
        logger.warning("AZURE_STORAGE_BLOB_ENDPOINT is not set; candidate applications are disabled")
    _job_service_task = asyncio.create_task(_connect_job_service_with_retry(settings))


async def close_job_service() -> None:
    """Stop pending connection attempts and close the Cosmos DB and Blob Storage clients."""

    global _job_repository, _job_service, _job_service_task, _application_repository, _resume_store
    if _job_service_task is not None:
        _job_service_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _job_service_task
    if _job_repository is not None:
        await _job_repository.close()
    if _resume_store is not None:
        await _resume_store.close()
    _job_repository = None
    _job_service = None
    _job_service_task = None
    _application_repository = None
    _resume_store = None


def get_job_service() -> CrudService[Job]:
    """Provide the application-scoped job service."""

    if _job_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job storage is still connecting. Retry shortly.",
        )
    return _job_service


def get_application_service(jobs: Annotated[CrudService[Job], Depends(get_job_service)]) -> ApplicationService:
    """Provide the application service once Cosmos DB and Blob Storage are available."""

    if _application_repository is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Application storage is still connecting. Retry shortly.")
    if _resume_store is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Resume storage is not configured.")
    return ApplicationService(jobs, _application_repository, _resume_store)


JobService = Annotated[CrudService[Job], Depends(get_job_service)]
ApplicationServiceDependency = Annotated[ApplicationService, Depends(get_application_service)]