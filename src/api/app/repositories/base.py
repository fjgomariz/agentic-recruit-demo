"""Repository contracts for domain persistence."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

Entity = TypeVar("Entity", bound=BaseModel)


class Repository(Protocol[Entity]):
    """Minimal asynchronous CRUD contract used by application services."""

    async def list(self) -> list[Entity]: ...

    async def get(self, entity_id: str) -> Entity | None: ...

    async def create(self, entity: Entity) -> Entity: ...

    async def update(self, entity: Entity) -> Entity | None: ...