"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import applications, candidates, evaluations, health, job_description_drafts, jobs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(applications.router, tags=["Applications"])
api_router.include_router(job_description_drafts.router, prefix="/job-description-drafts", tags=["AI authoring"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluations"])