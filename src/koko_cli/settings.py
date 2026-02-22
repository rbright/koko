from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MAX_INPUT_CHARS,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    DEFAULT_LOCAL_MODEL_DIR,
    DEFAULT_REPO_ID,
    DEFAULT_SUMMARIZE,
    DEFAULT_VOICE,
)
from .errors import UsageError

CONFIG_FILE_ENV_VAR = "KOKO_CONFIG_FILE"


def resolve_config_file_path() -> Path:
    """Resolve the optional JSONC config location."""

    configured_path = os.environ.get(CONFIG_FILE_ENV_VAR, "").strip()
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_CONFIG_FILE.expanduser()


def strip_jsonc_comments(raw: str) -> str:
    """Strip // and /* */ comments from a JSONC string."""

    result: list[str] = []
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False

    index = 0
    while index < len(raw):
        current = raw[index]
        next_char = raw[index + 1] if index + 1 < len(raw) else ""

        if in_line_comment:
            if current == "\n":
                in_line_comment = False
                result.append(current)
            index += 1
            continue

        if in_block_comment:
            if current == "*" and next_char == "/":
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if in_string:
            result.append(current)
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                in_string = False
            index += 1
            continue

        if current == '"':
            in_string = True
            result.append(current)
            index += 1
            continue

        if current == "/" and next_char == "/":
            in_line_comment = True
            index += 2
            continue

        if current == "/" and next_char == "*":
            in_block_comment = True
            index += 2
            continue

        result.append(current)
        index += 1

    return "".join(result)


def strip_jsonc_trailing_commas(raw: str) -> str:
    """Remove trailing commas before } or ] while preserving string content."""

    result: list[str] = []
    in_string = False
    escaped = False

    index = 0
    while index < len(raw):
        current = raw[index]

        if in_string:
            result.append(current)
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                in_string = False
            index += 1
            continue

        if current == '"':
            in_string = True
            result.append(current)
            index += 1
            continue

        if current == ",":
            lookahead = index + 1
            while lookahead < len(raw) and raw[lookahead].isspace():
                lookahead += 1

            if lookahead < len(raw) and raw[lookahead] in {"]", "}"}:
                index += 1
                continue

        result.append(current)
        index += 1

    return "".join(result)


def parse_jsonc_object(raw: str, *, source: Path) -> dict[str, Any]:
    """Parse JSONC text into a dictionary."""

    without_comments = strip_jsonc_comments(raw)
    normalized = strip_jsonc_trailing_commas(without_comments)

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as error:  # pragma: no cover - surfaced with precise message
        raise UsageError(
            f"Invalid JSON in config file '{source}': {error.msg} (line {error.lineno}, column {error.colno})."
        ) from error

    if not isinstance(parsed, dict):
        raise UsageError(f"Config file '{source}' must contain a top-level JSON object.")

    return parsed


def normalize_config_keys(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize config keys to setting field names."""

    normalized: dict[str, Any] = {str(key).replace("-", "_"): value for key, value in raw.items() if key != "llm"}

    llm_section = raw.get("llm")
    if isinstance(llm_section, dict):
        for key, value in llm_section.items():
            normalized_key = f"llm_{str(key).replace('-', '_')}"
            normalized.setdefault(normalized_key, value)

    return normalized


def load_config_file_settings(path: Path) -> dict[str, Any]:
    """Load optional settings from a JSONC config file."""

    if not path.exists():
        return {}

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise UsageError(f"Failed to read config file '{path}': {error}") from error

    parsed = parse_jsonc_object(raw, source=path)
    return normalize_config_keys(parsed)


class KokoSettings(BaseSettings):
    """Runtime configuration loaded from env vars and optional JSONC config file."""

    model_config = SettingsConfigDict(env_prefix="koko_", extra="ignore")

    repo_id: str = Field(default=DEFAULT_REPO_ID)
    default_voice: str = Field(default=DEFAULT_VOICE)
    offline: bool = Field(default=True)
    model_dir: Path | None = Field(default=None)
    default_model_dir: Path = Field(default=DEFAULT_LOCAL_MODEL_DIR)
    summarize: bool = Field(default=DEFAULT_SUMMARIZE)
    llm_base_url: str = Field(default=DEFAULT_LLM_BASE_URL)
    llm_model: str = Field(default=DEFAULT_LLM_MODEL)
    llm_api_key: str = Field(default="")
    llm_timeout_seconds: float = Field(default=DEFAULT_LLM_TIMEOUT_SECONDS, gt=0)
    llm_max_input_chars: int = Field(default=DEFAULT_LLM_MAX_INPUT_CHARS, ge=256)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Load precedence: init args > env vars > JSONC config > defaults."""

        _ = settings_cls
        return (
            init_settings,
            env_settings,
            cls._config_file_settings_source,
            dotenv_settings,
            file_secret_settings,
        )

    @staticmethod
    def _config_file_settings_source() -> dict[str, Any]:
        return load_config_file_settings(resolve_config_file_path())


@lru_cache(maxsize=1)
def get_settings() -> KokoSettings:
    """Get cached application settings."""

    return KokoSettings()


class SettingsSnapshot(BaseModel):
    """Serializable snapshot used by CLI argument defaults."""

    repo_id: str
    default_voice: str
    offline: bool
    model_dir: Path | None
    default_model_dir: Path
    summarize: bool
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    llm_timeout_seconds: float
    llm_max_input_chars: int


def snapshot_settings(settings: KokoSettings) -> SettingsSnapshot:
    """Return a concrete settings snapshot for CLI wiring."""

    return SettingsSnapshot.model_validate(settings.model_dump())
