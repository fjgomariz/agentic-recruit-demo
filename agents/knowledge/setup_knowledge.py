"""Create the Foundry IQ knowledge sources and knowledge base for the recruiter copilot.

Idempotent: every object is created or updated, so running it again after a deployment is safe.
It then waits for the indexers and sends one retrieval that needs both sources, to prove the whole
pipeline works (private storage read through the shared private link, embeddings, query planning).

Required environment variables:
- AZURE_SEARCH_ENDPOINT: https://<service>.search.windows.net
- AZURE_STORAGE_ACCOUNT_ID: resource ID of the private storage account
- AZURE_AI_ACCOUNT_NAME: Foundry account that hosts the embedding and planning models
- AZURE_AI_EMBEDDING_DEPLOYMENT_NAME (default text-embedding-3-large)
- AZURE_AI_MODEL_DEPLOYMENT_NAME: model that plans the queries (for example gpt-5.4-mini)

The caller needs Search Service Contributor and Search Index Data Contributor on the Search service.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from azure.identity import DefaultAzureCredential

API_VERSION = "2026-08-01-preview"
KNOWLEDGE_BASE = "recruiting-iq"
TALENT_POOL_SOURCE = "talent-pool-ks"
POLICIES_SOURCE = "hiring-policies-ks"
MANIFEST = Path(__file__).resolve().parents[2] / "samples" / "seed-manifest.json"
SYNC_TIMEOUT_SECONDS = 900
SMOKE_QUESTION = (
    "Which candidates in our talent pool could fill a Senior Product Designer role in London, "
    "and is each one's salary expectation inside our band for that level?"
)

RETRIEVAL_INSTRUCTIONS = (
    "Use the talent pool for questions about candidates: skills, experience, languages, availability and salary "
    "expectations. Use the hiring policies for questions about compensation bands and levels, remote and hybrid work, "
    "the interview process, language requirements, inclusive language and data retention. When a question combines "
    "candidates with policy, query both sources and keep the answer grounded in the documents."
)


class Search:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.credential = DefaultAzureCredential()
        self.session = requests.Session()

    def request(self, method: str, path: str, body: dict[str, Any] | None = None, retries: int = 12) -> Any:
        url = f"{self.endpoint}{path}{'&' if '?' in path else '?'}api-version={API_VERSION}"
        for attempt in range(1, retries + 1):
            token = self.credential.get_token("https://search.azure.com/.default").token
            response = self.session.request(
                method, url, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=120,
            )
            # Roles created by the same deployment can take minutes to apply.
            if response.status_code in (401, 403) and attempt < retries:
                print(f"Waiting for Search access to apply ({attempt}/{retries})", flush=True)
                time.sleep(20)
                continue
            if response.status_code >= 400:
                raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:1500]}")
            return response.json() if response.content else None
        raise AssertionError("unreachable")


def blob_source(name: str, description: str, container: str, config: dict[str, str]) -> dict[str, Any]:
    return {
        "name": name,
        "kind": "azureBlob",
        "description": description,
        "azureBlobParameters": {
            "connectionString": f"ResourceId={config['storage_id']}",
            "containerName": container,
            "isADLSGen2": False,
            "ingestionParameters": {
                # The storage account is private only, so indexing must run in the private environment
                # and read through the approved shared private link.
                "networkAccessMode": "private",
                "disableImageVerbalization": True,
                "contentExtractionMode": "minimal",
                "embeddingModel": {
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters": {
                        "resourceUri": config["openai_endpoint"],
                        "deploymentId": config["embedding"],
                        "modelName": config["embedding"],
                    },
                },
            },
        },
    }


def wait_for_sync(search: Search, source: str, expected: int) -> None:
    deadline = time.time() + SYNC_TIMEOUT_SECONDS
    while time.time() < deadline:
        status = search.request("GET", f"/knowledgesources/{source}/status")
        last = status.get("lastSynchronizationState")
        if last and last.get("endTime") and not status.get("currentSynchronizationState"):
            failed = last.get("itemsUpdatesFailed", 0)
            processed = last.get("itemsUpdatesProcessed", 0)
            if failed:
                raise RuntimeError(f"{source}: {failed} items failed: {json.dumps(last.get('errors'))[:1500]}")
            if processed >= expected:
                print(f"{source}: indexed {processed}/{expected} documents", flush=True)
                return
        time.sleep(10)
    raise TimeoutError(f"{source} did not finish indexing {expected} documents in {SYNC_TIMEOUT_SECONDS} seconds")


def smoke_test(search: Search) -> None:
    result = search.request(
        "POST",
        f"/knowledgebases/{KNOWLEDGE_BASE}/retrieve",
        {
            "messages": [{"role": "user", "content": [{"type": "text", "text": SMOKE_QUESTION}]}],
            "includeActivity": True,
        },
    )
    references = result.get("references") or []
    activity = result.get("activity") or []
    print(f"Smoke test: {len(references)} references, {len(activity)} activity records")
    for record in activity:
        arguments = (record.get("azureBlobArguments") or {}).get("search", "")
        source = record.get("knowledgeSourceName", "")
        print(f"  - {record.get('type')} {source}: {arguments}".rstrip(": "))
    if not references:
        raise RuntimeError("The knowledge base returned no references")


def main() -> int:
    account = os.environ["AZURE_AI_ACCOUNT_NAME"]
    config = {
        "storage_id": os.environ["AZURE_STORAGE_ACCOUNT_ID"],
        "openai_endpoint": f"https://{account}.openai.azure.com",
        "embedding": os.getenv("AZURE_AI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large"),
        "planner": os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
    }
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    search = Search(os.environ["AZURE_SEARCH_ENDPOINT"])

    search.request("PUT", f"/knowledgesources/{TALENT_POOL_SOURCE}", blob_source(
        TALENT_POOL_SOURCE,
        "Resumes of candidates who applied to Northstar before: skills, experience, languages, availability, "
        "notice period and salary expectation. Use it to find and compare people.",
        "talent-pool", config,
    ))
    search.request("PUT", f"/knowledgesources/{POLICIES_SOURCE}", blob_source(
        POLICIES_SOURCE,
        "Northstar hiring policies: compensation bands by level, remote and hybrid work, interview process, "
        "language requirements, inclusive language style guide and data retention and consent rules.",
        "hiring-policies", config,
    ))
    print("Knowledge sources created or updated", flush=True)

    search.request("PUT", f"/knowledgebases/{KNOWLEDGE_BASE}", {
        "name": KNOWLEDGE_BASE,
        "description": "Talent pool and hiring policies for the Northstar recruiter copilot.",
        "retrievalInstructions": RETRIEVAL_INSTRUCTIONS,
        "outputMode": "extractiveData",
        "knowledgeSources": [{"name": TALENT_POOL_SOURCE}, {"name": POLICIES_SOURCE}],
        "models": [{
            "kind": "azureOpenAI",
            "azureOpenAIParameters": {
                "resourceUri": config["openai_endpoint"],
                "deploymentId": config["planner"],
                "modelName": config["planner"],
            },
        }],
        "retrievalReasoningEffort": {"kind": "low"},
    })
    print(f"Knowledge base {KNOWLEDGE_BASE} created or updated", flush=True)

    wait_for_sync(search, TALENT_POOL_SOURCE, len(manifest["talent-pool"]))
    wait_for_sync(search, POLICIES_SOURCE, len(manifest["hiring-policies"]))
    smoke_test(search)
    return 0


if __name__ == "__main__":
    sys.exit(main())
