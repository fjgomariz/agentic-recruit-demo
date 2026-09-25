"""Startup behavior when Cosmos DB is not reachable yet."""

import pytest
from fastapi.testclient import TestClient

from app.dependencies import services
from app.main import app


def test_api_stays_healthy_while_cosmos_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable(_: object) -> None:
        raise ConnectionError("Cosmos DB unreachable")

    monkeypatch.setenv("AZURE_COSMOS_ENDPOINT", "https://example.documents.azure.com:443/")
    monkeypatch.setattr(services, "_connect_job_service", unavailable)
    monkeypatch.setattr(services, "COSMOS_RETRY_SECONDS", 0.01)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/jobs").status_code == 503
        assert client.get("/candidates").status_code == 200


def test_startup_fails_fast_without_cosmos_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZURE_COSMOS_ENDPOINT", raising=False)

    with pytest.raises(RuntimeError, match="AZURE_COSMOS_ENDPOINT"):
        with TestClient(app):
            pass
