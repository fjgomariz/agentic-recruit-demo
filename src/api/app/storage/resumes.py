"""Store candidate resumes in a private Azure Blob Storage container."""

import logging
from typing import Protocol

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient

from app.config import StorageSettings

logger = logging.getLogger(__name__)


class ResumeStore(Protocol):
    """Minimal resume file operations used by the application service."""

    container_name: str

    async def upload(self, blob_name: str, data: bytes) -> None: ...

    async def download(self, blob_name: str) -> bytes: ...

    async def delete(self, blob_name: str) -> None: ...


class BlobResumeStore:
    """Read and write PDF resumes with the API's managed identity."""

    def __init__(self, settings: StorageSettings) -> None:
        if not settings.blob_endpoint:
            raise ValueError("AZURE_STORAGE_BLOB_ENDPOINT must be configured")
        self.container_name = settings.resumes_container_name
        self._credential = DefaultAzureCredential()
        self._service = BlobServiceClient(settings.blob_endpoint, credential=self._credential)
        self._container = self._service.get_container_client(self.container_name)

    async def upload(self, blob_name: str, data: bytes) -> None:
        await self._container.upload_blob(
            name=blob_name,
            data=data,
            overwrite=False,
            content_settings=ContentSettings(content_type="application/pdf"),
        )
        logger.info("Uploaded resume blob=%s/%s bytes=%s", self.container_name, blob_name, len(data))

    async def download(self, blob_name: str) -> bytes:
        stream = await self._container.download_blob(blob_name)
        return await stream.readall()

    async def delete(self, blob_name: str) -> None:
        await self._container.delete_blob(blob_name)

    async def close(self) -> None:
        await self._service.close()
        await self._credential.close()
