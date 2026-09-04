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