"""Match open jobs against the talent pool with the Foundry IQ recruiter copilot."""

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from app.config import AgentSettings, KnowledgeSettings
from app.domain import (
    Job,
    KnowledgeSourceKind,
    RetrievalPlan,
    RetrievalStep,
    TalentMatchResult,
    TalentMatchSource,
)

from .agents import AgentRunRecorder, AgentResponseError, FoundryAgent, NullRecorder, ResponsesClient, job_posting_lines

logger = logging.getLogger(__name__)

KNOWLEDGE_API_VERSION = "2026-08-01-preview"
SAFE_FILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CITATION_MARKER = re.compile(r"【[^】]*】")
REPEATED_MARKER = re.compile(r"(\[(\d+)\])(?:\[\2\])+")
MAX_TITLE_LENGTH = 60
PLAN_TIMEOUT_SECONDS = 45

TokenProvider = Callable[[], Awaitable[str]]


def build_talent_match_input(job: Job, notes: str) -> str:
    """Ask the recruiter copilot to shortlist talent pool candidates for an open role."""

    lines = [
        "Find candidates in our talent pool for this open role. For each one, check the salary expectation "
        "against our compensation band for the role's level and country, and flag any policy point that matters.",
        "",
        *job_posting_lines(job),
        "",
        "Recruiter notes:",
        notes.strip() or "(none)",
    ]
    return "\n".join(lines)


def _as_dict(value: Any) -> dict[str, Any]:
    """View an SDK object, a pydantic model or a plain dict as a dict."""

    if isinstance(value, dict):
        return value
    for method in ("to_dict", "model_dump"):
        converter = getattr(value, method, None)
        if callable(converter):
            return converter()
    return dict(vars(value))


def _location(url: str) -> tuple[KnowledgeSourceKind, str] | None:
    """Split a blob URL into its knowledge source container and a validated file name."""

    parts = [unquote(part) for part in urlparse(url).path.split("/") if part]
    if len(parts) != 2:
        return None
    container, file_name = parts
    try:
        kind = KnowledgeSourceKind(container)
    except ValueError:
        return None
    return (kind, file_name) if SAFE_FILE_NAME.match(file_name) else None


def _humanize(file_name: str) -> str:
    stem = file_name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ")
    return stem[:1].upper() + stem[1:]


def _title(kind: KnowledgeSourceKind, file_name: str, snippet: str | None) -> str:
    """Name a resume after the person on its first line; policies are named after their file."""

    if kind is KnowledgeSourceKind.TALENT_POOL and snippet:
        first = next((line.strip() for line in snippet.splitlines() if line.strip()), "")
        if first and len(first) <= MAX_TITLE_LENGTH and not any(mark in first for mark in "|@:"):
            return first
    return _humanize(file_name)


def _retrieved_documents(output_items: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    """Read the agent's knowledge base queries and the first line of every retrieved document."""

    queries: list[str] = []
    snippets: dict[str, str] = {}
    for item in output_items:
        if item.get("type") != "mcp_call":
            continue
        try:
            arguments = json.loads(item.get("arguments") or "{}")
        except (TypeError, json.JSONDecodeError):
            arguments = {}
        for query in arguments.get("query_variants") or []:
            if isinstance(query, str) and query not in queries:
                queries.append(query)
        try:
            documents = json.loads(item.get("output") or "{}").get("documents") or []
        except (TypeError, json.JSONDecodeError, AttributeError):
            documents = []
        for document in documents:
            try:
                content = json.loads(document.get("content") or "{}")
            except (TypeError, json.JSONDecodeError):
                content = {}
            url = content.get("blob_url") or document.get("url") or document.get("title")
            if isinstance(url, str) and isinstance(content.get("snippet"), str):
                snippets.setdefault(url, content["snippet"])
    return queries, snippets


def parse_answer(response: Any) -> tuple[str, list[TalentMatchSource], list[str]]:
    """Turn the agent's message into text with [n] markers, the numbered sources and the queries it ran."""

    items = [_as_dict(item) for item in (getattr(response, "output", None) or [])]
    queries, snippets = _retrieved_documents(items)

    sources: list[TalentMatchSource] = []
    numbers: dict[str, int] = {}

    def number_for(url: str) -> int | None:
        located = _location(url)
        if located is None:
            return None
        if url not in numbers:
            kind, file_name = located
            numbers[url] = len(sources) + 1
            sources.append(TalentMatchSource(id=numbers[url], container=kind, file_name=file_name, title=_title(kind, file_name, snippets.get(url))))
        return numbers[url]

    paragraphs: list[str] = []
    for item in items:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            part = _as_dict(part)
            text = part.get("text")
            if not isinstance(text, str):
                continue
            annotations = sorted(
                (_as_dict(a) for a in part.get("annotations") or [] if _as_dict(a).get("type") == "url_citation"),
                key=lambda annotation: annotation.get("start_index", 0),
            )
            # Number sources in reading order, then replace from the end so earlier indices stay valid.
            numbered = [(annotation, number_for(annotation.get("url") or "")) for annotation in annotations]
            for annotation, number in reversed(numbered):
                start, end = annotation.get("start_index"), annotation.get("end_index")
                if not isinstance(start, int) or not isinstance(end, int) or not CITATION_MARKER.fullmatch(text[start:end]):
                    continue
                text = f"{text[:start]}{f'[{number}]' if number else ''}{text[end:]}"
            paragraphs.append(CITATION_MARKER.sub("", text))

    answer = REPEATED_MARKER.sub(r"\1", "\n\n".join(paragraphs)).strip()
    return answer, sources, queries


class KnowledgeBaseClient:
    """Ask the Foundry IQ knowledge base how it breaks a question down (the retrieval activity log)."""

    def __init__(self, settings: KnowledgeSettings, token_provider: TokenProvider, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._token_provider = token_provider
        self._http = http

    async def plan(self, question: str) -> RetrievalPlan:
        token = await self._token_provider()
        response = await self._http.post(
            f"{self._settings.search_endpoint}/knowledgebases/{self._settings.knowledge_base_name}/retrieve",
            params={"api-version": KNOWLEDGE_API_VERSION},
            headers={"Authorization": f"Bearer {token}"},
            json={"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}], "includeActivity": True},
            timeout=PLAN_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return plan_from_activity(response.json().get("activity") or [])


def plan_from_activity(activity: list[dict[str, Any]]) -> RetrievalPlan:
    steps: list[RetrievalStep] = []
    effort: str | None = None
    for record in activity:
        kind = record.get("type")
        if kind == "modelQueryPlanning":
            model = record.get("model") or {}
            steps.append(RetrievalStep(
                kind="planning", elapsed_ms=record.get("elapsedMs"), model=model.get("modelName"),
                input_tokens=record.get("inputTokens"), output_tokens=record.get("outputTokens"),
            ))
        elif kind == "agenticReasoning":
            effort = (record.get("retrievalReasoningEffort") or {}).get("kind")
            steps.append(RetrievalStep(kind="reasoning", reasoning_tokens=record.get("reasoningTokens")))
        elif record.get("knowledgeSourceName"):
            arguments = next((value for key, value in record.items() if key.endswith("Arguments") and isinstance(value, dict)), {})
            steps.append(RetrievalStep(
                kind="search", knowledge_source=record["knowledgeSourceName"], query=arguments.get("search"),
                document_count=record.get("count"), elapsed_ms=record.get("elapsedMs"),
            ))
    return RetrievalPlan(steps=steps, reasoning_effort=effort)


class TalentPoolAgentService:
    """Shortlist talent pool candidates for a job with the recruiter copilot agent."""

    def __init__(
        self,
        settings: AgentSettings,
        client: ResponsesClient | None,
        knowledge: KnowledgeBaseClient | None = None,
        recorder: AgentRunRecorder | None = None,
    ) -> None:
        self._agent = FoundryAgent(settings.recruiter_copilot_agent_name, settings.model_deployment_name, client, recorder or NullRecorder())
        self._knowledge = knowledge

    @property
    def configured(self) -> bool:
        return self._agent.configured and self._knowledge is not None

    async def match(self, job: Job, notes: str = "") -> TalentMatchResult:
        related = [job.id]
        question = build_talent_match_input(job, notes)
        response, run = await self._agent.run(question, related_entity_ids=related)

        answer, sources, queries = parse_answer(response)
        if not answer:
            logger.error("Recruiter copilot returned no answer response_id=%s", response.id)
            await self._agent.record_invalid_output(run, related_entity_ids=related)
            raise AgentResponseError("The recruiter copilot returned no answer")

        await self._agent.record_success(
            run, related_entity_ids=related,
            output_summary=f"Searched the talent pool for '{job.title}': {len(sources)} sources cited",
        )
        return TalentMatchResult(
            answer=answer,
            sources=sources,
            agent_queries=queries,
            retrieval_plan=await self._plan(queries[0] if queries else question),
            execution_id=response.id,
            agent_name=self._agent.agent_name,
            agent_version=run.agent_version,
            duration_ms=run.duration_ms,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
        )

    async def _plan(self, question: str) -> RetrievalPlan | None:
        """Replay the question the agent sent to show the plan; the answer never depends on it."""

        if self._knowledge is None:
            return None
        try:
            return await self._knowledge.plan(question)
        except Exception:
            logger.warning("Could not read the knowledge base retrieval activity", exc_info=True)
            return None
