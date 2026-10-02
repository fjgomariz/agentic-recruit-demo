"""Environment-backed application configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CosmosSettings:
    """Connection settings for the recruitment Cosmos DB account."""

    endpoint: str
    database_name: str = "recruitment"
    jobs_container_name: str = "jobs"
    key: str | None = None

    @classmethod
    def from_environment(cls) -> "CosmosSettings":
        """Load Cosmos DB settings from process environment variables."""

        endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
        if not endpoint:
            raise RuntimeError("AZURE_COSMOS_ENDPOINT must be configured")
        return cls(
            endpoint=endpoint,
            database_name=os.getenv("AZURE_COSMOS_DATABASE_NAME", "recruitment"),
            jobs_container_name=os.getenv("AZURE_COSMOS_JOBS_CONTAINER_NAME", "jobs"),
            key=os.getenv("AZURE_COSMOS_KEY"),
        )


@dataclass(frozen=True)
class AgentSettings:
    """Connection settings for the Foundry project that hosts the recruitment agents."""

    project_endpoint: str | None
    job_description_agent_name: str = "job-description-writer"

    @classmethod
    def from_environment(cls) -> "AgentSettings":
        """Load agent settings; a missing endpoint disables AI features instead of failing startup."""

        return cls(
            project_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or None,
            job_description_agent_name=os.getenv("JOB_DESCRIPTION_AGENT_NAME", "job-description-writer"),
        )