"""Simple CRUD application service shared by API resources."""

from typing import Generic, TypeVar

from pydantic import BaseModel

from app.repositories.base import Repository

Entity = TypeVar("Entity", bound=BaseModel)


class EntityNotFoundError(LookupError):
    """Raised when a requested domain entity does not exist."""


class EntityAlreadyExistsError(ValueError):
    """Raised when creating an entity with an existing identifier."""


class CrudService(Generic[Entity]):
    """Coordinate basic CRUD behavior independently of storage technology."""

    def __init__(self, repository: Repository[Entity], resource_name: str) -> None:
        self._repository = repository
        self._resource_name = resource_name

    async def list(self) -> list[Entity]:
        """List all entities in repository order."""

        return await self._repository.list()

    async def get(self, entity_id: str) -> Entity:
        """Get one entity or raise a domain-friendly error."""

        entity = await self._repository.get(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"{self._resource_name} '{entity_id}' was not found")
        return entity

    async def create(self, entity: Entity) -> Entity:
        """Create one entity with duplicate-ID handling."""

        try:
            return await self._repository.create(entity)
        except ValueError as error:
            raise EntityAlreadyExistsError(str(error)) from error

    async def update(self, entity_id: str, entity: Entity) -> Entity:
        """Replace an entity after validating the route and body identifiers."""

        if entity.id != entity_id:
            raise ValueError("Path identifier must match the request body identifier")
        updated = await self._repository.update(entity)
        if updated is None:
            raise EntityNotFoundError(f"{self._resource_name} '{entity_id}' was not found")
        return updated