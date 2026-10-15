"""Read the documents Foundry IQ indexes: the talent pool resumes and the hiring policies."""

import logging
import re

from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

from app.config import KnowledgeSettings, StorageSettings

logger = logging.getLogger(__name__)

SAFE_FILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MEDIA_TYPES = {".pdf": "application/pdf", ".md": "text/plain; charset=utf-8"}


class KnowledgeDocumentNotFoundError(LookupError):
    """The container is not a knowledge source, the name is not a plain file name, or the blob does not exist."""


class KnowledgeDocumentStore:
    """Read-only access to the two knowledge source containers with the API's managed identity."""

    def __init__(self, storage: StorageSettings, knowledge: KnowledgeSettings) -> None:
        if not storage.blob_endpoint:
            raise ValueError("AZURE_STORAGE_BLOB_ENDPOINT must be configured")
        self._containers = {knowledge.talent_pool_container_name, knowledge.hiring_policies_container_name}
        self._credential = DefaultAzureCredential()
        self._service = BlobServiceClient(storage.blob_endpoint, credential=self._credential)

    async def download(self, container: str, file_name: str) -> tuple[bytes, str]:
        """Return the file and its media type. Only plain file names in the knowledge containers are served."""

        extension = file_name[file_name.rfind("."):].lower() if "." in file_name else ""
        if container not in self._containers or not SAFE_FILE_NAME.match(file_name) or extension not in MEDIA_TYPES:
            raise KnowledgeDocumentNotFoundError(f"Document '{container}/{file_name}' was not found")
        try:
            stream = await self._service.get_container_client(container).download_blob(file_name)
            return await stream.readall(), MEDIA_TYPES[extension]
        except ResourceNotFoundError as error:
            raise KnowledgeDocumentNotFoundError(f"Document '{container}/{file_name}' was not found") from error

    async def close(self) -> None:
        await self._service.close()
        await self._credential.close()
