"""Agent run recording shared by the agent services and the AI Operations endpoint."""

import logging

from app.domain import AgentExecution
from app.repositories import CosmosAgentExecutionRepository

logger = logging.getLogger(__name__)

_repository: CosmosAgentExecutionRepository | None = None


def set_repository(repository: CosmosAgentExecutionRepository | None) -> None:
    global _repository
    _repository = repository


def get_repository() -> CosmosAgentExecutionRepository | None:
    return _repository


class CosmosAgentRunRecorder:
    """Store agent runs once Cosmos DB is connected; earlier runs are only logged."""

    async def record(self, execution: AgentExecution) -> None:
        if _repository is None:
            logger.warning("Agent run not recorded because Cosmos DB is still connecting id=%s", execution.id)
            return
        await _repository.create(execution)
