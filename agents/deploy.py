"""Publish the prompt agents in this folder to the Foundry project.

Each subfolder with an ``agent.json`` is one agent. A new agent version is created only when
the definition (model, instructions, output schema, reasoning) changes, so redeploying the same
commit is a no-op. An agent can choose its model deployment with ``"modelDeployment"`` in
``agent.json``; otherwise it uses the default. Required environment variables:

- ``AZURE_AI_PROJECT_ENDPOINT``: Foundry project endpoint.
- ``AZURE_AI_MODEL_DEPLOYMENT_NAME``: default model deployment.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MCPTool,
    PromptAgentDefinition,
    PromptAgentDefinitionTextOptions,
    Reasoning,
    TextResponseFormatJsonSchema,
)
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential

AGENTS_DIRECTORY = Path(__file__).resolve().parent
HASH_METADATA_KEY = "definition_sha256"
PERMISSION_RETRY_SECONDS = 15
PERMISSION_RETRY_ATTEMPTS = 24


class KnowledgeBaseNotConfigured(Exception):
    """The agent needs a Foundry IQ knowledge base but the environment has no Azure AI Search endpoint."""


def knowledge_base_tool(config: dict[str, Any]) -> MCPTool:
    """Connect the agent to a Foundry IQ knowledge base through the project connection named in agent.json."""

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    if not endpoint:
        raise KnowledgeBaseNotConfigured("AZURE_SEARCH_ENDPOINT is not set")
    api_version = config.get("apiVersion", "2026-08-01-preview")
    return MCPTool(
        server_label="knowledge-base",
        server_url=f"{endpoint}/knowledgebases/{config['name']}/mcp?api-version={api_version}",
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=config["connection"],
    )


def load_agent(folder: Path, default_model: str) -> tuple[str, str, PromptAgentDefinition, str, str]:
    """Build an agent definition and a stable hash of everything that defines its behavior.

    "outputSchemaFile" is optional (agents that answer in free text omit it) and "knowledgeBase"
    ({"name", "connection"}) adds the Foundry IQ retrieval tool.
    """

    config = json.loads((folder / "agent.json").read_text(encoding="utf-8"))
    model = config.get("modelDeployment") or default_model
    instructions = (folder / config["instructionsFile"]).read_text(encoding="utf-8").strip()
    schema = json.loads((folder / config["outputSchemaFile"]).read_text(encoding="utf-8")) if "outputSchemaFile" in config else None
    effort = config.get("reasoningEffort")
    knowledge_base = knowledge_base_tool(config["knowledgeBase"]) if "knowledgeBase" in config else None

    definition = PromptAgentDefinition(
        model=model,
        instructions=instructions,
        text=PromptAgentDefinitionTextOptions(
            format=TextResponseFormatJsonSchema(name=config["outputSchemaName"], schema=schema, strict=True)
        ) if schema is not None else None,
        tools=[knowledge_base] if knowledge_base else None,
        reasoning=Reasoning(effort=effort) if effort else None,
    )
    fingerprint_data: dict[str, Any] = {"model": model, "instructions": instructions, "schema": schema, "effort": effort}
    if knowledge_base:
        # Only agents with a knowledge base carry this key, so the hashes of the other agents do not change.
        fingerprint_data["knowledgeBase"] = {"url": knowledge_base.server_url, "connection": knowledge_base.project_connection_id}
    fingerprint = json.dumps(fingerprint_data, sort_keys=True)
    return config["name"], config["description"], definition, hashlib.sha256(fingerprint.encode()).hexdigest(), model


def latest_hash(client: AIProjectClient, name: str) -> str | None:
    try:
        agent = client.agents.get(agent_name=name)
    except ResourceNotFoundError:
        return None
    return (agent.versions.latest.metadata or {}).get(HASH_METADATA_KEY)


def publish(client: AIProjectClient, folder: Path, default_model: str) -> None:
    name, description, definition, definition_hash, model = load_agent(folder, default_model)
    if latest_hash(client, name) == definition_hash:
        print(f"{name}: unchanged, keeping the latest version")
        return

    metadata: dict[str, Any] = {HASH_METADATA_KEY: definition_hash}
    if commit := os.getenv("GITHUB_SHA"):
        metadata["source_commit"] = commit
    version = client.agents.create_version(
        agent_name=name,
        definition=definition,
        description=description,
        metadata=metadata,
    )
    print(f"{name}: published version {version.version} using model deployment '{model}'")


def is_permission_error(error: Exception) -> bool:
    if isinstance(error, ClientAuthenticationError):
        return True
    return isinstance(error, HttpResponseError) and error.status_code in (401, 403)


def main() -> int:
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]
    folders = sorted(path.parent for path in AGENTS_DIRECTORY.glob("*/agent.json"))
    if not folders:
        print("No agents found")
        return 1

    with DefaultAzureCredential() as credential, AIProjectClient(endpoint=endpoint, credential=credential) as client:
        for folder in folders:
            # Role assignments created by the same deployment can take a few minutes to apply.
            for attempt in range(1, PERMISSION_RETRY_ATTEMPTS + 1):
                try:
                    publish(client, folder, model)
                    break
                except KnowledgeBaseNotConfigured as error:
                    print(f"{folder.name}: skipped, no knowledge base here ({error})")
                    break
                except Exception as error:
                    if not is_permission_error(error) or attempt == PERMISSION_RETRY_ATTEMPTS:
                        raise
                    print(f"{folder.name}: waiting for Foundry permissions ({attempt}/{PERMISSION_RETRY_ATTEMPTS})")
                    time.sleep(PERMISSION_RETRY_SECONDS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
