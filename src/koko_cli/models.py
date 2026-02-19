from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .constants import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MAX_INPUT_CHARS, DEFAULT_LLM_MODEL, DEFAULT_LLM_TIMEOUT_SECONDS


class VoicesCommand(BaseModel):
    """Validated inputs for `koko voices`."""

    model_config = ConfigDict(extra="forbid")

    repo_id: str = Field(min_length=1)
    model_dir: Path | None = None
    offline: bool = True


class SpeakCommand(BaseModel):
    """Validated inputs for `koko` speak flow."""

    model_config = ConfigDict(extra="forbid")

    message: list[str] = Field(default_factory=list)
    voice: str
    lang_code: str | None = None
    speed: float = Field(gt=0)
    output: Path | None = None
    input_file: str | None = None
    summarize: bool = False
    llm_base_url: str = Field(default=DEFAULT_LLM_BASE_URL)
    llm_model: str = Field(default=DEFAULT_LLM_MODEL)
    llm_api_key: str = ""
    llm_timeout_seconds: float = Field(default=DEFAULT_LLM_TIMEOUT_SECONDS, gt=0)
    llm_max_input_chars: int = Field(default=DEFAULT_LLM_MAX_INPUT_CHARS, ge=256)
    repo_id: str = Field(min_length=1)
    model_dir: Path | None = None
    offline: bool = True
    device: Literal["auto", "cpu", "cuda"] = "auto"
    split_pattern: str = r"\n+"
    play: bool = True
    list_voices: bool = False

    @field_validator("voice")
    @classmethod
    def validate_voice_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("voice cannot be blank")
        return stripped

    @model_validator(mode="after")
    def validate_audio_destination(self) -> SpeakCommand:
        if not self.play and self.output is None:
            raise ValueError("--no-play requires --output so the audio has a destination.")

        if self.summarize:
            if not self.llm_base_url.strip():
                raise ValueError("--summarize requires --llm-base-url to be non-blank.")
            if not self.llm_model.strip():
                raise ValueError("--summarize requires --llm-model to be non-blank.")

        return self


class DownloadCommand(BaseModel):
    """Validated inputs for `koko-download-model`."""

    model_config = ConfigDict(extra="forbid")

    model_dir: Path
    repo_id: str = Field(min_length=1)
    voices: str

    @field_validator("voices")
    @classmethod
    def validate_voices_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("voices cannot be blank")
        return stripped


def format_validation_error(error: ValidationError) -> str:
    """Render a concise validation error string for CLI usage output."""

    first = error.errors()[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    message = first.get("msg", "invalid input")

    if location:
        return f"{location}: {message}"
    return message
