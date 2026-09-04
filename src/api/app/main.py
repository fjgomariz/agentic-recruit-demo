"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.dependencies.services import close_job_service, initialize_job_service

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize and release application-scoped persistence resources."""

    await initialize_job_service()
    try:
        yield
    finally:
        await close_job_service()

app = FastAPI(
    title="Recruitment Foundry Demo API",
    description="Backend API for the Recruitment Foundry Demo.",
    version="0.1.0",
    contact={"name": "Recruitment Foundry Demo"},
    lifespan=lifespan,
)
app.include_router(api_router)