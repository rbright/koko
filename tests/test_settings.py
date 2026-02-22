from __future__ import annotations

from pathlib import Path

import pytest

from koko_cli import settings as settings_module
from koko_cli.errors import UsageError


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_module.get_settings.cache_clear()
    monkeypatch.delenv("KOKO_CONFIG_FILE", raising=False)
    monkeypatch.delenv("KOKO_LLM_MODEL", raising=False)
    monkeypatch.delenv("KOKO_SUMMARIZE", raising=False)


def test_load_config_file_settings_parses_jsonc_comments_and_trailing_commas(tmp_path: Path) -> None:
    config_path = tmp_path / "config.jsonc"
    config_path.write_text(
        """
        {
          // prefer a smaller local model
          "llm": {
            "model": "Mistral-7B-Instruct-v0.3-Q6_K",
            "timeout-seconds": 7,
          },
          "summarize": true,
        }
        """,
        encoding="utf-8",
    )

    loaded = settings_module.load_config_file_settings(config_path)

    assert loaded["llm_model"] == "Mistral-7B-Instruct-v0.3-Q6_K"
    assert loaded["llm_timeout_seconds"] == 7
    assert loaded["summarize"] is True


def test_get_settings_reads_default_config_from_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    config_path = tmp_path / ".config" / "koko" / "config.jsonc"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"llm_model": "Mistral-7B-Instruct-v0.3-Q6_K"}', encoding="utf-8")

    resolved = settings_module.get_settings()

    assert resolved.llm_model == "Mistral-7B-Instruct-v0.3-Q6_K"


def test_environment_overrides_jsonc_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    config_path = tmp_path / ".config" / "koko" / "config.jsonc"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"llm_model": "Mistral-7B-Instruct-v0.3-Q6_K"}', encoding="utf-8")

    monkeypatch.setenv("KOKO_LLM_MODEL", "override-from-env")

    resolved = settings_module.get_settings()

    assert resolved.llm_model == "override-from-env"


def test_get_settings_uses_koko_config_file_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    override_path = tmp_path / "custom-koko-config.jsonc"
    override_path.write_text('{"llm_model": "model-from-custom-file"}', encoding="utf-8")

    monkeypatch.setenv("KOKO_CONFIG_FILE", str(override_path))

    resolved = settings_module.get_settings()

    assert resolved.llm_model == "model-from-custom-file"


def test_load_config_file_settings_rejects_invalid_json(tmp_path: Path) -> None:
    config_path = tmp_path / "config.jsonc"
    config_path.write_text('{"llm_model": "oops",', encoding="utf-8")

    with pytest.raises(UsageError, match="Invalid JSON in config file"):
        settings_module.load_config_file_settings(config_path)
