"""Azure Cosmos DB persistence for Job entities."""

import logging
from typing import Any

from azure.cosmos import PartitionKey
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import (
    CosmosHttpResponseError,
    CosmosResourceExistsError,
    CosmosResourceNotFoundError,
)
from azure.identity.aio import DefaultAzureCredential

from app.config import CosmosSettings
from app.domain import Job

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
        """Create the configured database and jobs container when absent."""

        try:
            database = await self._client.create_database_if_not_exists(self._database_name)
            self._container = await database.create_container_if_not_exists(
                id=self._container_name,
                partition_key=PartitionKey(path="/id"),
            )
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
                partition_key=entity.id,
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

    @staticmethod
    def _serialize(entity: Job) -> dict[str, Any]:
        return entity.model_dump(mode="json", by_alias=True, exclude_none=True)