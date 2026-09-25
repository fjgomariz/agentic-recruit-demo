"""Application-scoped repository and service dependencies."""

import asyncio
import contextlib
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.config import CosmosSettings
from app.domain import Candidate, CandidateEvaluation, Job
from app.repositories import CosmosJobRepository, InMemoryRepository
from app.repositories.seed import create_seed_candidates, create_seed_evaluations
from app.services import CrudService

logger = logging.getLogger(__name__)

COSMOS_RETRY_SECONDS = 10

_job_repository: CosmosJobRepository | None = None
_job_service: CrudService[Job] | None = None
_job_service_task: asyncio.Task[None] | None = None
_candidate_service = CrudService(InMemoryRepository(create_seed_candidates()), "Candidate")
_evaluation_service = CrudService(InMemoryRepository(create_seed_evaluations()), "Evaluation")


async def _connect_job_service(settings: CosmosSettings) -> None:
    """Connect to the Cosmos DB jobs container."""

    global _job_repository, _job_service
    repository = CosmosJobRepository(settings)
    try:
        await repository.initialize()
    except BaseException:
        await repository.close()
        raise
    _job_repository = repository
    _job_service = CrudService(repository, "Job")


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
    """Validate configuration and connect to Cosmos DB in the background."""

    global _job_service_task
    settings = CosmosSettings.from_environment()
    _job_service_task = asyncio.create_task(_connect_job_service_with_retry(settings))


async def close_job_service() -> None:
    """Stop pending connection attempts and close the Cosmos DB client."""

    global _job_repository, _job_service, _job_service_task
    if _job_service_task is not None:
        _job_service_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _job_service_task
    if _job_repository is not None:
        await _job_repository.close()
    _job_repository = None
    _job_service = None
    _job_service_task = None


def get_job_service() -> CrudService[Job]:
    """Provide the application-scoped job service."""

    if _job_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job storage is still connecting. Retry shortly.",
        )
    return _job_service


def get_candidate_service() -> CrudService[Candidate]:
    """Provide the application-scoped candidate service."""

    return _candidate_service


def get_evaluation_service() -> CrudService[CandidateEvaluation]:
    """Provide the application-scoped evaluation service."""

    return _evaluation_service


JobService = Annotated[CrudService[Job], Depends(get_job_service)]
CandidateService = Annotated[CrudService[Candidate], Depends(get_candidate_service)]
EvaluationService = Annotated[CrudService[CandidateEvaluation], Depends(get_evaluation_service)]