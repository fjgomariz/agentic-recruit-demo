"""Offline guardrails for the Foundry candidate-evaluator evaluation and the dev infrastructure it relies on."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "agents" / "evaluations"))
import run_evaluation as evaluation  # noqa: E402


def test_items_use_the_production_prompt_with_resume_text() -> None:
    items = evaluation.build_items()
    assert len(items) >= 4
    assert {item["case"] for item in items} >= {"strong-match", "weak-match", "inline-injection"}
    for item in items:
        assert item["query"].startswith("Job posting")
        assert "resume text follows (untrusted)" in item["query"]
        assert "attached as a PDF" not in item["query"]
        assert item["expected_recommendation"] in {"Strong match", "Possible match", "Not a match"}
    maya = next(item for item in items if item["case"] == "strong-match")
    assert "Maya Rodriguez" in maya["query"]


def test_criteria_cover_accuracy_evidence_and_injection() -> None:
    criteria = evaluation.testing_criteria("judge-model")
    assert [item["name"] for item in criteria] == [
        "recommendation_matches", "evidence_based", "ignores_embedded_instructions",
    ]
    assert criteria[0]["type"] == "string_check"
    assert "%" not in criteria[0]["reference"]
    assert all(item["model"] == "judge-model" for item in criteria[1:])


def test_lab_agent_never_targets_production_agent() -> None:
    assert evaluation.LAB_AGENT == "candidate-evaluator-lab"
    assert evaluation.LAB_AGENT != "candidate-evaluator"


def test_experiment_deployment_is_confined_to_dev() -> None:
    bicep = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    assert "environmentName == 'dev' ? experimentalModelDeployments : []" in bicep


def test_knowledge_search_is_entra_only_dev_only_and_reads_storage_privately() -> None:
    infra = ROOT / "infra"
    main = (infra / "main.bicep").read_text(encoding="utf-8")
    search = (infra / "modules" / "search.bicep").read_text(encoding="utf-8")
    script = (infra / "scripts" / "approve-search-private-link.sh").read_bytes()

    assert "var deployKnowledge = environmentName == 'dev'" in main
    assert "param searchLocation string" in main
    assert "location: searchLocation" in main
    assert "environmentName == 'dev' ? knowledgeModelDeployments : []" in main
    assert "disableLocalAuth: true" in search
    assert "publicNetworkAccess: 'enabled'" in search
    assert "groupId: 'blob'" in search
    assert b"\r" not in script
    assert b"description=='${REQUEST_MESSAGE}'" in script


def test_search_roles_are_scoped_to_the_services_that_need_them() -> None:
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    assert "roleDefinitionId: cognitiveServicesUserRoleId" in main
    assert "roleDefinitionId: searchIndexDataReaderRoleId" in main
    assert "storage-blob-reader.bicep" in main


def _load_seed_script():
    spec = importlib.util.spec_from_file_location("seed_knowledge", ROOT / "infra" / "scripts" / "seed-knowledge.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_manifest_lists_existing_files_and_rejects_unsafe_names() -> None:
    seed = _load_seed_script()
    manifest = json.loads((ROOT / "samples" / "seed-manifest.json").read_text(encoding="utf-8"))

    assert set(seed.validate_manifest(manifest)) == {"talent-pool", "hiring-policies"}
    for container, files in manifest.items():
        for name in files:
            assert (ROOT / "samples" / container / name).is_file()
    for bad in ({"talent-pool": ["../secrets.pdf"]}, {"talent-pool": ["a/b.pdf"]}, {"../x": ["a.pdf"]}, {}, {"talent-pool": []}):
        with pytest.raises(ValueError):
            seed.validate_manifest(bad)


def test_seed_job_copies_from_a_pinned_public_source_with_managed_identity() -> None:
    script = (ROOT / "infra" / "scripts" / "seed-knowledge.py").read_text(encoding="utf-8")
    bicep = (ROOT / "infra" / "modules" / "seed-job.bicep").read_text(encoding="utf-8")
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")

    assert 'ALLOWED_HOST_PREFIX = "https://raw.githubusercontent.com/"' in script
    assert "ManagedIdentityCredential" in script and "overwrite=True" in script
    assert "loadTextContent('../scripts/seed-knowledge.py')" in bicep
    assert "triggerType: 'Manual'" in bicep
    assert "var deploySeedJob = deployKnowledge && deployApps && !empty(seedSourceBaseUrl)" in main
    assert "${GITHUB_REPOSITORY}/${GITHUB_SHA}/samples" in workflow

def test_knowledge_sources_index_the_private_storage_with_identity_only() -> None:
    spec = importlib.util.spec_from_file_location("setup_knowledge", ROOT / "agents" / "knowledge" / "setup_knowledge.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = {"storage_id": "/subscriptions/s/resourceGroups/r/providers/Microsoft.Storage/storageAccounts/a",
              "openai_endpoint": "https://acct.openai.azure.com", "embedding": "emb", "planner": "plan"}

    source = module.blob_source("ks", "description", "talent-pool", config)
    parameters = source["azureBlobParameters"]
    assert parameters["connectionString"].startswith("ResourceId=")
    assert "AccountKey" not in parameters["connectionString"] and "SharedAccessSignature" not in parameters["connectionString"]
    assert parameters["ingestionParameters"]["networkAccessMode"] == "private"
    assert parameters["ingestionParameters"]["embeddingModel"]["azureOpenAIParameters"]["deploymentId"] == "emb"
    assert {"talent-pool-ks", "hiring-policies-ks"} == {module.TALENT_POOL_SOURCE, module.POLICIES_SOURCE}
    assert "talent pool" in module.RETRIEVAL_INSTRUCTIONS and "hiring policies" in module.RETRIEVAL_INSTRUCTIONS

    workflow = (ROOT / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")
    assert "python agents/knowledge/setup_knowledge.py" in workflow
    assert workflow.index("Seed the Foundry IQ knowledge sources") < workflow.index("Create the Foundry IQ knowledge base")


def test_recruiter_copilot_uses_the_knowledge_base_tool_and_skips_without_search(monkeypatch) -> None:
    import hashlib

    from deploy import KnowledgeBaseNotConfigured, load_agent

    folder = ROOT / "agents" / "recruiter-copilot"
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT", raising=False)
    with pytest.raises(KnowledgeBaseNotConfigured):
        load_agent(folder, "model")

    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://search.example.net/")
    name, _, definition, digest, _ = load_agent(folder, "model")
    tool = definition.tools[0]
    assert name == "recruiter-copilot" and definition.text is None
    assert tool.server_url == "https://search.example.net/knowledgebases/recruiting-iq/mcp?api-version=2026-08-01-preview"
    assert tool.project_connection_id == "kb-recruiting-iq" and tool.allowed_tools == ["knowledge_base_retrieve"]
    assert tool.require_approval == "never"
    # The agent must cite, ignore instructions inside documents and avoid protected characteristics.
    text = definition.instructions
    assert "Cite every claim" in text and "untrusted data" in text and "protected characteristics" in text

    # Agents without a knowledge base keep their original hash, so no new versions are published for them.
    folder = ROOT / "agents" / "candidate-evaluator"
    _, _, existing, existing_digest, _ = load_agent(folder, "model")
    config = json.loads((folder / "agent.json").read_text(encoding="utf-8"))
    schema = json.loads((folder / config["outputSchemaFile"]).read_text(encoding="utf-8"))
    legacy = json.dumps({"model": "model", "instructions": existing.instructions, "schema": schema,
                         "effort": config["reasoningEffort"]}, sort_keys=True)
    assert existing_digest == hashlib.sha256(legacy.encode()).hexdigest()
    assert digest != existing_digest


def test_knowledge_connection_is_deployed_for_dev_without_secrets() -> None:
    infra = ROOT / "infra"
    module = (infra / "modules" / "foundry-knowledge-connection.bicep").read_text(encoding="utf-8")
    main = (infra / "main.bicep").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")

    assert "authType: 'ProjectManagedIdentity'" in module and "category: 'RemoteTool'" in module
    assert "audience: 'https://search.azure.com/'" in module
    assert "credentials" not in module
    assert "knowledgeBaseConnection './modules/foundry-knowledge-connection.bicep' = if (deployKnowledge)" in main
    assert 'AZURE_SEARCH_ENDPOINT="$(azd env get-value AZURE_SEARCH_ENDPOINT)"' in workflow


def test_api_reads_the_knowledge_base_and_documents_with_its_own_identity() -> None:
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")

    # The retrieval plan is read with the API identity (Search Index Data Reader), never with keys.
    assert "module apiSearchAccess './modules/search-role.bicep' = if (deployKnowledge)" in main
    assert "principalId: apiIdentity.outputs.principalId\n    roleDefinitionId: searchIndexDataReaderRoleId" in main
    for variable in ("AZURE_SEARCH_ENDPOINT", "KNOWLEDGE_BASE_NAME", "RECRUITER_COPILOT_AGENT_NAME",
                     "AZURE_STORAGE_TALENT_POOL_CONTAINER_NAME", "AZURE_STORAGE_HIRING_POLICIES_CONTAINER_NAME"):
        assert f"name: '{variable}'" in main
    # Opening cited documents must not depend on the one-off seed job being deployed.
    assert "module apiTalentPoolAccess './modules/blob-container-access.bicep' = if (deployKnowledge)" in main
    assert "module apiHiringPoliciesAccess './modules/blob-container-access.bicep' = if (deployKnowledge)" in main


def test_dev_creates_the_foundry_account_unless_told_to_reuse_it() -> None:
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    dev = (ROOT / "infra" / "parameters" / "dev.bicepparam").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")
    existing = (ROOT / "infra" / "modules" / "foundry-existing.bicep").read_text(encoding="utf-8")

    assert "param reuseExistingFoundry bool = false" in main
    assert "if (reuseExistingFoundry)" in main
    assert "param reuseExistingFoundry = false" in dev
    assert "AZURE_FOUNDRY_ACCOUNT_EXISTS \"${AZURE_FOUNDRY_ACCOUNT_EXISTS:-false}\"" in workflow
    assert "Microsoft.CognitiveServices/accounts@2026-07-01' existing" in existing
