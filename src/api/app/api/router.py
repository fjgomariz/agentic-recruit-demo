"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import candidates, evaluations, health, jobs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluations"])