"""Application-scoped repository and service dependencies."""

import logging
from typing import Annotated

from fastapi import Depends

from app.config import CosmosSettings
from app.domain import Candidate, CandidateEvaluation, Job
from app.repositories import CosmosJobRepository, InMemoryRepository
from app.repositories.seed import create_seed_candidates, create_seed_evaluations, create_seed_jobs
from app.services import CrudService

logger = logging.getLogger(__name__)

_job_repository: CosmosJobRepository | None = None
_job_service: CrudService[Job] | None = None
_candidate_service = CrudService(InMemoryRepository(create_seed_candidates()), "Candidate")
_evaluation_service = CrudService(InMemoryRepository(create_seed_evaluations()), "Evaluation")


async def initialize_job_service() -> None:
    """Initialize Cosmos DB persistence and seed a new demo container."""

    global _job_repository, _job_service
    repository = CosmosJobRepository(CosmosSettings.from_environment())
    try:
        await repository.initialize()
        if not await repository.list():
            for job in create_seed_jobs():
                await repository.create(job)
            logger.info("Seeded the empty Cosmos DB jobs container")
    except Exception:
        await repository.close()
        raise
    _job_repository = repository
    _job_service = CrudService(repository, "Job")


async def close_job_service() -> None:
    """Close the application-scoped Cosmos DB client."""

    global _job_repository, _job_service
    if _job_repository is not None:
        await _job_repository.close()
    _job_repository = None
    _job_service = None


def get_job_service() -> CrudService[Job]:
    """Provide the application-scoped job service."""

    if _job_service is None:
        raise RuntimeError("Job service has not been initialized")
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