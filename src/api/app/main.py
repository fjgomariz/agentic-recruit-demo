"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(
    title="Recruitment Foundry Demo API",
    description="In-memory backend foundation for the Recruitment Foundry Demo.",
    version="0.1.0",
    contact={"name": "Recruitment Foundry Demo"},
)
app.include_router(api_router)