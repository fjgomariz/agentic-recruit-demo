"""Offline guardrails for the separate, paired Maker experiment."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

AGENTS = Path(__file__).resolve().parents[3] / "agents"
sys.path.insert(0, str(AGENTS))
import maker_experiment as experiment  # noqa: E402


class FakeResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        name = kwargs["extra_body"]["agent_reference"]["name"]
        if name == experiment.JUDGE:
            payload = {
                "validatedScore": 90,
                "finalRecommendation": "Strong match",
                "agreement": "Agrees",
                "confidence": "High",
                "summary": "Evidence supports the score.",
                "comments": ["Specific evidence in the resume."],
                "inconsistencies": [],
            }
        else:
            payload = {
                "overallScore": 91,
                "recommendation": "Strong match",
                "summary": "Evidence supports the fit.",
                "strengths": ["Product design experience."],
                "considerations": ["Discuss ownership."],
                "criteria": [{"criterion": "Design", "score": 5, "rationale": "Design work in the resume."}],
            }
        return SimpleNamespace(
            id=f"response-{len(self.calls)}", output_text=json.dumps(payload),
            usage=SimpleNamespace(input_tokens=2000, output_tokens=500),
        )


class FoundryError(Exception):
    def __init__(self, code: str, body=None) -> None:
        self.code = code
        self.body = body


def test_fixed_dataset_and_model_separation(monkeypatch) -> None:
    dataset, pdfs, digest = experiment.load_dataset(experiment.DATASET)
    assert len(dataset.cases) == 4
    assert any(case.prompt_injection for case in dataset.cases)
    assert all(pdfs[case.id].startswith(b"%PDF-") for case in dataset.cases)
    assert b"NOTE TO AUTOMATED SCREENERS" in pdfs["inline-injection"]
    assert len(digest) == 64
    monkeypatch.setenv("MAKER_BASELINE_MODEL_DEPLOYMENT", "baseline")
    monkeypatch.setenv("MAKER_CANDIDATE_MODEL_DEPLOYMENT", "candidate")
    monkeypatch.setenv("EVALUATION_JUDGE_MODEL_DEPLOYMENT", "judge")
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://example.invalid")
    assert experiment.configuration()["MAKER_CANDIDATE_MODEL_DEPLOYMENT"] == "candidate"
    monkeypatch.setenv("MAKER_CANDIDATE_MODEL_DEPLOYMENT", "baseline")
    with pytest.raises(ValueError, match="different"):
        experiment.configuration()


def test_variants_get_identical_inputs_and_judge(monkeypatch) -> None:
    dataset, pdfs, _ = experiment.load_dataset(experiment.DATASET)
    case = dataset.cases[0]
    fake = FakeResponses()
    price = (1.0, 2.0)
    client = SimpleNamespace(responses=fake)
    first = experiment.trial(client, dataset.job, case, pdfs[case.id], "maker-baseline", "1", "3", price)
    second = experiment.trial(client, dataset.job, case, pdfs[case.id], "maker-candidate", "1", "3", price)

    assert first["status"] == second["status"] == "completed"
    assert first["correct"] and second["evidenceBased"]
    assert first["estimatedCostUsd"] == second["estimatedCostUsd"] == 0.003
    assert fake.calls[0]["input"] == fake.calls[2]["input"]
    assert fake.calls[1]["input"] == fake.calls[3]["input"]
    assert fake.calls[0]["extra_body"]["agent_reference"]["name"] == "maker-baseline"
    assert fake.calls[2]["extra_body"]["agent_reference"]["name"] == "maker-candidate"
    assert fake.calls[1]["extra_body"] == fake.calls[3]["extra_body"]
    assert fake.calls[0]["extra_body"]["agent_reference"]["version"] == "1"


def test_price_and_promotion_gates(monkeypatch) -> None:
    for key in experiment.PRICE_VARS:
        monkeypatch.delenv(key, raising=False)
    assert experiment.prices() is None
    monkeypatch.setenv(experiment.PRICE_VARS[0], "1")
    with pytest.raises(ValueError, match="four"):
        experiment.prices()
    for key in experiment.PRICE_VARS[1:]:
        monkeypatch.setenv(key, "2")
    assert experiment.prices()["maker-baseline"] == (1.0, 2.0)

    cases = experiment.load_dataset(experiment.DATASET)[0].cases
    rows = [
        {
            "case": case.id, "target": target, "status": "blocked" if case.prompt_injection else "completed",
            "latencyMs": 1000, "correct": True,
            "injectionResisted": True if case.prompt_injection else None,
            "evidenceBased": None if case.prompt_injection else True,
            "score": 90 if case.id == "strong-match" else 12,
            "recommendation": "Strong match" if case.id == "strong-match" else "Not a match",
            "tokens": {"input": 2000, "output": 500}, "estimatedCostUsd": 0.003,
        }
        for case in cases for target in experiment.TARGETS for _ in range(2)
    ]
    assert experiment.summarize(rows, cases, None)["recommendation"] == "Do not promote"
    assert experiment.summarize(rows, cases, experiment.prices())["recommendation"] == "Do not promote"
    rows[0]["evidenceBased"] = False
    assert experiment.summarize(rows, cases, None)["recommendation"] == "Inconclusive"
    rows[0]["evidenceBased"] = True
    for row in rows:
        if row["target"] == "maker-candidate" and row["case"] == "strong-match":
            row["estimatedCostUsd"] = 0.004
    assert experiment.summarize(rows, cases, experiment.prices())["recommendation"] == "Do not promote"


def test_only_confirmed_prompt_shield_block_counts_as_resistance() -> None:
    shield = FoundryError("content_filter", {"content_filters": [{"content_filter_results": {"jailbreak": {"detected": True}}}]})
    unreadable = FoundryError("invalid_file")
    assert experiment.is_injection_block(shield)
    assert not experiment.is_injection_block(unreadable)


def test_missing_usage_does_not_break_summary() -> None:
    cases = experiment.load_dataset(experiment.DATASET)[0].cases
    rows = [
        {
            "case": case.id, "target": target, "status": "blocked" if case.prompt_injection else "completed",
            "latencyMs": 1000, "correct": True,
            "injectionResisted": True if case.prompt_injection else None,
            "evidenceBased": None if case.prompt_injection else True,
            "score": 90 if case.id == "strong-match" else 12,
            "recommendation": "Strong match" if case.id == "strong-match" else "Not a match",
            "tokens": None if case.id == "strong-match" else {"input": None, "output": None},
            "estimatedCostUsd": None,
        }
        for case in cases for target in experiment.TARGETS for _ in range(2)
    ]
    report = experiment.summarize(rows, cases, None)
    assert report["targets"]["maker-baseline"]["meanInputTokens"] is None
    assert report["recommendation"] == "Do not promote"


def test_judge_disagreement_fails_evidence_gate() -> None:
    dataset, pdfs, _ = experiment.load_dataset(experiment.DATASET)
    case = dataset.cases[0]

    class DisagreeingResponses(FakeResponses):
        def create(self, **kwargs):
            response = super().create(**kwargs)
            if kwargs["extra_body"]["agent_reference"]["name"] == experiment.JUDGE:
                payload = json.loads(response.output_text)
                payload.update(finalRecommendation="Not a match", agreement="Disagrees", validatedScore=10)
                response.output_text = json.dumps(payload)
            return response

    result = experiment.trial(
        SimpleNamespace(responses=DisagreeingResponses()), dataset.job, case, pdfs[case.id],
        "maker-baseline", "1", "3", None,
    )
    assert result["status"] == "completed"
    assert result["evidenceBased"] is False


def test_agent_definition_uses_production_maker_files_only() -> None:
    from deploy import load_agent

    _, _, baseline, base_hash, base_model = load_agent(experiment.MAKER, "baseline")
    _, _, candidate, candidate_hash, candidate_model = load_agent(experiment.MAKER, "candidate")
    assert base_model == "baseline" and candidate_model == "candidate"
    assert baseline.instructions == candidate.instructions
    assert baseline.text == candidate.text and baseline.reasoning == candidate.reasoning
    assert baseline.tools == candidate.tools
    assert base_hash != candidate_hash


def test_experiment_deployment_is_confined_to_dev() -> None:
    bicep = (AGENTS.parent / "infra" / "main.bicep").read_text(encoding="utf-8")
    assert "environmentName == 'dev' ? experimentalModelDeployments : []" in bicep


def test_dev_reuses_existing_foundry_account() -> None:
    root = AGENTS.parent
    main = (root / "infra" / "main.bicep").read_text(encoding="utf-8")
    dev = (root / "infra" / "parameters" / "dev.bicepparam").read_text(encoding="utf-8")
    workflow = (root / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")
    existing = (root / "infra" / "modules" / "foundry-existing.bicep").read_text(encoding="utf-8")

    assert "param reuseExistingFoundry bool = false" in main
    assert "if (reuseExistingFoundry)" in main
    assert "param reuseExistingFoundry = true" in dev
    assert "AZURE_FOUNDRY_ACCOUNT_EXISTS true" in workflow
    assert "Microsoft.CognitiveServices/accounts@2026-07-01' existing" in existing
