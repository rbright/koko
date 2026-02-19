from __future__ import annotations

import pytest

from koko_cli import summarization
from koko_cli.errors import SummarizationError


def test_load_summary_instructions_comes_from_prompt_file() -> None:
    instructions = summarization.load_summary_instructions()

    assert "arbitrary text" in instructions
    assert "technical assistant output" not in instructions


def test_is_local_llm_base_url_detects_loopback() -> None:
    assert summarization.is_local_llm_base_url("http://127.0.0.1:11434/v1")
    assert summarization.is_local_llm_base_url("http://localhost:11434/v1")
    assert summarization.is_local_llm_base_url("127.0.0.1:11434/v1")
    assert summarization.is_local_llm_base_url("http://0.0.0.0:11434/v1")
    assert summarization.is_local_llm_base_url("http://[::1]:11434/v1")
    assert not summarization.is_local_llm_base_url("https://api.openai.com/v1")


def test_resolve_api_key_uses_local_sentinel_when_blank() -> None:
    assert summarization.resolve_api_key("http://127.0.0.1:11434/v1", "") == "local"
    assert summarization.resolve_api_key("https://api.openai.com/v1", "") is None
    assert summarization.resolve_api_key("https://api.openai.com/v1", "secret") == "secret"


def test_truncate_summary_input_limits_size() -> None:
    raw = "x" * 256
    result = summarization.truncate_summary_input(raw, max_input_chars=64)

    assert len(result) <= 64
    assert result.endswith("[Input truncated before summarization.]")


def test_truncate_summary_input_omits_notice_when_cap_is_too_small() -> None:
    raw = "x" * 32
    result = summarization.truncate_summary_input(raw, max_input_chars=8)

    assert result == "x" * 8
    assert len(result) <= 8
    assert "Input truncated before summarization" not in result


def test_normalize_summary_output_strips_markdown_artifacts() -> None:
    raw = "# Done\n- Updated CI smoke path\n1. Added badge"

    assert summarization.normalize_summary_output(raw) == "Done Updated CI smoke path Added badge"


def test_summarize_for_speech_returns_normalized_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResult:
        output = "- All checks passed."

    class FakeAgent:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def run_sync(self, *args: object, **kwargs: object) -> FakeResult:
            return FakeResult()

    class FakeModelSettings(dict):
        def __init__(self, timeout: float) -> None:
            super().__init__(timeout=timeout)

    class FakeOpenAIChatModel:
        def __init__(self, model_name: str, provider: object) -> None:
            self.model_name = model_name
            self.provider = provider

    class FakeOpenAIProvider:
        def __init__(self, base_url: str, api_key: str | None) -> None:
            self.base_url = base_url
            self.api_key = api_key

    monkeypatch.setattr(
        summarization,
        "load_pydantic_ai_components",
        lambda: (FakeAgent, FakeModelSettings, FakeOpenAIChatModel, FakeOpenAIProvider),
    )

    result = summarization.summarize_for_speech(
        text="raw markdown input",
        base_url="http://127.0.0.1:11434/v1",
        model="mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q6_K",
        api_key="",
        timeout_seconds=5.0,
        max_input_chars=1000,
    )

    assert result == "All checks passed."


def test_summarize_for_speech_raises_when_model_call_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAgent:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def run_sync(self, *args: object, **kwargs: object) -> str:
            raise RuntimeError("upstream error")

    class FakeModelSettings(dict):
        def __init__(self, timeout: float) -> None:
            super().__init__(timeout=timeout)

    class FakeOpenAIChatModel:
        def __init__(self, model_name: str, provider: object) -> None:
            self.model_name = model_name
            self.provider = provider

    class FakeOpenAIProvider:
        def __init__(self, base_url: str, api_key: str | None) -> None:
            self.base_url = base_url
            self.api_key = api_key

    monkeypatch.setattr(
        summarization,
        "load_pydantic_ai_components",
        lambda: (FakeAgent, FakeModelSettings, FakeOpenAIChatModel, FakeOpenAIProvider),
    )

    with pytest.raises(SummarizationError, match="Summarization request failed"):
        summarization.summarize_for_speech(
            text="raw markdown input",
            base_url="http://127.0.0.1:11434/v1",
            model="mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q6_K",
            api_key="",
            timeout_seconds=5.0,
            max_input_chars=1000,
        )
