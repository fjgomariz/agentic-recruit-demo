"""Match open jobs against the talent pool with the Foundry IQ recruiter copilot."""

import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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
TERM = re.compile(r"[a-z0-9]+(?:[,.][0-9]+)*")
MAX_TITLE_LENGTH = 60
PLAN_TIMEOUT_SECONDS = 45
MIN_SHARED_TERMS = 2
# Words that appear in nearly every document and say nothing about which policy a sentence comes from.
GENERIC_TERMS = frozenset(
    "about also been candidate candidates each every from have into level levels like more most only other over policy "
    "required requires requirement requirements role roles should some such than that their them then there these they "
    "this those used what when where which will with would your".split()
)

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


def _person(snippet: str | None) -> str | None:
    """The candidate's name: the first line of a resume, when it looks like a name."""

    first = next((line.strip() for line in (snippet or "").splitlines() if line.strip()), "")
    if first and len(first) <= MAX_TITLE_LENGTH and not any(mark in first for mark in "|@:"):
        return first
    return None


def _terms(text: str) -> set[str]:
    """Distinctive lowercase terms, with plurals folded, used to tell which policy a sentence is about."""

    terms = set()
    for word in TERM.findall(text.lower()):
        if any(character.isdigit() for character in word):
            terms.add(word)
        elif len(word) >= 4 and word not in GENERIC_TERMS:
            terms.add(word[:-1] if word.endswith("s") and not word.endswith("ss") else word)
    return terms


def _mentions(line: str, name: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(name)}(?!\w)", line, re.IGNORECASE) is not None


@dataclass(frozen=True)
class RetrievedDocument:
    """A document the agent's knowledge base call returned, with enough content to check citations against."""

    url: str
    kind: KnowledgeSourceKind
    file_name: str
    snippet: str
    person: str | None

    @property
    def title(self) -> str:
        if self.kind is KnowledgeSourceKind.TALENT_POOL and self.person:
            return self.person
        return _humanize(self.file_name)


def _retrieved(output_items: list[dict[str, Any]]) -> tuple[list[str], dict[str, RetrievedDocument]]:
    """Read the queries the agent sent and the documents the knowledge base returned."""

    queries: list[str] = []
    documents: dict[str, RetrievedDocument] = {}
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
            returned = json.loads(item.get("output") or "{}").get("documents") or []
        except (TypeError, json.JSONDecodeError, AttributeError):
            returned = []
        for document in returned:
            try:
                content = json.loads(document.get("content") or "{}")
            except (TypeError, json.JSONDecodeError):
                content = {}
            url = content.get("blob_url") or document.get("url")
            located = _location(url) if isinstance(url, str) else None
            if located is None or url in documents:
                continue
            snippet = content.get("snippet") if isinstance(content.get("snippet"), str) else ""
            documents[url] = RetrievedDocument(url, located[0], located[1], snippet, _person(snippet) if located[0] is KnowledgeSourceKind.TALENT_POOL else None)
    return queries, documents


@dataclass(frozen=True)
class ParsedAnswer:
    text: str
    sources: list[TalentMatchSource]
    queries: list[str]
    citations_adjusted: int


def _verified_citations(line: str, cited: list[str], documents: dict[str, RetrievedDocument]) -> tuple[list[str], int]:
    """Keep only the citations the line itself supports, and add the resume of every candidate it names.

    The model numbers documents unreliably in long answers, so a citation is trusted only when the text agrees:
    a resume must belong to a candidate named in the line, and a policy must share distinctive terms with the line.
    """

    named = [document for document in documents.values() if document.person and _mentions(line, document.person)]
    line_terms = _terms(line)
    keep: list[str] = []
    adjusted = 0
    for url in cited:
        document = documents.get(url)
        if document is None:
            supported = False
        elif document.kind is KnowledgeSourceKind.TALENT_POOL:
            supported = document in named
        else:
            supported = len(line_terms & _terms(document.snippet)) >= MIN_SHARED_TERMS
        if supported and url not in keep:
            keep.append(url)
        elif not supported:
            adjusted += 1
    for document in named:
        if document.url not in keep:
            keep.append(document.url)
            adjusted += 1
    return keep, adjusted


def parse_answer(response: Any) -> ParsedAnswer:
    """Turn the agent's message into text with verified [n] markers, the numbered sources and the queries it ran."""

    items = [_as_dict(item) for item in (getattr(response, "output", None) or [])]
    queries, documents = _retrieved(items)

    sources: list[TalentMatchSource] = []
    numbers: dict[str, int] = {}
    adjusted = 0

    def number_for(url: str) -> int:
        if url not in numbers:
            document = documents[url]
            numbers[url] = len(sources) + 1
            sources.append(TalentMatchSource(id=numbers[url], container=document.kind, file_name=document.file_name, title=document.title))
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
            spans = []
            for annotation in (_as_dict(a) for a in part.get("annotations") or []):
                start, end = annotation.get("start_index"), annotation.get("end_index")
                if annotation.get("type") == "url_citation" and isinstance(start, int) and isinstance(end, int) and CITATION_MARKER.fullmatch(text[start:end]):
                    spans.append((start, annotation.get("url") or ""))

            lines, offset = [], 0
            for raw in text.split("\n"):
                cited = [url for start, url in spans if offset <= start < offset + len(raw)]
                offset += len(raw) + 1
                clean = CITATION_MARKER.sub("", raw).rstrip()
                if not clean.strip():
                    lines.append(clean)
                    continue
                keep, changed = _verified_citations(clean, cited, documents)
                adjusted += changed
                lines.append(clean + "".join(f"[{number}]" for number in dict.fromkeys(number_for(url) for url in keep)))
            paragraphs.append("\n".join(lines))

    return ParsedAnswer("\n\n".join(paragraphs).strip(), sources, queries, adjusted)


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

        parsed = parse_answer(response)
        if not parsed.text:
            logger.error("Recruiter copilot returned no answer response_id=%s", response.id)
            await self._agent.record_invalid_output(run, related_entity_ids=related)
            raise AgentResponseError("The recruiter copilot returned no answer")
        if parsed.citations_adjusted:
            logger.info("Adjusted %s citations that did not match the text response_id=%s", parsed.citations_adjusted, response.id)

        await self._agent.record_success(
            run, related_entity_ids=related,
            output_summary=f"Searched the talent pool for '{job.title}': {len(parsed.sources)} sources cited, {parsed.citations_adjusted} citations adjusted",
        )
        return TalentMatchResult(
            answer=parsed.text,
            sources=parsed.sources,
            citations_adjusted=parsed.citations_adjusted,
            agent_queries=parsed.queries,
            retrieval_plan=await self._plan(parsed.queries[0] if parsed.queries else question),
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
