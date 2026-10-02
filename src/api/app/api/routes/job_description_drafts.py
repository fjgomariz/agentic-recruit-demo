"""AI-assisted job authoring endpoints backed by Foundry agents."""

from fastapi import APIRouter, HTTPException, status

from app.dependencies.agents import JobDescriptionAgent
from app.domain import JobDescriptionDraftResult, JobDescriptionRequest
from app.services import AgentResponseError, AgentUnavailableError

router = APIRouter()


@router.post(
    "",
    response_model=JobDescriptionDraftResult,
    response_model_by_alias=True,
    summary="Draft a job description with the Foundry job description agent",
)
async def create_job_description_draft(request: JobDescriptionRequest, agent: JobDescriptionAgent) -> JobDescriptionDraftResult:
    try:
        return await agent.generate(request)
    except AgentUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except AgentResponseError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
