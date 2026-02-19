from __future__ import annotations

import argparse
import os
import wave
from pathlib import Path

import pytest
import torch

from koko_cli import cli, constants, offline, service, synthesis, text
from koko_cli import settings as settings_module
from koko_cli.errors import SummarizationError, UsageError
from koko_cli.settings import SettingsSnapshot


def make_settings(default_model_dir: Path) -> SettingsSnapshot:
    return SettingsSnapshot(
        repo_id=constants.DEFAULT_REPO_ID,
        default_voice=constants.DEFAULT_VOICE,
        offline=True,
        model_dir=None,
        default_model_dir=default_model_dir,
        summarize=constants.DEFAULT_SUMMARIZE,
        llm_base_url=constants.DEFAULT_LLM_BASE_URL,
        llm_model=constants.DEFAULT_LLM_MODEL,
        llm_api_key="",
        llm_timeout_seconds=constants.DEFAULT_LLM_TIMEOUT_SECONDS,
        llm_max_input_chars=constants.DEFAULT_LLM_MAX_INPUT_CHARS,
    )


def test_resolve_lang_code_uses_voice_prefix_by_default() -> None:
    assert text.resolve_lang_code(lang_code=None, voice="af_heart") == "a"
    assert text.resolve_lang_code(lang_code=None, voice="bf_emma") == "b"
    assert text.resolve_lang_code(lang_code=None, voice="jm_kumo") == "j"


def test_resolve_lang_code_accepts_aliases() -> None:
    assert text.resolve_lang_code(lang_code="en-us", voice="af_heart") == "a"
    assert text.resolve_lang_code(lang_code="pt-br", voice="af_heart") == "p"


def test_resolve_lang_code_rejects_unknown_value() -> None:
    with pytest.raises(UsageError, match="Unsupported language code"):
        text.resolve_lang_code(lang_code="xx", voice="af_heart")


def test_pipeline_lang_code_uses_espeak_safe_mapping_for_english() -> None:
    assert synthesis.pipeline_lang_code("a") == "e"
    assert synthesis.pipeline_lang_code("b") == "e"
    assert synthesis.pipeline_lang_code("j") == "j"


def test_resolve_model_dir_requires_local_assets_in_offline_mode(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="Offline mode requires local model assets"):
        offline.resolve_model_dir(
            model_dir=None,
            offline=True,
            require_local_assets=True,
            default_local_model_dir=tmp_path / "missing-model-dir",
        )


def test_resolve_text_joins_message_parts() -> None:
    resolved_text = text.resolve_text(message_parts=["hello", "there"], input_file=None)
    assert resolved_text == "hello there"


def test_resolve_text_rejects_conflicting_sources(tmp_path: Path) -> None:
    source_path = tmp_path / "message.txt"
    source_path.write_text("hello", encoding="utf-8")

    with pytest.raises(UsageError, match="either message args or --input-file"):
        text.resolve_text(message_parts=["hello"], input_file=str(source_path))


def test_min_256_int_validator() -> None:
    assert text.min_256_int("256") == 256

    with pytest.raises(argparse.ArgumentTypeError, match=">= 256"):
        text.min_256_int("255")


def test_configure_offline_environment_sets_offline_flags() -> None:
    offline.configure_offline_environment(True)

    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_local_voices_are_discovered_from_model_dir(tmp_path: Path) -> None:
    model_dir = tmp_path / "kokoro"
    voices_dir = model_dir / "voices"
    voices_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "kokoro-v1_0.pth").write_bytes(b"model")
    (voices_dir / "af_heart.pt").write_bytes(b"voice")
    (voices_dir / "bf_emma.pt").write_bytes(b"voice")

    voices = offline.list_available_voices(repo_id=constants.DEFAULT_REPO_ID, model_dir=model_dir)

    assert voices == ["af_heart", "bf_emma"]


def test_main_generates_wav_without_playback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "speech.wav"
    dummy_pipeline = object()

    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(default_model_dir=tmp_path / "missing-model-dir"))

    def fake_build_pipeline(lang_code: str, repo_id: str, device: str | None, model: object = True) -> object:
        assert lang_code == "e"
        assert repo_id == constants.DEFAULT_REPO_ID
        assert device is None
        assert model is True
        return dummy_pipeline

    def fake_synthesize_waveform(
        pipeline: object,
        text: str,
        voice: str,
        speed: float,
        split_pattern: str,
        lang_code: str,
    ) -> torch.Tensor:
        assert pipeline is dummy_pipeline
        assert text == "hello from koko"
        assert voice == constants.DEFAULT_VOICE
        assert speed == 1.0
        assert split_pattern == r"\n+"
        assert lang_code == "a"
        return torch.tensor([0.0, 0.25, -0.25, 0.0], dtype=torch.float32)

    monkeypatch.setattr(service, "build_pipeline", fake_build_pipeline)
    monkeypatch.setattr(service, "synthesize_waveform", fake_synthesize_waveform)

    exit_code = cli.main(["--no-offline", "--no-play", "--output", str(output_path), "hello", "from", "koko"])

    assert exit_code == 0
    assert output_path.exists()

    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getframerate() == constants.DEFAULT_SAMPLE_RATE
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2

    assert capsys.readouterr().out.strip() == str(output_path.resolve())


def test_main_summarize_transforms_text_before_synthesis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "speech-summary.wav"
    dummy_pipeline = object()

    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(default_model_dir=tmp_path / "missing-model-dir"))
    monkeypatch.setattr(service, "summarize_for_speech", lambda **kwargs: "Completed successfully.")

    def fake_build_pipeline(lang_code: str, repo_id: str, device: str | None, model: object = True) -> object:
        return dummy_pipeline

    def fake_synthesize_waveform(
        pipeline: object,
        text: str,
        voice: str,
        speed: float,
        split_pattern: str,
        lang_code: str,
    ) -> torch.Tensor:
        assert pipeline is dummy_pipeline
        assert text == "Completed successfully."
        return torch.tensor([0.0, 0.25, -0.25, 0.0], dtype=torch.float32)

    monkeypatch.setattr(service, "build_pipeline", fake_build_pipeline)
    monkeypatch.setattr(service, "synthesize_waveform", fake_synthesize_waveform)

    exit_code = cli.main(
        [
            "--no-offline",
            "--summarize",
            "--no-play",
            "--output",
            str(output_path),
            "raw",
            "markdown",
            "input",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert capsys.readouterr().out.strip() == str(output_path.resolve())


def test_main_summarize_requires_non_blank_model(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--summarize", "--llm-model", "", "hello"])

    assert exit_code == 2
    assert "--summarize requires --llm-model" in capsys.readouterr().err


def test_main_summarize_failure_is_noop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "speech-summary-fail.wav"

    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(default_model_dir=tmp_path / "missing-model-dir"))

    def fail_summarize(**kwargs: object) -> str:
        raise SummarizationError("summarization failed")

    monkeypatch.setattr(service, "summarize_for_speech", fail_summarize)

    def should_not_build_pipeline(**kwargs: object) -> object:
        raise AssertionError("pipeline should not build on summarization failure")

    monkeypatch.setattr(service, "build_pipeline", should_not_build_pipeline)

    exit_code = cli.main(
        [
            "--no-offline",
            "--summarize",
            "--no-play",
            "--output",
            str(output_path),
            "raw",
            "markdown",
            "input",
        ]
    )

    assert exit_code == 1
    assert not output_path.exists()
    assert "summarization failed" in capsys.readouterr().err


def test_main_supports_voice_listing_via_question_mark(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(default_model_dir=tmp_path / "missing-model-dir"))
    monkeypatch.setattr(service, "list_available_voices", lambda repo_id, model_dir: ["af_heart", "bf_emma"])

    exit_code = cli.main(["-v", "?"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip().splitlines() == ["af_heart", "bf_emma"]


def test_main_requires_output_when_no_play(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--no-play", "hello"])

    assert exit_code == 2
    assert "--no-play requires --output" in capsys.readouterr().err


def test_offline_flag_requires_local_assets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(default_model_dir=tmp_path / "missing-model-dir"))

    exit_code = cli.main(["--offline", "--no-play", "--output", "/tmp/koko-offline.wav", "hello"])

    assert exit_code == 2
    assert "Offline mode requires local model assets" in capsys.readouterr().err


def test_offline_summarize_requires_local_llm_base_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(default_model_dir=tmp_path / "missing-model-dir"))
    output_path = tmp_path / "koko-offline-summary.wav"

    exit_code = cli.main(
        [
            "--summarize",
            "--llm-base-url",
            "https://api.example.com/v1",
            "--no-play",
            "--output",
            str(output_path),
            "hello",
        ]
    )

    assert exit_code == 2
    assert "Offline mode with --summarize requires a local --llm-base-url" in capsys.readouterr().err


@pytest.fixture(autouse=True)
def clear_koko_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_module.get_settings.cache_clear()
    monkeypatch.delenv("KOKO_MODEL_DIR", raising=False)
    monkeypatch.delenv("KOKO_SUMMARIZE", raising=False)
    monkeypatch.delenv("KOKO_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("KOKO_LLM_MODEL", raising=False)
    monkeypatch.delenv("KOKO_LLM_API_KEY", raising=False)
    monkeypatch.delenv("KOKO_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("KOKO_LLM_MAX_INPUT_CHARS", raising=False)
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    assert os.environ.get("KOKO_MODEL_DIR") is None
