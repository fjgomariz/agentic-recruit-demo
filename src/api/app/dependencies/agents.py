"""Application-scoped Foundry agent clients."""

import logging
from contextlib import AsyncExitStack
from typing import Annotated

from fastapi import Depends

from app.config import AgentSettings
from app.services import JobDescriptionAgentService

logger = logging.getLogger(__name__)

_exit_stack: AsyncExitStack | None = None
_job_description_agent = JobDescriptionAgentService(AgentSettings(project_endpoint=None), client=None)


async def initialize_agent_services() -> None:
    """Create the Foundry project and OpenAI clients when an endpoint is configured."""

    global _exit_stack, _job_description_agent
    settings = AgentSettings.from_environment()
    if not settings.project_endpoint:
        logger.warning("AZURE_AI_PROJECT_ENDPOINT is not set; AI-assisted features are disabled")
        _job_description_agent = JobDescriptionAgentService(settings, client=None)
        return

    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import DefaultAzureCredential

    stack = AsyncExitStack()
    credential = await stack.enter_async_context(DefaultAzureCredential())
    project = await stack.enter_async_context(AIProjectClient(endpoint=settings.project_endpoint, credential=credential))
    openai_client = await stack.enter_async_context(project.get_openai_client())
    _exit_stack = stack
    _job_description_agent = JobDescriptionAgentService(settings, client=openai_client)
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


JobDescriptionAgent = Annotated[JobDescriptionAgentService, Depends(get_job_description_agent)]
