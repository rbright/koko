from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from typing import Any
from urllib.parse import urlparse

from .errors import SummarizationError

SUMMARY_PROMPT_RESOURCE = "prompts/summarize_for_speech.txt"
MAX_SUMMARY_SENTENCES = 4
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
SUMMARY_META_PREFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?is)^\s*(?:summary|recap)(?:\s*[:\-–]\s*|\s+)"),
    re.compile(
        r"(?is)^\s*(?:here(?:'s| is)|this is|the following is)\s+"
        r"(?:a\s+)?(?:brief|quick|short|concise)?\s*(?:summary|recap)"
        r"(?:\s+(?:in|as)\s+(?:a\s+)?(?:more\s+)?conversational(?:\s+form)?)?"
        r"(?:\s*[:\-–]\s*|\s+)"
    ),
    re.compile(r"(?is)^\s*(?:in summary|to summarize)(?:\s*[,:\-–]\s*|\s+)"),
    re.compile(
        r"(?is)^\s*(?:i\s+(?:have|'ve)\s+)?(?:rewritten|translated|converted|summarized)\s+"
        r"(?:the\s+)?(?:text|input|message)\s+(?:into|to)\s+(?:a\s+)?(?:more\s+)?"
        r"conversational(?:\s+form|\s+tone)?(?:\s*[:\-–]\s*|\s+)"
    ),
)
SUMMARY_META_SENTENCE_EXACT: set[str] = {
    "summary",
    "recap",
    "in summary",
    "to summarize",
    "here's a summary",
    "here is a summary",
    "here's a quick summary",
    "here is a quick summary",
    "here's a concise summary",
    "here is a concise summary",
    "this is a summary",
    "the following is a summary",
    "here's a summary in conversational form",
    "here is a summary in conversational form",
}
SUMMARY_META_SENTENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?is)^(?:here(?:'s| is)|this is|the following is)\s+"
        r"(?:a\s+)?(?:brief|quick|short|concise)?\s*(?:summary|recap)"
        r"(?:\s+(?:in|as)\s+(?:a\s+)?(?:more\s+)?conversational(?:\s+form)?)?"
        r"\s*[:;,\-.!?–—]*\s*$"
    ),
    re.compile(r"(?is)^(?:summary|recap|in summary|to summarize)\s*[:;,\-.!?–—]*\s*$"),
    re.compile(
        r"(?is)^(?:i\s+(?:have|'ve)\s+)?(?:rewritten|translated|converted|summarized)\s+"
        r"(?:the\s+)?(?:text|input|message)"
        r"(?:\s+(?:into|to)\s+(?:a\s+)?(?:more\s+)?conversational(?:\s+form|\s+tone)?)?"
        r"\s*[:;,\-.!?–—]*\s*$"
    ),
)


@lru_cache(maxsize=1)
def load_summary_instructions() -> str:
    """Load speech summarization instructions from packaged prompt text."""

    try:
        prompt_text = files("koko_cli").joinpath(SUMMARY_PROMPT_RESOURCE).read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise SummarizationError(f"Summarization prompt resource is missing: {SUMMARY_PROMPT_RESOURCE}") from error

    normalized = prompt_text.strip()
    if not normalized:
        raise SummarizationError("Summarization prompt resource is empty.")

    return normalized


@lru_cache(maxsize=1)
def load_pydantic_ai_components() -> tuple[type[Any], type[Any], type[Any], type[Any]]:
    """Load pydantic-ai classes lazily so base CLI still works without summarize deps."""

    try:
        from pydantic_ai import Agent
        from pydantic_ai.models import ModelSettings
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
    except ImportError as error:
        raise SummarizationError(
            "Summarization requires the optional dependency 'pydantic-ai' in the runtime environment."
        ) from error

    return Agent, ModelSettings, OpenAIChatModel, OpenAIProvider


def summarize_for_speech(
    *,
    text: str,
    base_url: str,
    model: str,
    api_key: str,
    timeout_seconds: float,
    max_input_chars: int,
) -> str:
    """Summarize raw text into concise spoken conversational output."""

    prepared_text = truncate_summary_input(text=text, max_input_chars=max_input_chars)
    resolved_api_key = resolve_api_key(base_url=base_url, api_key=api_key)

    Agent, ModelSettings, OpenAIChatModel, OpenAIProvider = load_pydantic_ai_components()

    provider = OpenAIProvider(base_url=base_url, api_key=resolved_api_key)
    chat_model = OpenAIChatModel(model_name=model, provider=provider)
    agent = Agent(model=chat_model, output_type=str, instructions=load_summary_instructions(), retries=0)

    try:
        result = agent.run_sync(prepared_text, model_settings=ModelSettings(timeout=timeout_seconds))
    except Exception as error:
        raise SummarizationError(f"Summarization request failed: {error}") from error

    summary = normalize_summary_output(result.output)
    if not summary:
        raise SummarizationError("Summarization returned empty text.")

    return summary


def truncate_summary_input(text: str, max_input_chars: int) -> str:
    """Limit input size before sending text to the LLM."""

    normalized = text.strip()
    if len(normalized) <= max_input_chars:
        return normalized

    note = "\n\n[Input truncated before summarization.]"
    budget = max_input_chars - len(note)
    if budget <= 0:
        return normalized[:max_input_chars].rstrip()

    truncated = normalized[:budget].rstrip()
    return f"{truncated}{note}"


def normalize_summary_output(output: str) -> str:
    """Normalize model output into plain conversational text."""

    cleaned = output.replace("```", " ").strip()
    if not cleaned:
        return ""

    normalized_lines: list[str] = []
    for line in cleaned.splitlines():
        candidate = line.strip()
        if not candidate:
            continue

        candidate = re.sub(r"^\s*[-*#]+\s*", "", candidate)
        candidate = re.sub(r"^\s*\d+[.)]\s*", "", candidate)
        normalized_lines.append(candidate)

    normalized = " ".join(normalized_lines).strip()
    if not normalized:
        return ""

    normalized = strip_summary_meta_prefixes(normalized)
    normalized = strip_summary_meta_sentences(normalized)
    normalized = clamp_summary_sentences(normalized, max_sentences=MAX_SUMMARY_SENTENCES)
    return normalized.strip()


def strip_summary_meta_prefixes(text: str) -> str:
    """Remove leading summary meta-commentary before returning spoken text."""

    normalized = text.strip()
    for pattern in SUMMARY_META_PREFIX_PATTERNS:
        normalized = pattern.sub("", normalized, count=1).strip()
    return normalized


def strip_summary_meta_sentences(text: str) -> str:
    """Drop sentence fragments that only describe the act of summarizing."""

    sentences = split_sentences(text)
    if not sentences:
        return text.strip()

    filtered_sentences = [sentence for sentence in sentences if not is_summary_meta_sentence(sentence)]
    if not filtered_sentences:
        return ""

    return " ".join(filtered_sentences).strip()


def is_summary_meta_sentence(sentence: str) -> bool:
    """Return True when sentence content is summarization meta-commentary only."""

    normalized = re.sub(r"\s+", " ", sentence.strip().lower())
    normalized = normalized.strip(" \t\r\n:;,.!?-–—")
    if not normalized:
        return False

    if normalized in SUMMARY_META_SENTENCE_EXACT:
        return True

    return any(pattern.fullmatch(normalized) is not None for pattern in SUMMARY_META_SENTENCE_PATTERNS)


def clamp_summary_sentences(text: str, *, max_sentences: int) -> str:
    """Limit summary output to a maximum number of sentence-like chunks."""

    sentences = split_sentences(text)
    if not sentences:
        return text.strip()

    return " ".join(sentences[:max_sentences]).strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentence-like chunks for post-processing."""

    return [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(text.strip()) if part.strip()]


def is_local_llm_base_url(base_url: str) -> bool:
    """Return True when the model endpoint resolves to a local host."""

    parse_target = base_url if "://" in base_url else f"http://{base_url}"
    parsed = urlparse(parse_target)
    hostname = (parsed.hostname or "").strip("[]").lower()
    return hostname in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def resolve_api_key(base_url: str, api_key: str) -> str | None:
    """Resolve API key value for OpenAI-compatible calls."""

    stripped = api_key.strip()
    if stripped:
        return stripped

    if is_local_llm_base_url(base_url):
        return "local"

    return None
