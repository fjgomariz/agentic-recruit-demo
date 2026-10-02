"""FastAPI application entry point."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.dependencies.agents import close_agent_services, initialize_agent_services
from app.dependencies.services import close_job_service, initialize_job_service

logging.basicConfig(level=logging.INFO)
# The Azure SDK logs every HTTP request and header at INFO, which floods Log Analytics.
logging.getLogger("azure").setLevel(logging.WARNING)


def configure_telemetry() -> None:
    """Send requests, dependencies, logs, and agent call spans to Application Insights when configured."""

    if not os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        return
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(logger_name="app")
    try:
        from azure.ai.projects.telemetry import AIProjectInstrumentor

        AIProjectInstrumentor().instrument()
    except Exception:
        logging.getLogger(__name__).exception("Foundry client tracing could not be enabled")


configure_telemetry()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize and release application-scoped persistence and agent resources."""

    await initialize_job_service()
    await initialize_agent_services()
    try:
        yield
    finally:
        await close_agent_services()
        await close_job_service()

app = FastAPI(
    title="Recruitment Foundry Demo API",
    description="Backend API for the Recruitment Foundry Demo.",
    version="0.1.0",
    contact={"name": "Recruitment Foundry Demo"},
    lifespan=lifespan,
)
app.include_router(api_router)