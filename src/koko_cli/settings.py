from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import DEFAULT_LOCAL_MODEL_DIR, DEFAULT_REPO_ID, DEFAULT_VOICE


class KokoSettings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="koko_", extra="ignore")

    repo_id: str = Field(default=DEFAULT_REPO_ID)
    default_voice: str = Field(default=DEFAULT_VOICE)
    offline: bool = Field(default=True)
    model_dir: Path | None = Field(default=None)
    default_model_dir: Path = Field(default=DEFAULT_LOCAL_MODEL_DIR)


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


def snapshot_settings(settings: KokoSettings) -> SettingsSnapshot:
    """Return a concrete settings snapshot for CLI wiring."""

    return SettingsSnapshot.model_validate(settings.model_dump())
