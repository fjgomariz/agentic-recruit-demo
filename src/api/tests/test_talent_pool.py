"""Talent pool matching: answer parsing, retrieval plan, agent service and endpoints."""

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
BANDS = f"{BLOB}/hiring-policies/compensation-bands.md"
SETTINGS = KnowledgeSettings(search_endpoint="https://search.example.net")

# Shapes taken from a live Foundry agent response with the knowledge base MCP tool.
ACTIVITY = [
    {"type": "modelQueryPlanning", "id": 0, "elapsedMs": 1428, "inputTokens": 1124, "outputTokens": 96, "model": {"modelName": "gpt-5.4-mini"}},
    {"type": "azureBlob", "id": 1, "knowledgeSourceName": "talent-pool-ks", "count": 10, "elapsedMs": 458, "azureBlobArguments": {"search": "Senior Product Designer candidates London"}},
    {"type": "azureBlob", "id": 2, "knowledgeSourceName": "hiring-policies-ks", "count": 1, "elapsedMs": 197, "azureBlobArguments": {"search": "Senior Product Designer compensation band"}},
    {"type": "agenticReasoning", "id": 3, "reasoningTokens": 18642, "retrievalReasoningEffort": {"kind": "low"}},
]


def document(url: str, snippet: str) -> dict[str, Any]:
    return {"id": "x", "title": url, "url": url, "content": json.dumps({"blob_url": url, "snippet": snippet})}


def agent_response(text_parts: list[tuple[str, list[tuple[str, str]]]], queries: list[str] | None = None) -> SimpleNamespace:
    """Build a response whose annotations point at the real marker positions in each text part."""

    documents = [document(JONAS, "Jonas Weber\nSenior UX Designer | Berlin, DE | jonas.weber@example.com"), document(BANDS, "# Compensation bands - Northstar (fictional)\n\nEffective 1 January 2026.")]
    output: list[dict[str, Any]] = [
        {"type": "mcp_list_tools"},
        {"type": "mcp_call", "name": "knowledge_base_retrieve", "arguments": json.dumps({"query_variants": queries or ["senior designers london"]}), "output": json.dumps({"documents": documents})},
    ]
    parts = []
    for text, markers in text_parts:
        annotations = []
        for marker, url in markers:
            start = text.index(marker)
            annotations.append({"type": "url_citation", "url": url, "start_index": start, "end_index": start + len(marker)})
        parts.append({"type": "output_text", "text": text, "annotations": annotations})
    output.append({"type": "message", "content": parts})
    return SimpleNamespace(id="resp_1", output=output, agent_reference={"name": "recruiter-copilot", "version": "2"}, usage=SimpleNamespace(input_tokens=7000, output_tokens=250))


def test_parse_answer_numbers_sources_by_first_citation_and_strips_markers() -> None:
    text = "- **Jonas Weber**: German, 3 months notice.【5:0†source】【5:0†source】\n- Band L4 is GBP 64,000 - 82,000.【5:1†source】 Done.【5:0†source】"
    response = agent_response([(text, [("【5:0†source】", JONAS), ("【5:1†source】", BANDS)])], queries=["german user research", "german user research", "l4 band"])

    # Annotation indices point at the first occurrence of each marker, so only those are replaced.
    answer, sources, queries = parse_answer(response)

    assert "【" not in answer and "†" not in answer
    assert [source.id for source in sources] == [1, 2]
    assert sources[0].container is KnowledgeSourceKind.TALENT_POOL and sources[0].file_name == "jonas-weber-senior-ux-designer-de.pdf"
    assert sources[0].title == "Jonas Weber"
    assert sources[1].container is KnowledgeSourceKind.HIRING_POLICIES and sources[1].title == "Compensation bands"
    assert answer.startswith("- **Jonas Weber**: German, 3 months notice.[1]")
    assert "[1][1]" not in answer
    assert queries == ["german user research", "l4 band"]


def test_parse_answer_drops_citations_that_do_not_point_at_a_knowledge_container() -> None:
    other = f"{BLOB}/resumes/application-123.pdf"
    traversal = f"{BLOB}/talent-pool/..%2Fsecrets.pdf"
    text = "Candidate.【1:0†source】 Another.【1:1†source】 Third.【1:2†source】"
    response = agent_response([(text, [("【1:0†source】", other), ("【1:1†source】", traversal), ("【1:2†source】", JONAS)])])

    answer, sources, _ = parse_answer(response)

    assert [source.file_name for source in sources] == ["jonas-weber-senior-ux-designer-de.pdf"]
    assert answer == "Candidate. Another. Third.[1]"


def test_parse_answer_tolerates_missing_annotations_and_plain_objects() -> None:
    response = SimpleNamespace(id="r", output=[SimpleNamespace(to_dict=lambda: {"type": "message", "content": [{"type": "output_text", "text": "Hello.【3:4†source】", "annotations": []}]})])
    answer, sources, queries = parse_answer(response)
    assert answer == "Hello." and sources == [] and queries == []


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
GOOD_RESPONSE = agent_response([("- **Jonas Weber**【5:0†source】", [("【5:0†source】", JONAS)])], queries=["senior product designer london"])


@pytest.mark.asyncio
async def test_match_calls_the_copilot_by_name_records_the_run_and_replays_the_plan() -> None:
    agent, responses, knowledge, recorder = service(GOOD_RESPONSE)

    result = await agent.match(JOB, "German speakers only")

    call = responses.calls[0]
    assert call["extra_body"] == {"agent_reference": {"name": "recruiter-copilot", "type": "agent_reference"}}
    assert "Title: Senior Product Designer" in call["input"] and "German speakers only" in call["input"]
    assert result.answer == "- **Jonas Weber**[1]" and result.sources[0].title == "Jonas Weber"
    assert result.agent_queries == ["senior product designer london"]
    assert knowledge.questions == ["senior product designer london"]
    assert result.retrieval_plan is not None and len(result.retrieval_plan.steps) == 4
    assert (result.execution_id, result.agent_version, result.input_tokens, result.output_tokens) == ("resp_1", "2", 7000, 250)
    assert recorder.executions[0].agent_name == "recruiter-copilot" and recorder.executions[0].related_entity_ids == [JOB.id]


@pytest.mark.asyncio
async def test_match_still_answers_when_the_retrieval_plan_cannot_be_read() -> None:
    agent, *_ = service(GOOD_RESPONSE, FakeKnowledge(fail=True))
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
    agent, *_ = service(GOOD_RESPONSE)
    app.dependency_overrides[get_talent_pool_agent] = lambda: agent

    response = client.post("/jobs/senior-product-designer/talent-matches", json={"notes": "german"})
    assert response.status_code == 200
    body = response.json()
    assert body["executionId"] == "resp_1" and body["agentQueries"] == ["senior product designer london"]
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
