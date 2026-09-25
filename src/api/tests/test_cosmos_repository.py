"""Focused behavior checks for Cosmos DB Job persistence."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.cosmos import CosmosJobRepository
from job_fixtures import create_sample_jobs


class FakeContainer:
    """Async container double whose methods accept only the arguments the Cosmos SDK honors.

    The SDK forwards unknown keyword arguments to aiohttp, so a lenient fake would hide
    calls that fail against a real account (for example ``replace_item(partition_key=...)``).
    """

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def query_items(self, query: str) -> Any:
        assert query == "SELECT * FROM jobs"

        async def results() -> Any:
            for item in self.items.values():
                yield item.copy()

        return results()

    async def read_item(self, item: str, partition_key: str) -> dict[str, Any]:
        assert partition_key == item
        return self.items[item].copy()

    async def create_item(self, body: dict[str, Any]) -> dict[str, Any]:
        self.items[body["id"]] = body.copy()
        return body.copy()

    async def replace_item(self, item: str, body: dict[str, Any]) -> dict[str, Any]:
        assert body["id"] == item
        self.items[item] = body.copy()
        return body.copy()

    async def delete_item(self, item: str, partition_key: str) -> None:
        assert partition_key == item
        del self.items[item]


@pytest.mark.asyncio
async def test_initialize_binds_existing_container_without_creating_resources() -> None:
    container = AsyncMock()
    database = MagicMock()
    database.get_container_client.return_value = container
    client = MagicMock()
    client.get_database_client.return_value = database
    repository = CosmosJobRepository.__new__(CosmosJobRepository)
    repository._client = client
    repository._database_name = "recruitment"
    repository._container_name = "jobs"
    repository._container = None

    await repository.initialize()

    client.get_database_client.assert_called_once_with("recruitment")
    database.get_container_client.assert_called_once_with("jobs")
    container.read.assert_awaited_once()
    assert repository._container is container
    assert not client.create_database_if_not_exists.called


@pytest.mark.asyncio
async def test_cosmos_job_repository_round_trip() -> None:
    container = FakeContainer()
    repository = CosmosJobRepository.__new__(CosmosJobRepository)
    repository._container = container
    job = create_sample_jobs()[0].model_copy(update={"id": "cosmos-job"})

    created = await repository.create(job)
    assert created == job
    assert container.items[job.id]["employmentType"] == "Full-time"
    assert "employment_type" not in container.items[job.id]
    assert await repository.get(job.id) == job
    assert await repository.list() == [job]

    updated_job = job.model_copy(update={"title": "Updated title"})
    assert await repository.update(updated_job) == updated_job
    assert await repository.delete(job.id) is True
    assert container.items == {}