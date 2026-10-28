"""Offline guardrails for the recruiter-copilot retrieval evaluation: dataset, graders and criteria."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "agents" / "evaluations"))
sys.path.insert(0, str(ROOT / "agents" / "knowledge"))

import retrieval_graders as graders  # noqa: E402
import run_retrieval_evaluation as runner  # noqa: E402

BLOB = "https://storage.blob.core.windows.net"


def citation(text: str, marker: str, name: str, container: str = "talent-pool") -> dict:
    start = text.index(marker)
    return {"type": "url_citation", "start_index": start, "end_index": start + len(marker), "url": f"{BLOB}/{container}/{name}"}


def agent_item(text: str, annotations: list[dict], retrieved: list[str], **fields) -> dict:
    documents = [{"content": json.dumps({"blob_url": f"{BLOB}/talent-pool/{name}", "snippet": "..."})} for name in retrieved]
    return {
        **fields,
        "sample": {"output_items": [
            {"role": "system", "content": "instructions"},
            {"role": "assistant", "content": [{"type": "tool_call", "name": "knowledge_base_retrieve"}]},
            {"role": "tool", "content": [{"type": "tool_result", "tool_result": json.dumps({"documents": documents})}]},
            {"role": "assistant", "content": [{"type": "output_text", "text": text, "annotations": annotations}]},
        ]},
    }


def test_dataset_covers_the_retrieval_challenges_and_the_documents_exist() -> None:
    cases = json.loads((ROOT / "agents" / "evaluations" / "retrieval-dataset.json").read_text(encoding="utf-8"))["cases"]
    assert {case["category"] for case in cases} >= {"multi-source", "synonyms", "typos", "multilingual", "policy", "not-in-knowledge-base"}
    assert len({case["id"] for case in cases}) == len(cases)
    samples = ROOT / "samples"
    for case in cases:
        assert case["query"] and case["ground_truth"]
        assert bool(case.get("expect_unknown")) == (not case["expected_files"])
        for name in case["expected_files"]:
            assert (samples / "talent-pool" / name).exists() or (samples / "hiring-policies" / name).exists(), name


def test_retrieval_and_citation_recall() -> None:
    text = "- **Yuki Tanaka** fits.【6:1†source】 Band is GBP 64,000.【6:0†source】"
    item = agent_item(
        text,
        [citation(text, "【6:1†source】", "yuki-tanaka-ai-product-designer.pdf")],
        ["yuki-tanaka-ai-product-designer.pdf", "priya-nair-product-designer.pdf"],
        expected_files=["yuki-tanaka-ai-product-designer.pdf", "compensation-bands.md"],
    )
    assert graders.retrieval_recall(item) == 0.5
    assert graders.citation_recall(item) == 0.5
    item["expected_files"] = []
    assert graders.retrieval_recall(item) == graders.citation_recall(item) == 1.0


def test_citation_precision_catches_a_resume_on_another_candidates_line() -> None:
    text = "- **Priya Nair** is below the band.【6:0†source】\n- **Yuki Tanaka** is inside the band.【6:3†source】\n"
    right = citation(text, "【6:0†source】", "priya-nair-product-designer.pdf")
    wrong = citation(text, "【6:3†source】", "elena-petrova-design-systems-lead.pdf")
    policy = citation(text, "【6:0†source】", "compensation-bands.md", "hiring-policies")
    assert graders.citation_precision(agent_item(text, [right, wrong], [])) == 0.5
    assert graders.citation_precision(agent_item(text, [right, policy], [])) == 1.0
    assert graders.citation_precision(agent_item("No citations here.", [], [])) == 1.0


def test_citation_precision_ignores_punctuation_in_names() -> None:
    text = "- **Liam O'Connor** has DevOps experience.【6:0†source】"
    item = agent_item(text, [citation(text, "【6:0†source】", "liam-oconnor-devops-engineer.pdf")], [])
    assert graders.citation_precision(item) == 1.0


def test_honest_when_missing_in_both_directions() -> None:
    unknown = agent_item("I don't know: the documents do not contain a parental leave policy.", [], [], expect_unknown=True)
    invented = agent_item("Parental leave is 26 weeks.", [], [], expect_unknown=True)
    gave_up = agent_item("I don't know.", [], [], expect_unknown=False)
    answered = agent_item("Yuki Tanaka fits.", [], [], expect_unknown=False)
    assert [graders.honest_when_missing(item) for item in (unknown, invented, gave_up, answered)] == [1.0, 0.0, 0.0, 1.0]


def test_every_grader_runs_standalone_as_foundry_executes_it() -> None:
    text = "- **Yuki Tanaka** fits.【6:1†source】"
    item = agent_item(
        text, [citation(text, "【6:1†source】", "yuki-tanaka-ai-product-designer.pdf")],
        ["yuki-tanaka-ai-product-designer.pdf"], expected_files=["yuki-tanaka-ai-product-designer.pdf"], expect_unknown=False,
    )
    for metric in runner.CODE_METRICS:
        namespace: dict = {}
        exec(runner.grader_source(metric), namespace)  # noqa: S102 - mirrors the sandbox
        assert namespace["grade"]({}, item) == 1.0, metric


def test_criteria_combine_code_judge_and_builtin_evaluators() -> None:
    criteria = runner.testing_criteria("judge-model")
    names = [criterion["name"] for criterion in criteria]
    assert names == [
        "retrieval_recall", "citation_recall", "citation_precision", "honest_when_missing",
        "answer_correct", "groundedness", "relevance", "response_completeness",
    ]
    assert {criterion["type"] for criterion in criteria} == {"python", "score_model", "azure_ai_evaluator"}
    assert all(c["initialization_parameters"]["deployment_name"] == "judge-model" for c in criteria if c["type"] == "azure_ai_evaluator")


def test_runner_never_creates_or_changes_the_agent() -> None:
    source = (ROOT / "agents" / "evaluations" / "run_retrieval_evaluation.py").read_text(encoding="utf-8")
    assert "create_version" not in source
    assert source.count("set_effort(search, original)") == 1
    assert "finally:" in source


def test_grader_source_avoids_what_the_foundry_sandbox_rejects() -> None:
    source = (ROOT / "agents" / "evaluations" / "retrieval_graders.py").read_text(encoding="utf-8")
    assert "compile" not in source
    assert "import requests" not in source
