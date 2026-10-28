"""Compare Foundry IQ retrieval reasoning effort for the recruiter copilot with a Foundry evaluation.

The recruiter-copilot agent is the target and stays unchanged. Each run changes only the knowledge base's
``retrievalReasoningEffort`` (minimal, low or medium), sends the same questions to the agent and scores the
answers. All runs belong to one evaluation, so Foundry (**Evaluations** in the portal) lets you compare them.

Criteria:
- retrieval_recall: the expected documents were returned by the knowledge base (code).
- citation_recall: the answer cites the expected documents (code).
- citation_precision: every resume citation sits on a line about that candidate (code).
- honest_when_missing: it says it does not know when the knowledge base cannot answer (code).
- answer_correct: a judge compares the answer with the reference answer.
- groundedness, relevance, response_completeness: Foundry built-in evaluators.

The knowledge base is shared with the portal: it is switched for the duration of each run and restored to
its original effort at the end, even if the script fails.

    python agents/evaluations/run_retrieval_evaluation.py
    python agents/evaluations/run_retrieval_evaluation.py --efforts low medium --cases role-and-band unknown-policy

Environment: AZURE_AI_PROJECT_ENDPOINT, AZURE_SEARCH_ENDPOINT and optionally EVALUATION_JUDGE_MODEL_DEPLOYMENT
(default gpt-5.4). The caller needs Foundry User on the project and Search Service Contributor on the search service.
"""

import argparse
import inspect
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "knowledge"))

import retrieval_graders  # noqa: E402
from setup_knowledge import KNOWLEDGE_BASE, Search  # noqa: E402

DATASET = HERE / "retrieval-dataset.json"
EVALUATION_NAME = "recruiter-copilot-retrieval-quality"
AGENT = "recruiter-copilot"
DEFAULT_JUDGE = "gpt-5.4"
EFFORTS = ("minimal", "low", "medium")
CODE_METRICS = ("retrieval_recall", "citation_recall", "citation_precision", "honest_when_missing")


def load_cases(selected: list[str] | None) -> list[dict[str, Any]]:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    if selected:
        unknown = set(selected) - {case["id"] for case in cases}
        if unknown:
            raise SystemExit(f"Unknown case ids: {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case["id"] in selected]
    return [
        {
            "case": case["id"], "category": case["category"], "query": case["query"],
            "expected_files": case["expected_files"], "expect_unknown": bool(case.get("expect_unknown")),
            "ground_truth": case["ground_truth"],
        }
        for case in cases
    ]


def grader_source(metric: str) -> str:
    """The graders module plus a ``grade`` entry point for one metric (Foundry runs it as a standalone script)."""
    return inspect.getsource(retrieval_graders) + f"\n\ndef grade(sample, item):\n    return {metric}(item)\n"


def testing_criteria(judge_model: str) -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = [
        {"type": "python", "name": metric, "source": grader_source(metric), "pass_threshold": 1.0}
        for metric in CODE_METRICS
    ]
    criteria.append({
        "type": "score_model", "name": "answer_correct", "model": judge_model, "range": [0, 1], "pass_threshold": 0.7,
        "input": [
            {"role": "system", "content": (
                "You grade an answer from a recruiting assistant against a reference answer. Score 1 when the answer "
                "contains every fact of the reference (names, salary figures, bands, rules) and nothing in it "
                "contradicts the reference. Other candidates or details are fine when they are plausible and the "
                "answer says why they fit less. Lower the score for each missing reference fact, wrong number, wrong "
                "verdict (inside or outside a band) or content invented about a document. When the reference says "
                "the knowledge base cannot answer, the answer must say it does not know and must not invent content. "
                "When the reference names a language for the answer, the answer must use it. Return a number from 0 to 1."
            )},
            {"role": "user", "content": "QUESTION:\n{{item.query}}\n\nREFERENCE ANSWER:\n{{item.ground_truth}}\n\nANSWER:\n{{sample.output_text}}"},
        ],
    })
    criteria += [
        {
            "type": "azure_ai_evaluator", "name": "groundedness", "evaluator_name": "builtin.groundedness",
            "initialization_parameters": {"deployment_name": judge_model},
            "data_mapping": {
                "query": "{{item.query}}", "response": "{{sample.output_items}}",
                "tool_definitions": "{{sample.tool_definitions}}",
            },
        },
        {
            "type": "azure_ai_evaluator", "name": "relevance", "evaluator_name": "builtin.relevance",
            "initialization_parameters": {"deployment_name": judge_model},
            "data_mapping": {"query": "{{item.query}}", "response": "{{sample.output_text}}"},
        },
        {
            "type": "azure_ai_evaluator", "name": "response_completeness", "evaluator_name": "builtin.response_completeness",
            "initialization_parameters": {"deployment_name": judge_model},
            "data_mapping": {"ground_truth": "{{item.ground_truth}}", "response": "{{sample.output_text}}"},
        },
    ]
    return criteria


def get_or_create_evaluation(openai: Any, judge_model: str) -> str:
    for existing in openai.evals.list(limit=100):
        if existing.name == EVALUATION_NAME:
            return existing.id
    created = openai.evals.create(
        name=EVALUATION_NAME,
        data_source_config={
            "type": "custom", "include_sample_schema": True,
            "item_schema": {
                "type": "object",
                "properties": {
                    "case": {"type": "string"}, "category": {"type": "string"}, "query": {"type": "string"},
                    "expected_files": {"type": "array", "items": {"type": "string"}},
                    "expect_unknown": {"type": "boolean"}, "ground_truth": {"type": "string"},
                },
                "required": ["query", "ground_truth"],
            },
        },
        testing_criteria=testing_criteria(judge_model),
    )
    return created.id


def set_effort(search: Search, kind: str) -> None:
    knowledge_base = search.request("GET", f"/knowledgebases/{KNOWLEDGE_BASE}")
    knowledge_base = {key: value for key, value in knowledge_base.items() if not key.startswith("@odata")}
    knowledge_base["retrievalReasoningEffort"] = {"kind": kind}
    search.request("PUT", f"/knowledgebases/{KNOWLEDGE_BASE}", knowledge_base)


def current_effort(search: Search) -> str:
    return search.request("GET", f"/knowledgebases/{KNOWLEDGE_BASE}").get("retrievalReasoningEffort", {}).get("kind", "low")


def run_variant(openai: Any, evaluation_id: str, effort: str, version: str, items: list[dict[str, Any]]) -> Any:
    run = openai.evals.runs.create(
        eval_id=evaluation_id,
        name=f"kb-effort-{effort} ({AGENT} v{version})",
        metadata={"agent": AGENT, "agent_version": version, "retrieval_reasoning_effort": effort},
        data_source={
            "type": "azure_ai_target_completions",
            "source": {"type": "file_content", "content": [{"item": item} for item in items]},
            "input_messages": {"type": "template", "template": [
                {"type": "message", "role": "user", "content": {"type": "input_text", "text": "{{item.query}}"}},
            ]},
            "target": {"type": "azure_ai_agent", "name": AGENT, "version": version},
        },
    )
    print(f"[{effort}] started {run.name}", flush=True)
    while run.status not in ("completed", "failed", "canceled"):
        time.sleep(10)
        run = openai.evals.runs.retrieve(run_id=run.id, eval_id=evaluation_id)
    print(f"[{effort}] {run.status}: {run.report_url}", flush=True)
    if run.status != "completed":
        print(f"[{effort}] error: {run.error}", flush=True)
    return run


def summarize(openai: Any, evaluation_id: str, run: Any) -> dict[str, Any]:
    scores: dict[str, list[float]] = {}
    latencies: list[float] = []
    tokens: list[int] = []
    failures: list[str] = []
    for output in openai.evals.runs.output_items.list(run_id=run.id, eval_id=evaluation_id, limit=100):
        data = output.model_dump()
        case = (data.get("datasource_item") or {}).get("case", data.get("datasource_item_id"))
        for result in data.get("results") or []:
            if result.get("score") is not None:
                scores.setdefault(result["name"], []).append(float(result["score"]))
            if result.get("passed") is False:
                failures.append(f"{case}: {result['name']}")
        sample = data.get("sample") or {}
        if sample.get("latency_ms"):
            latencies.append(float(sample["latency_ms"]) / 1000)
        if (sample.get("usage") or {}).get("total_tokens"):
            tokens.append(int(sample["usage"]["total_tokens"]))
    return {
        "status": run.status, "url": run.report_url, "scores": scores, "failures": failures,
        "latency_median": statistics.median(latencies) if latencies else None,
        "latency_max": max(latencies) if latencies else None,
        "tokens_mean": statistics.mean(tokens) if tokens else None,
    }


def print_table(results: dict[str, dict[str, Any]]) -> None:
    metrics = list(dict.fromkeys(name for result in results.values() for name in result["scores"]))
    print("\nMean score per criterion (code and judge criteria: 0-1; groundedness, relevance and response_completeness: built-in 1-5 scale)")
    print(f"{'criterion':<24}" + "".join(f"{effort:>10}" for effort in results))
    for metric in metrics:
        row = "".join(
            f"{statistics.mean(result['scores'][metric]):>10.2f}" if metric in result["scores"] else f"{'-':>10}"
            for result in results.values()
        )
        print(f"{metric:<24}{row}")
    print(f"{'median latency (s)':<24}" + "".join(f"{(r['latency_median'] or 0):>10.1f}" for r in results.values()))
    print(f"{'max latency (s)':<24}" + "".join(f"{(r['latency_max'] or 0):>10.1f}" for r in results.values()))
    print(f"{'mean tokens':<24}" + "".join(f"{(r['tokens_mean'] or 0):>10.0f}" for r in results.values()))
    for effort, result in results.items():
        if result["failures"]:
            print(f"\n[{effort}] failed checks: " + "; ".join(result["failures"]))


def report(judge_model: str) -> int:
    """Print the comparison for the newest completed run of each effort."""
    results: dict[str, dict[str, Any]] = {}
    with DefaultAzureCredential() as credential, AIProjectClient(
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=credential
    ) as client, client.get_openai_client() as openai:
        evaluation_id = get_or_create_evaluation(openai, judge_model)
        runs = sorted(openai.evals.runs.list(eval_id=evaluation_id, limit=100), key=lambda run: run.created_at, reverse=True)
        for run in runs:
            effort = (run.metadata or {}).get("retrieval_reasoning_effort")
            if effort and run.status == "completed" and effort not in results:
                results[effort] = summarize(openai, evaluation_id, run)
    print_table({effort: results[effort] for effort in EFFORTS if effort in results})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--efforts", nargs="+", choices=EFFORTS, default=list(EFFORTS), help="Retrieval reasoning efforts to compare")
    parser.add_argument("--cases", nargs="+", help="Run only these case ids")
    parser.add_argument("--dry-run", action="store_true", help="Show the dataset rows without calling Foundry")
    parser.add_argument("--report", action="store_true", help="Compare the latest existing run of each effort without starting new runs")
    args = parser.parse_args()

    items = load_cases(args.cases)
    if args.dry_run:
        print(json.dumps([{key: item[key] for key in ("case", "category", "expected_files", "expect_unknown")} for item in items], indent=2))
        return 0

    judge_model = os.getenv("EVALUATION_JUDGE_MODEL_DEPLOYMENT", DEFAULT_JUDGE)
    if args.report:
        return report(judge_model)
    search = Search(os.environ["AZURE_SEARCH_ENDPOINT"])
    original = current_effort(search)
    results: dict[str, dict[str, Any]] = {}
    with DefaultAzureCredential() as credential, AIProjectClient(
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=credential
    ) as client, client.get_openai_client() as openai:
        version = str(client.agents.get(agent_name=AGENT).versions.latest.version)
        evaluation_id = get_or_create_evaluation(openai, judge_model)
        try:
            for effort in args.efforts:
                set_effort(search, effort)
                run = run_variant(openai, evaluation_id, effort, version, items)
                results[effort] = summarize(openai, evaluation_id, run)
        finally:
            set_effort(search, original)
            print(f"Knowledge base reasoning effort restored to '{original}'", flush=True)
    print_table(results)
    return 0 if all(result["status"] == "completed" for result in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
