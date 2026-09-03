"""Candidate evaluation REST endpoints."""

from fastapi import APIRouter, status

from app.api.errors import execute
from app.dependencies.services import EvaluationService
from app.domain import CandidateEvaluation

router = APIRouter()


@router.get("", response_model=list[CandidateEvaluation], summary="List evaluations")
async def list_evaluations(service: EvaluationService) -> list[CandidateEvaluation]:
    return await service.list()


@router.get("/{evaluation_id}", response_model=CandidateEvaluation, summary="Get an evaluation")
async def get_evaluation(evaluation_id: str, service: EvaluationService) -> CandidateEvaluation:
    return await execute(lambda: service.get(evaluation_id))


@router.post("", response_model=CandidateEvaluation, status_code=status.HTTP_201_CREATED, summary="Create an evaluation")
async def create_evaluation(evaluation: CandidateEvaluation, service: EvaluationService) -> CandidateEvaluation:
    return await execute(lambda: service.create(evaluation))


@router.put("/{evaluation_id}", response_model=CandidateEvaluation, summary="Update an evaluation")
async def update_evaluation(evaluation_id: str, evaluation: CandidateEvaluation, service: EvaluationService) -> CandidateEvaluation:
    return await execute(lambda: service.update(evaluation_id, evaluation))