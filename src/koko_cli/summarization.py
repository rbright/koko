from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from typing import Any
from urllib.parse import urlparse

from .errors import SummarizationError

SUMMARY_PROMPT_RESOURCE = "prompts/summarize_for_speech.txt"


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
    except Exception as error:  # noqa: BLE001
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

    truncated = normalized[:max_input_chars].rstrip()
    return f"{truncated}\n\n[Input truncated before summarization.]"


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

    return " ".join(normalized_lines).strip()


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
