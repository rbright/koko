from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MAX_INPUT_CHARS,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    DEFAULT_LOCAL_MODEL_DIR,
    DEFAULT_REPO_ID,
    DEFAULT_SUMMARIZE,
    DEFAULT_VOICE,
)


class KokoSettings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

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
