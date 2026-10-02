"""Invoke the Foundry job description agent through the Responses API."""

import json
import logging
from typing import Any, Protocol

from pydantic import ValidationError

from app.config import AgentSettings
from app.domain import JobDescriptionDraft, JobDescriptionDraftResult, JobDescriptionRequest

logger = logging.getLogger(__name__)


class AgentUnavailableError(RuntimeError):
    """Raised when the agent is not configured or cannot be reached."""


class AgentResponseError(RuntimeError):
    """Raised when the agent answers with content that does not match the expected draft."""


class ResponsesClient(Protocol):
    """Subset of the OpenAI Responses client used by the service."""

    @property
    def responses(self) -> Any: ...


def build_agent_input(request: JobDescriptionRequest) -> str:
    """Render role facts and recruiter notes as the user message for the agent."""

    facts = {
        "Title": request.title,
        "Department": request.department,
        "Location": request.location,
        "Workplace type": request.workplace_type,
        "Employment type": request.employment_type,
        "Experience level": request.experience_level,
        "Hiring manager": request.hiring_manager,
    }
    lines = ["Role facts:"]
    lines += [f"- {label}: {value}" for label, value in facts.items() if value]
    lines += ["", "Recruiter notes:", request.notes.strip() or "(none)"]
    return "\n".join(lines)


def _agent_version(response: Any) -> str | None:
    agent = getattr(response, "agent_reference", None) or getattr(response, "agent", None)
    if isinstance(agent, dict):
        return agent.get("version")
    return getattr(agent, "version", None)


class JobDescriptionAgentService:
    """Generate job description drafts with the Foundry prompt agent."""

    def __init__(self, settings: AgentSettings, client: ResponsesClient | None) -> None:
        self._agent_name = settings.job_description_agent_name
        self._client = client

    async def generate(self, request: JobDescriptionRequest) -> JobDescriptionDraftResult:
        if self._client is None:
            raise AgentUnavailableError("The job description agent is not configured")

        try:
            response = await self._client.responses.create(
                input=build_agent_input(request),
                extra_body={"agent_reference": {"name": self._agent_name, "type": "agent_reference"}},
            )
        except Exception as error:
            logger.exception("Job description agent call failed agent=%s", self._agent_name)
            raise AgentUnavailableError("The job description agent could not be reached") from error

        try:
            draft = JobDescriptionDraft.model_validate(json.loads(response.output_text))
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            logger.exception("Job description agent returned an invalid draft response_id=%s", response.id)
            raise AgentResponseError("The job description agent returned an invalid draft") from error

        logger.info("Generated job description draft agent=%s response_id=%s", self._agent_name, response.id)
        return JobDescriptionDraftResult(
            draft=draft,
            execution_id=response.id,
            agent_name=self._agent_name,
            agent_version=_agent_version(response),
        )
