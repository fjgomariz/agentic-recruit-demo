"""Talent pool matching: past candidates for an open job, and the documents the answer cites."""

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response, status

from app.api.errors import execute
from app.dependencies.agents import TalentPoolAgent
from app.dependencies.services import JobService, KnowledgeDocumentStoreDependency
from app.domain import TalentMatchRequest, TalentMatchResult
from app.services import AgentResponseError, AgentUnavailableError
from app.storage import KnowledgeDocumentNotFoundError

router = APIRouter()


@router.post(
    "/jobs/{job_id}/talent-matches",
    response_model=TalentMatchResult,
    response_model_by_alias=True,
    summary="Find past candidates for a job in the talent pool with the Foundry IQ recruiter copilot",
)
async def find_talent_matches(job_id: str, request: TalentMatchRequest, jobs: JobService, agent: TalentPoolAgent) -> TalentMatchResult:
    job = await execute(lambda: jobs.get(job_id))
    try:
        return await agent.match(job, request.notes)
    except AgentUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except AgentResponseError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.get(
    "/knowledge-documents/{container}/{file_name}",
    summary="Open a talent pool resume or hiring policy cited by the recruiter copilot",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}, "text/plain": {}}}},
)
async def download_knowledge_document(container: str, file_name: str, store: KnowledgeDocumentStoreDependency) -> Response:
    try:
        content, media_type = await store.download(container, file_name)
    except KnowledgeDocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(file_name)}", "X-Content-Type-Options": "nosniff"},
    )
