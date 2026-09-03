"""Translate application errors into HTTP responses."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import HTTPException, status

from app.services import EntityAlreadyExistsError, EntityNotFoundError

Result = TypeVar("Result")


async def execute(operation: Callable[[], Awaitable[Result]]) -> Result:
    """Execute a service operation and map expected errors to HTTP semantics."""

    try:
        return await operation()
    except EntityNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except EntityAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error