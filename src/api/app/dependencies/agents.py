"""Application-scoped Foundry agent clients."""

import logging
from contextlib import AsyncExitStack
from typing import Annotated

from fastapi import Depends

from app.config import AgentSettings, KnowledgeSettings
from app.dependencies.recording import CosmosAgentRunRecorder
from app.services import (
    CandidateEvaluationAgentService,
    CandidateReviewAgentService,
    JobDescriptionAgentService,
    KnowledgeBaseClient,
    TalentPoolAgentService,
)

logger = logging.getLogger(__name__)

SEARCH_SCOPE = "https://search.azure.com/.default"

_recorder = CosmosAgentRunRecorder()
_exit_stack: AsyncExitStack | None = None
_job_description_agent = JobDescriptionAgentService(AgentSettings(project_endpoint=None), client=None)
_candidate_evaluation_agent = CandidateEvaluationAgentService(AgentSettings(project_endpoint=None), client=None)
_candidate_review_agent = CandidateReviewAgentService(AgentSettings(project_endpoint=None), client=None)
_talent_pool_agent = TalentPoolAgentService(AgentSettings(project_endpoint=None), client=None)


async def initialize_agent_services() -> None:
    """Create the Foundry project and OpenAI clients when an endpoint is configured."""

    global _exit_stack, _job_description_agent, _candidate_evaluation_agent, _candidate_review_agent, _talent_pool_agent
    settings = AgentSettings.from_environment()
    if not settings.project_endpoint:
        logger.warning("AZURE_AI_PROJECT_ENDPOINT is not set; AI-assisted features are disabled")
        _job_description_agent = JobDescriptionAgentService(settings, client=None)
        _candidate_evaluation_agent = CandidateEvaluationAgentService(settings, client=None)
        _candidate_review_agent = CandidateReviewAgentService(settings, client=None)
        _talent_pool_agent = TalentPoolAgentService(settings, client=None)
        return

    import httpx
    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import DefaultAzureCredential

    stack = AsyncExitStack()
    credential = await stack.enter_async_context(DefaultAzureCredential())
    project = await stack.enter_async_context(AIProjectClient(endpoint=settings.project_endpoint, credential=credential))
    openai_client = await stack.enter_async_context(project.get_openai_client())

    knowledge_settings = KnowledgeSettings.from_environment()
    knowledge: KnowledgeBaseClient | None = None
    if knowledge_settings.search_endpoint:
        async def search_token() -> str:
            return (await credential.get_token(SEARCH_SCOPE)).token

        http = await stack.enter_async_context(httpx.AsyncClient())
        knowledge = KnowledgeBaseClient(knowledge_settings, search_token, http)
    else:
        logger.warning("AZURE_SEARCH_ENDPOINT is not set; the retrieval plan of talent pool searches is not shown")

    _exit_stack = stack
    _job_description_agent = JobDescriptionAgentService(settings, client=openai_client, recorder=_recorder)
    _candidate_evaluation_agent = CandidateEvaluationAgentService(settings, client=openai_client, recorder=_recorder)
    _candidate_review_agent = CandidateReviewAgentService(settings, client=openai_client, recorder=_recorder)
    _talent_pool_agent = TalentPoolAgentService(settings, client=openai_client, knowledge=knowledge, recorder=_recorder)
    logger.info("Foundry agents configured endpoint=%s", settings.project_endpoint)


async def close_agent_services() -> None:
    """Close Foundry clients and credentials."""

    global _exit_stack
    if _exit_stack is not None:
        await _exit_stack.aclose()
    _exit_stack = None


def get_job_description_agent() -> JobDescriptionAgentService:
    """Provide the application-scoped job description agent service."""

    return _job_description_agent


def get_candidate_evaluation_agent() -> CandidateEvaluationAgentService:
    """Provide the application-scoped candidate evaluation agent service."""

    return _candidate_evaluation_agent


def get_candidate_review_agent() -> CandidateReviewAgentService:
    """Provide the application-scoped evaluation reviewer agent service."""

    return _candidate_review_agent


def get_talent_pool_agent() -> TalentPoolAgentService:
    """Provide the application-scoped recruiter copilot service."""

    return _talent_pool_agent


JobDescriptionAgent = Annotated[JobDescriptionAgentService, Depends(get_job_description_agent)]
CandidateEvaluationAgent = Annotated[CandidateEvaluationAgentService, Depends(get_candidate_evaluation_agent)]
CandidateReviewAgent = Annotated[CandidateReviewAgentService, Depends(get_candidate_review_agent)]
TalentPoolAgent = Annotated[TalentPoolAgentService, Depends(get_talent_pool_agent)]
