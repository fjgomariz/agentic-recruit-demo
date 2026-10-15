"""Talent pool matching: citation checking, retrieval plan, agent service and endpoints."""

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import AgentSettings, KnowledgeSettings, StorageSettings
from app.dependencies.agents import get_talent_pool_agent
from app.dependencies.services import get_job_service, get_knowledge_document_store
from app.domain import KnowledgeSourceKind
from app.main import app
from app.repositories import InMemoryRepository
from app.services import AgentResponseError, AgentUnavailableError, CrudService, KnowledgeBaseClient, TalentPoolAgentService
from app.services.talent_pool import build_talent_match_input, parse_answer, plan_from_activity
from app.storage import KnowledgeDocumentNotFoundError, KnowledgeDocumentStore
from job_fixtures import create_sample_jobs

BLOB = "https://strecruitmentdevqds3kzxb.blob.core.windows.net"
JONAS = f"{BLOB}/talent-pool/jonas-weber-senior-ux-designer-de.pdf"
ELENA = f"{BLOB}/talent-pool/elena-petrova-design-systems-lead.pdf"
YUKI = f"{BLOB}/talent-pool/yuki-tanaka-ai-product-designer.pdf"
BANDS = f"{BLOB}/hiring-policies/compensation-bands.md"
LANGUAGES = f"{BLOB}/hiring-policies/language-requirements.md"
SETTINGS = KnowledgeSettings(search_endpoint="https://search.example.net")

SNIPPETS = {
    JONAS: "Jonas Weber\nSenior UX Designer | Berlin, DE | jonas.weber@example.com\nSprachen: Deutsch, Englisch",
    ELENA: "Elena Petrova\nDesign Systems Lead | London, UK | elena.petrova@example.com",
    YUKI: "Yuki Tanaka\nProduct Designer, AI products | London, UK | yuki.tanaka@example.com",
    BANDS: "# Compensation bands - Northstar (fictional)\n\n| L4 | Senior Product Designer | 64,000 - 82,000 | UK GBP salary band per level",
    LANGUAGES: "# Language requirements - Northstar (fictional)\n\nEnglish is the working language. German C1 for DACH customer roles.",
}

# Shapes taken from a live Foundry agent response with the knowledge base MCP tool.
ACTIVITY = [
    {"type": "modelQueryPlanning", "id": 0, "elapsedMs": 1428, "inputTokens": 1124, "outputTokens": 96, "model": {"modelName": "gpt-5.4-mini"}},
    {"type": "azureBlob", "id": 1, "knowledgeSourceName": "talent-pool-ks", "count": 10, "elapsedMs": 458, "azureBlobArguments": {"search": "Senior Product Designer candidates London"}},
    {"type": "azureBlob", "id": 2, "knowledgeSourceName": "hiring-policies-ks", "count": 1, "elapsedMs": 197, "azureBlobArguments": {"search": "Senior Product Designer compensation band"}},
    {"type": "agenticReasoning", "id": 3, "reasoningTokens": 18642, "retrievalReasoningEffort": {"kind": "low"}},
]


def document(url: str) -> dict[str, Any]:
    return {"id": "x", "title": url, "url": url, "content": json.dumps({"blob_url": url, "snippet": SNIPPETS[url]})}


def agent_response(text: str, markers: list[tuple[str, str]], queries: list[str] | None = None) -> SimpleNamespace:
    """Build a response whose annotations sit on the real marker positions in the text.

    markers lists (marker, url) in order of appearance, so repeated markers get their own position.
    """

    annotations, cursor = [], 0
    for marker, url in markers:
        start = text.index(marker, cursor)
        annotations.append({"type": "url_citation", "url": url, "start_index": start, "end_index": start + len(marker)})
        cursor = start + len(marker)
    output: list[dict[str, Any]] = [
        {"type": "mcp_list_tools"},
        {"type": "mcp_call", "name": "knowledge_base_retrieve", "arguments": json.dumps({"query_variants": queries or ["senior designers london"]}), "output": json.dumps({"documents": [document(url) for url in SNIPPETS]})},
        {"type": "message", "content": [{"type": "output_text", "text": text, "annotations": annotations}]},
    ]
    return SimpleNamespace(id="resp_1", output=output, agent_reference={"name": "recruiter-copilot", "version": "2"}, usage=SimpleNamespace(input_tokens=7000, output_tokens=250))


M1, M2, M3 = "【6:0†source】", "【6:1†source】", "【6:2†source】"


def test_citations_that_the_line_supports_are_numbered_by_first_citation_and_markers_are_removed() -> None:
    text = f"- **Jonas Weber** speaks German; notice is 3 months.{M1}\n- The UK L4 salary band for a Senior Product Designer is GBP 64,000 - 82,000.{M2}"
    parsed = parse_answer(agent_response(text, [(M1, JONAS), (M2, BANDS)], queries=["german user research", "german user research", "l4 band"]))

    assert parsed.text == "- **Jonas Weber** speaks German; notice is 3 months.[1]\n- The UK L4 salary band for a Senior Product Designer is GBP 64,000 - 82,000.[2]"
    assert [(s.id, s.container, s.file_name, s.title) for s in parsed.sources] == [
        (1, KnowledgeSourceKind.TALENT_POOL, "jonas-weber-senior-ux-designer-de.pdf", "Jonas Weber"),
        (2, KnowledgeSourceKind.HIRING_POLICIES, "compensation-bands.md", "Compensation bands - Northstar (fictional)".split(" - ")[0]),
    ]
    assert parsed.citations_adjusted == 0 and "【" not in parsed.text
    assert parsed.queries == ["german user research", "l4 band"]


def test_a_citation_that_points_at_another_candidates_resume_is_corrected_to_the_named_candidate() -> None:
    # Seen live: the line about Elena cited Yuki's resume and the line about Yuki cited Elena's.
    text = f"- **Elena Petrova**: 3 months notice, GBP 92,000.{M1}\n- **Yuki Tanaka**: 2 months notice, GBP 74,000.{M2}"
    parsed = parse_answer(agent_response(text, [(M1, YUKI), (M2, ELENA)]))

    assert parsed.text == "- **Elena Petrova**: 3 months notice, GBP 92,000.[1]\n- **Yuki Tanaka**: 2 months notice, GBP 74,000.[2]"
    assert [s.title for s in parsed.sources] == ["Elena Petrova", "Yuki Tanaka"]
    assert parsed.citations_adjusted == 4


def test_a_policy_citation_is_dropped_when_the_sentence_is_about_something_else() -> None:
    # Seen live: a salary band sentence cited the language requirements policy.
    text = f"- The compensation band is GBP 64,000 - 82,000 for this level.{M1}\n- English is the working language.{M2}"
    parsed = parse_answer(agent_response(text, [(M1, LANGUAGES), (M2, LANGUAGES)]))

    assert parsed.text == "- The compensation band is GBP 64,000 - 82,000 for this level.\n- English is the working language.[1]"
    assert [s.file_name for s in parsed.sources] == ["language-requirements.md"]
    assert parsed.citations_adjusted == 1


def test_a_resume_cited_by_a_line_that_names_nobody_is_dropped_and_a_named_candidate_gets_their_resume() -> None:
    text = f"**Policy points:** confirm consent before contacting anyone.{M1}\n- **Jonas Weber** speaks German."
    parsed = parse_answer(agent_response(text, [(M1, ELENA)]))

    assert parsed.text == "**Policy points:** confirm consent before contacting anyone.\n- **Jonas Weber** speaks German.[1]"
    assert [s.title for s in parsed.sources] == ["Jonas Weber"]
    assert parsed.citations_adjusted == 2


def test_citations_to_documents_the_agent_never_retrieved_are_dropped() -> None:
    other = f"{BLOB}/resumes/application-123.pdf"
    text = f"Hello.{M1}"
    parsed = parse_answer(agent_response(text, [(M1, other)]))
    assert parsed.text == "Hello." and parsed.sources == [] and parsed.citations_adjusted == 1


def test_parse_answer_tolerates_missing_annotations_and_plain_objects() -> None:
    response = SimpleNamespace(id="r", output=[SimpleNamespace(to_dict=lambda: {"type": "message", "content": [{"type": "output_text", "text": "Hello.【3:4†source】", "annotations": []}]})])
    parsed = parse_answer(response)
    assert (parsed.text, parsed.sources, parsed.queries) == ("Hello.", [], [])


def test_plan_from_activity_summarizes_planning_subqueries_and_reasoning() -> None:
    plan = plan_from_activity(ACTIVITY)

    assert plan.reasoning_effort == "low"
    assert [step.kind for step in plan.steps] == ["planning", "search", "search", "reasoning"]
    assert plan.steps[0].model == "gpt-5.4-mini" and plan.steps[0].input_tokens == 1124
    assert (plan.steps[1].knowledge_source, plan.steps[1].query, plan.steps[1].document_count) == ("talent-pool-ks", "Senior Product Designer candidates London", 10)
    assert plan.steps[3].reasoning_tokens == 18642


@pytest.mark.asyncio
async def test_knowledge_base_client_requests_the_activity_log_with_an_entra_token() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), auth=request.headers["Authorization"], body=json.loads(request.content))
        return httpx.Response(200, json={"activity": ACTIVITY, "references": []})

    async def token() -> str:
        return "search-token"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        plan = await KnowledgeBaseClient(SETTINGS, token, http).plan("who speaks german")

    assert seen["url"] == "https://search.example.net/knowledgebases/recruiting-iq/retrieve?api-version=2026-08-01-preview"
    assert seen["auth"] == "Bearer search-token"
    assert seen["body"]["includeActivity"] is True
    assert seen["body"]["messages"][0]["content"][0]["text"] == "who speaks german"
    assert len(plan.steps) == 4


class FakeResponses:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.response


class FakeKnowledge:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.questions: list[str] = []

    async def plan(self, question: str) -> Any:
        self.questions.append(question)
        if self.fail:
            raise RuntimeError("search unavailable")
        return plan_from_activity(ACTIVITY)


class Recorder:
    def __init__(self) -> None:
        self.executions: list[Any] = []

    async def record(self, execution: Any) -> None:
        self.executions.append(execution)


def service(response: Any, knowledge: FakeKnowledge | None = None) -> tuple[TalentPoolAgentService, FakeResponses, FakeKnowledge, Recorder]:
    responses, knowledge, recorder = FakeResponses(response), knowledge or FakeKnowledge(), Recorder()
    agent = TalentPoolAgentService(AgentSettings(project_endpoint="https://example"), SimpleNamespace(responses=responses), knowledge, recorder)
    return agent, responses, knowledge, recorder


JOB = create_sample_jobs()[0]


def good_response() -> SimpleNamespace:
    return agent_response(f"- **Jonas Weber** speaks German.{M1}", [(M1, JONAS)], queries=["senior product designer london"])


@pytest.mark.asyncio
async def test_match_calls_the_copilot_by_name_records_the_run_and_replays_the_plan() -> None:
    agent, responses, knowledge, recorder = service(good_response())

    result = await agent.match(JOB, "German speakers only")

    call = responses.calls[0]
    assert call["extra_body"] == {"agent_reference": {"name": "recruiter-copilot", "type": "agent_reference"}}
    assert "Title: Senior Product Designer" in call["input"] and "German speakers only" in call["input"]
    assert result.answer == "- **Jonas Weber** speaks German.[1]" and result.sources[0].title == "Jonas Weber"
    assert result.citations_adjusted == 0 and result.agent_queries == ["senior product designer london"]
    assert knowledge.questions == ["senior product designer london"]
    assert result.retrieval_plan is not None and len(result.retrieval_plan.steps) == 4
    assert (result.execution_id, result.agent_version, result.input_tokens, result.output_tokens) == ("resp_1", "2", 7000, 250)
    assert recorder.executions[0].agent_name == "recruiter-copilot" and recorder.executions[0].related_entity_ids == [JOB.id]


@pytest.mark.asyncio
async def test_match_still_answers_when_the_retrieval_plan_cannot_be_read() -> None:
    agent, *_ = service(good_response(), FakeKnowledge(fail=True))
    result = await agent.match(JOB)
    assert result.answer and result.retrieval_plan is None


@pytest.mark.asyncio
async def test_match_rejects_an_empty_answer_and_reports_an_unconfigured_agent() -> None:
    agent, _, _, recorder = service(SimpleNamespace(id="resp_2", output=[{"type": "mcp_list_tools"}], usage=None, agent_reference=None))
    with pytest.raises(AgentResponseError):
        await agent.match(JOB)
    assert recorder.executions[0].error_message == "The agent output did not match the expected schema"

    with pytest.raises(AgentUnavailableError):
        await TalentPoolAgentService(AgentSettings(project_endpoint=None), client=None).match(JOB)


def test_match_input_contains_the_job_and_marks_missing_notes() -> None:
    text = build_talent_match_input(JOB, "")
    assert "Find candidates in our talent pool" in text and "Required qualifications:" in text
    assert text.endswith("Recruiter notes:\n(none)")


@pytest.fixture
def client() -> TestClient:
    jobs = CrudService(InMemoryRepository(create_sample_jobs()), "Job")
    app.dependency_overrides[get_job_service] = lambda: jobs
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_endpoint_returns_camel_case_result_and_maps_errors(client: TestClient) -> None:
    agent, *_ = service(good_response())
    app.dependency_overrides[get_talent_pool_agent] = lambda: agent

    response = client.post("/jobs/senior-product-designer/talent-matches", json={"notes": "german"})
    assert response.status_code == 200
    body = response.json()
    assert body["executionId"] == "resp_1" and body["agentQueries"] == ["senior product designer london"] and body["citationsAdjusted"] == 0
    assert body["sources"][0] == {"id": 1, "container": "talent-pool", "fileName": "jonas-weber-senior-ux-designer-de.pdf", "title": "Jonas Weber"}
    assert body["retrievalPlan"]["steps"][1]["knowledgeSource"] == "talent-pool-ks"

    assert client.post("/jobs/nope/talent-matches", json={}).status_code == 404
    assert client.post("/jobs/senior-product-designer/talent-matches", json={"notes": "x" * 501}).status_code == 422

    app.dependency_overrides[get_talent_pool_agent] = lambda: TalentPoolAgentService(AgentSettings(project_endpoint=None), None)
    assert client.post("/jobs/senior-product-designer/talent-matches", json={}).status_code == 503
    empty, *_ = service(SimpleNamespace(id="r", output=[], usage=None, agent_reference=None))
    app.dependency_overrides[get_talent_pool_agent] = lambda: empty
    assert client.post("/jobs/senior-product-designer/talent-matches", json={}).status_code == 502


class FakeStore:
    async def download(self, container: str, file_name: str) -> tuple[bytes, str]:
        if file_name != "jonas-weber-senior-ux-designer-de.pdf":
            raise KnowledgeDocumentNotFoundError("missing")
        return b"%PDF-1.4 test", "application/pdf"


def test_document_endpoint_serves_inline_and_returns_404_for_unknown_documents(client: TestClient) -> None:
    app.dependency_overrides[get_knowledge_document_store] = lambda: FakeStore()

    found = client.get("/knowledge-documents/talent-pool/jonas-weber-senior-ux-designer-de.pdf")
    assert found.status_code == 200 and found.content.startswith(b"%PDF")
    assert found.headers["content-type"] == "application/pdf"
    assert found.headers["content-disposition"].startswith("inline;") and found.headers["x-content-type-options"] == "nosniff"
    assert client.get("/knowledge-documents/talent-pool/other.pdf").status_code == 404


@pytest.mark.asyncio
async def test_document_store_only_serves_plain_files_from_the_knowledge_containers() -> None:
    store = KnowledgeDocumentStore(StorageSettings(blob_endpoint="https://example.blob.core.windows.net"), SETTINGS)
    try:
        for container, name in [("resumes", "a.pdf"), ("talent-pool", "../a.pdf"), ("talent-pool", "a/b.pdf"), ("talent-pool", "a.exe"), ("hiring-policies", ".env")]:
            with pytest.raises(KnowledgeDocumentNotFoundError):
                await store.download(container, name)
    finally:
        await store.close()
