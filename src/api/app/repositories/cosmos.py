"""Azure Cosmos DB persistence for jobs and candidate applications."""

import logging
from typing import Any

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import (
    CosmosHttpResponseError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)
from azure.identity.aio import DefaultAzureCredential
from pydantic import BaseModel

from app.config import CosmosSettings
from app.domain import AgentExecution, Job, JobApplication

logger = logging.getLogger(__name__)


class CosmosJobRepository:
    """Persist jobs in the id-partitioned Cosmos DB jobs container."""

    def __init__(self, settings: CosmosSettings) -> None:
        credential = settings.key or DefaultAzureCredential()
        self._credential = credential if not settings.key else None
        self._client = CosmosClient(settings.endpoint, credential=credential)
        self._database_name = settings.database_name
        self._container_name = settings.jobs_container_name
        self._container: Any | None = None

    async def initialize(self) -> None:
        """Bind to the provisioned database and jobs container and verify access."""

        try:
            database = self._client.get_database_client(self._database_name)
            container = database.get_container_client(self._container_name)
            await container.read()
            self._container = container
            logger.info(
                "Cosmos DB Job repository initialized database=%s container=%s",
                self._database_name,
                self._container_name,
            )
        except CosmosHttpResponseError:
            logger.exception("Failed to initialize the Cosmos DB Job repository")
            raise

    async def close(self) -> None:
        """Release Cosmos DB and identity client resources."""

        await self._client.close()
        if self._credential is not None:
            await self._credential.close()

    async def list(self) -> list[Job]:
        """Return every job in the container."""

        container = self._get_container()
        try:
            items = container.query_items(query="SELECT * FROM jobs")
            return [Job.model_validate(item) async for item in items]
        except CosmosHttpResponseError:
            logger.exception("Failed to list jobs from Cosmos DB")
            raise

    async def get(self, entity_id: str) -> Job | None:
        """Return one job by its identifier and partition key."""

        try:
            item = await self._get_container().read_item(item=entity_id, partition_key=entity_id)
            return Job.model_validate(item)
        except CosmosResourceNotFoundError:
            return None
        except CosmosHttpResponseError:
            logger.exception("Failed to read Job id=%s from Cosmos DB", entity_id)
            raise

    async def create(self, entity: Job) -> Job:
        """Create a job while preserving duplicate-ID behavior."""

        try:
            item = await self._get_container().create_item(body=self._serialize(entity))
            logger.info("Created Job id=%s", entity.id)
            return Job.model_validate(item)
        except CosmosResourceExistsError as error:
            raise ValueError(f"Entity '{entity.id}' already exists") from error
        except CosmosHttpResponseError:
            logger.exception("Failed to create Job id=%s in Cosmos DB", entity.id)
            raise

    async def update(self, entity: Job) -> Job | None:
        """Replace an existing job."""

        try:
            item = await self._get_container().replace_item(
                item=entity.id,
                body=self._serialize(entity),
            )
            logger.info("Updated Job id=%s", entity.id)
            return Job.model_validate(item)
        except CosmosResourceNotFoundError:
            return None
        except CosmosHttpResponseError:
            logger.exception("Failed to update Job id=%s in Cosmos DB", entity.id)
            raise

    async def delete(self, entity_id: str) -> bool:
        """Delete a job and report whether it existed."""

        try:
            await self._get_container().delete_item(item=entity_id, partition_key=entity_id)
            logger.info("Deleted Job id=%s", entity_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except CosmosHttpResponseError:
            logger.exception("Failed to delete Job id=%s from Cosmos DB", entity_id)
            raise

    def _get_container(self) -> Any:
        if self._container is None:
            raise RuntimeError("CosmosJobRepository.initialize() must be called before use")
        return self._container

    @property
    def client(self) -> CosmosClient:
        """Cosmos DB client shared with other repositories on the same account."""

        return self._client

    @staticmethod
    def _serialize(entity: Job) -> dict[str, Any]:
        return entity.model_dump(mode="json", by_alias=True, exclude_none=True)


class CosmosApplicationRepository:
    """Persist candidate applications in the job-partitioned applications container.

    The repository borrows a Cosmos client owned by another repository and never closes it.
    """

    def __init__(self, client: CosmosClient, settings: CosmosSettings) -> None:
        self._client = client
        self._database_name = settings.database_name
        self._container_name = settings.applications_container_name
        self._container: Any | None = None

    async def initialize(self) -> None:
        """Bind to the provisioned applications container and verify access."""

        container = self._client.get_database_client(self._database_name).get_container_client(self._container_name)
        await container.read()
        self._container = container
        logger.info("Cosmos DB application repository initialized container=%s", self._container_name)

    async def create(self, application: JobApplication) -> JobApplication:
        """Store a new application."""

        body = application.model_dump(mode="json", by_alias=True, exclude_none=True)
        item = await self._get_container().create_item(body=body)
        logger.info("Created application id=%s job=%s", application.id, application.job_id)
        return JobApplication.model_validate(item)

    async def list_for_job(self, job_id: str) -> list[JobApplication]:
        """Return a job's applications, newest first."""

        items = self._get_container().query_items(
            query="SELECT * FROM c WHERE c.jobId = @jobId ORDER BY c.submittedAt DESC",
            parameters=[{"name": "@jobId", "value": job_id}],
            partition_key=job_id,
        )
        return [JobApplication.model_validate(item) async for item in items]

    async def list_all(self) -> list[JobApplication]:
        """Return every application across jobs, newest first (sorted in memory; demo-scale data)."""

        items = self._get_container().query_items(query="SELECT * FROM c")
        applications = [JobApplication.model_validate(item) async for item in items]
        return sorted(applications, key=lambda application: application.submitted_at, reverse=True)

    async def get(self, application_id: str) -> JobApplication | None:
        """Return one application by identifier, searching across jobs."""

        items = self._get_container().query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": application_id}],
        )
        async for item in items:
            return JobApplication.model_validate(item)
        return None

    async def set_fields(self, application: JobApplication, fields: dict[str, BaseModel | None]) -> JobApplication:
        """Set top-level fields with one partial update, so assessment steps never overwrite each other."""

        operations = [
            {"op": "set", "path": f"/{name}", "value": value.model_dump(mode="json", by_alias=True, exclude_none=True) if value is not None else None}
            for name, value in fields.items()
        ]
        if not operations:
            return application
        item = await self._get_container().patch_item(item=application.id, partition_key=application.job_id, patch_operations=operations)
        return JobApplication.model_validate(item)

    def _get_container(self) -> Any:
        if self._container is None:
            raise RuntimeError("CosmosApplicationRepository.initialize() must be called before use")
        return self._container


class CosmosAgentExecutionRepository:
    """Record Foundry agent runs in the agent-executions container (partitioned by agent name)."""

    def __init__(self, client: CosmosClient, settings: CosmosSettings) -> None:
        self._client = client
        self._database_name = settings.database_name
        self._container_name = settings.agent_executions_container_name
        self._container: Any | None = None

    async def initialize(self) -> None:
        container = self._client.get_database_client(self._database_name).get_container_client(self._container_name)
        await container.read()
        self._container = container
        logger.info("Cosmos DB agent execution repository initialized container=%s", self._container_name)

    async def create(self, execution: AgentExecution) -> AgentExecution:
        body = execution.model_dump(mode="json", by_alias=True, exclude_none=True)
        item = await self._get_container().create_item(body=body)
        return AgentExecution.model_validate(item)

    async def list_recent(self, limit: int) -> list[AgentExecution]:
        """Return the most recent runs across agents (sorted in memory; demo-scale data)."""

        items = self._get_container().query_items(query="SELECT * FROM c")
        executions = [AgentExecution.model_validate(item) async for item in items]
        return sorted(executions, key=lambda execution: execution.started_at, reverse=True)[:limit]

    def _get_container(self) -> Any:
        if self._container is None:
            raise RuntimeError("CosmosAgentExecutionRepository.initialize() must be called before use")
        return self._container