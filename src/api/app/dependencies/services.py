"""Application-scoped repository and service dependencies."""

from typing import Annotated

from fastapi import Depends

from app.domain import Candidate, CandidateEvaluation, Job
from app.repositories import InMemoryRepository
from app.repositories.seed import create_seed_candidates, create_seed_evaluations, create_seed_jobs
from app.services import CrudService

_job_service = CrudService(InMemoryRepository(create_seed_jobs()), "Job")
_candidate_service = CrudService(InMemoryRepository(create_seed_candidates()), "Candidate")
_evaluation_service = CrudService(InMemoryRepository(create_seed_evaluations()), "Evaluation")


def get_job_service() -> CrudService[Job]:
    """Provide the application-scoped job service."""

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