"""Code-based graders for the recruiter-copilot retrieval evaluation.

Foundry runs each ``grade`` function in a sandbox (standard library only, no network). The runner builds
one criterion per metric by appending a small ``grade`` wrapper to this file, so every helper here must
stay self-contained. ``item`` is the dataset row plus the agent run under ``item["sample"]``.
"""

import json
import re

# Kept as a plain string: the Foundry sandbox rejects graders that build patterns ahead of time.
UNKNOWN_PATTERN = (
    r"(i don['’]?t know|i do not know|no (such |matching )?(candidates?|resumes?|information|documents?)"
    r"|not (found|covered|mentioned|in the (knowledge base|documents|talent pool))"
    r"|(do|does|did) not (contain|include|mention|cover|have)|(don['’]t|doesn['’]t|didn['’]t) (contain|include|mention|cover|have)"
    r"|no s[eé] |no tengo|no hay)"
)


def _output_items(item):
    items = (item.get("sample") or {}).get("output_items")
    return items if isinstance(items, list) else []


def _retrieved_text(items):
    return "\n".join(json.dumps(entry.get("content"), ensure_ascii=False) for entry in items if entry.get("role") == "tool")


def _answer(items):
    for entry in reversed(items):
        content = entry.get("content")
        if entry.get("role") == "assistant" and isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    return part.get("text") or "", part.get("annotations") or []
    return "", []


def _file_name(url):
    return str(url).rsplit("/", 1)[-1]


def _flat(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _fraction(found, expected):
    return sum(1 for name in expected if name in found) / len(expected) if expected else 1.0


def retrieval_recall(item):
    """Share of the expected documents that the knowledge base returned to the agent."""
    retrieved = _retrieved_text(_output_items(item))
    expected = item.get("expected_files") or []
    return sum(1 for name in expected if name in retrieved) / len(expected) if expected else 1.0


def citation_recall(item):
    """Share of the expected documents that the answer cites."""
    _, annotations = _answer(_output_items(item))
    cited = {_file_name(annotation.get("url", "")) for annotation in annotations if annotation.get("type") == "url_citation"}
    return _fraction(cited, item.get("expected_files") or [])


def citation_precision(item):
    """Share of resume citations that sit on a line that names that candidate.

    The model sometimes numbers its sources wrongly, which attaches a resume to a sentence about someone else.
    """
    text, annotations = _answer(_output_items(item))
    checked = correct = 0
    for annotation in annotations:
        url = str(annotation.get("url", ""))
        if annotation.get("type") != "url_citation" or "/talent-pool/" not in url:
            continue
        start = int(annotation.get("start_index", 0))
        line = text[text.rfind("\n", 0, start) + 1:]
        line = line.split("\n", 1)[0]
        name = "".join(_file_name(url).split("-")[:2])
        checked += 1
        if name in _flat(line):
            correct += 1
    return correct / checked if checked else 1.0


def honest_when_missing(item):
    """Says it does not know when the knowledge base cannot answer, and does not give up when it can."""
    text, _ = _answer(_output_items(item))
    says_unknown = bool(re.search(UNKNOWN_PATTERN, text[:400], re.IGNORECASE))
    if item.get("expect_unknown"):
        return 1.0 if says_unknown else 0.0
    return 0.0 if re.match(r"\s*(i don['’]?t know|i do not know)", text, re.IGNORECASE) else 1.0
