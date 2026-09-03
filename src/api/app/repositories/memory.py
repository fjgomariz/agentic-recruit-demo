"""In-memory repository used before Azure persistence is introduced."""

from typing import Generic, TypeVar

from pydantic import BaseModel

Entity = TypeVar("Entity", bound=BaseModel)


class InMemoryRepository(Generic[Entity]):
    """Store Pydantic entities by stable identifier for the demo process lifetime."""

    def __init__(self, seed: list[Entity] | None = None) -> None:
        self._items = {item.id: item.model_copy(deep=True) for item in seed or []}

    async def list(self) -> list[Entity]:
        """Return defensive copies of all entities."""

        return [item.model_copy(deep=True) for item in self._items.values()]

    async def get(self, entity_id: str) -> Entity | None:
        """Return a defensive copy of one entity when present."""

        item = self._items.get(entity_id)
        return item.model_copy(deep=True) if item else None

    async def create(self, entity: Entity) -> Entity:
        """Insert an entity, rejecting duplicate identifiers."""

        if entity.id in self._items:
            raise ValueError(f"Entity '{entity.id}' already exists")
        self._items[entity.id] = entity.model_copy(deep=True)
        return entity.model_copy(deep=True)

    async def update(self, entity: Entity) -> Entity | None:
        """Replace an existing entity and return a defensive copy."""

        if entity.id not in self._items:
            return None
        self._items[entity.id] = entity.model_copy(deep=True)
        return entity.model_copy(deep=True)