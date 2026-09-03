"""Response models not represented by the recruitment domain."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """API liveness response."""

    status: Literal["healthy"] = "healthy"
    service: str = "recruitment-foundry-api"