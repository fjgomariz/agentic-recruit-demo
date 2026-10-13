"""Seed the Foundry IQ knowledge source containers from the public repository.

Runs as a manual Container Apps job inside the environment's virtual network, because the storage
account is reachable only through its private endpoint. It downloads ``seed-manifest.json`` and the
files it lists from a pinned commit of the repository, then uploads them with the job's managed
identity. Re-running is safe: blobs are overwritten.

Environment variables:
- SEED_SOURCE_BASE_URL: https://raw.githubusercontent.com/<owner>/<repo>/<commit>/samples
- AZURE_STORAGE_BLOB_ENDPOINT: blob endpoint of the storage account
- AZURE_CLIENT_ID: client ID of the user-assigned managed identity with Storage Blob Data Contributor
"""

import json
import os
import re
import sys
import time
import urllib.request

from azure.core.exceptions import HttpResponseError
from azure.identity import ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

ALLOWED_HOST_PREFIX = "https://raw.githubusercontent.com/"
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CONTENT_TYPES = {".pdf": "application/pdf", ".md": "text/markdown", ".txt": "text/plain"}
UPLOAD_ATTEMPTS = 20
UPLOAD_WAIT_SECONDS = 15


def validate_manifest(manifest: dict) -> dict[str, list[str]]:
    """Accept only {container: [file, ...]} with plain file names, so nothing escapes the source folder."""
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("The manifest must map container names to file lists")
    for container, files in manifest.items():
        if not SAFE_NAME.match(container) or not isinstance(files, list) or not files:
            raise ValueError(f"Invalid manifest entry for {container!r}")
        for name in files:
            if not isinstance(name, str) or not SAFE_NAME.match(name):
                raise ValueError(f"Unsafe file name {name!r} in {container}")
    return manifest


def fetch(url: str, attempts: int = 4) -> bytes:
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read()
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def upload(container_client, name: str, data: bytes) -> None:
    extension = os.path.splitext(name)[1].lower()
    settings = ContentSettings(content_type=CONTENT_TYPES.get(extension, "application/octet-stream"))
    for attempt in range(1, UPLOAD_ATTEMPTS + 1):
        try:
            container_client.upload_blob(name, data, overwrite=True, content_settings=settings)
            return
        except HttpResponseError as error:
            # Role assignments created by the same deployment can take minutes to apply.
            if error.status_code != 403 or attempt == UPLOAD_ATTEMPTS:
                raise
            print(f"Waiting for the storage role to apply ({attempt}/{UPLOAD_ATTEMPTS})", flush=True)
            time.sleep(UPLOAD_WAIT_SECONDS)


def main() -> int:
    base_url = os.environ["SEED_SOURCE_BASE_URL"].rstrip("/")
    if not base_url.startswith(ALLOWED_HOST_PREFIX):
        print(f"SEED_SOURCE_BASE_URL must start with {ALLOWED_HOST_PREFIX}", file=sys.stderr)
        return 2

    manifest = validate_manifest(json.loads(fetch(f"{base_url}/seed-manifest.json")))
    credential = ManagedIdentityCredential(client_id=os.environ["AZURE_CLIENT_ID"])
    service = BlobServiceClient(os.environ["AZURE_STORAGE_BLOB_ENDPOINT"], credential=credential)

    uploaded = 0
    for container, files in manifest.items():
        container_client = service.get_container_client(container)
        for name in files:
            upload(container_client, name, fetch(f"{base_url}/{container}/{name}"))
            uploaded += 1
        print(f"{container}: {len(files)} files", flush=True)
    print(f"Seeded {uploaded} files", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
