"""Service health endpoint."""

from fastapi import APIRouter

from app.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Check API health")
async def health() -> HealthResponse:
    """Return a lightweight liveness response."""

    return HealthResponse()