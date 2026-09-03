"""Candidate REST endpoints."""

from fastapi import APIRouter, status

from app.api.errors import execute
from app.dependencies.services import CandidateService
from app.domain import Candidate

router = APIRouter()


@router.get("", response_model=list[Candidate], summary="List candidates")
async def list_candidates(service: CandidateService) -> list[Candidate]:
    return await service.list()


@router.get("/{candidate_id}", response_model=Candidate, summary="Get a candidate")
async def get_candidate(candidate_id: str, service: CandidateService) -> Candidate:
    return await execute(lambda: service.get(candidate_id))


@router.post("", response_model=Candidate, status_code=status.HTTP_201_CREATED, summary="Create a candidate")
async def create_candidate(candidate: Candidate, service: CandidateService) -> Candidate:
    return await execute(lambda: service.create(candidate))


@router.put("/{candidate_id}", response_model=Candidate, summary="Update a candidate")
async def update_candidate(candidate_id: str, candidate: Candidate, service: CandidateService) -> Candidate:
    return await execute(lambda: service.update(candidate_id, candidate))