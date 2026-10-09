"""Offline guardrails for the Foundry candidate-evaluator evaluation and the dev infrastructure it relies on."""

import sys
from pathlib import Path

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


def test_dev_reuses_existing_foundry_account() -> None:
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    dev = (ROOT / "infra" / "parameters" / "dev.bicepparam").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")
    existing = (ROOT / "infra" / "modules" / "foundry-existing.bicep").read_text(encoding="utf-8")

    assert "param reuseExistingFoundry bool = false" in main
    assert "if (reuseExistingFoundry)" in main
    assert "param reuseExistingFoundry = true" in dev
    assert "AZURE_FOUNDRY_ACCOUNT_EXISTS true" in workflow
    assert "Microsoft.CognitiveServices/accounts@2026-07-01' existing" in existing
