from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    DEFAULT_LOCAL_MODEL_DIR,
    FALLBACK_VOICES,
    LOCAL_CONFIG_FILE,
    LOCAL_MODEL_FILE,
    LOCAL_VOICES_DIR,
)
from .errors import UsageError


@dataclass(frozen=True)
class LocalAssets:
    """Resolved local Kokoro model artifacts."""

    model_dir: Path
    config_path: Path
    model_path: Path
    voices_dir: Path


def configure_offline_environment(offline: bool) -> None:
    """Set offline env flags to prevent accidental outbound requests."""

    if not offline:
        return

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


def resolve_model_dir(
    model_dir: Path | None,
    offline: bool,
    require_local_assets: bool,
    default_local_model_dir: Path = DEFAULT_LOCAL_MODEL_DIR,
) -> Path | None:
    """Resolve local model directory from args, env, or default location."""

    if model_dir is not None:
        return model_dir.expanduser().resolve()

    env_dir = os.environ.get("KOKO_MODEL_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    default_dir = default_local_model_dir.expanduser().resolve()
    if default_dir.exists():
        return default_dir

    if offline and require_local_assets:
        raise UsageError("Offline mode requires local model assets. Pass --model-dir <path> or set KOKO_MODEL_DIR.")

    return None


def resolve_local_assets(model_dir: Path) -> LocalAssets:
    """Validate and return local Kokoro artifact paths."""

    config_path = model_dir / LOCAL_CONFIG_FILE
    model_path = model_dir / LOCAL_MODEL_FILE
    voices_dir = model_dir / LOCAL_VOICES_DIR

    missing_paths: list[Path] = [path for path in (config_path, model_path, voices_dir) if not path.exists()]
    if missing_paths:
        formatted = ", ".join(str(path) for path in missing_paths)
        raise UsageError(
            "Local model directory is missing required assets: "
            f"{formatted}. Expected files: {LOCAL_CONFIG_FILE}, {LOCAL_MODEL_FILE}, and {LOCAL_VOICES_DIR}/"
        )

    if not voices_dir.is_dir():
        raise UsageError(f"Expected voices directory at '{voices_dir}'.")

    return LocalAssets(
        model_dir=model_dir,
        config_path=config_path,
        model_path=model_path,
        voices_dir=voices_dir,
    )


def resolve_voice_source(voice: str, voices_dir: Path) -> str:
    """Resolve a voice string into local `.pt` path(s)."""

    voice_parts = [part.strip() for part in voice.split(",") if part.strip()]
    if not voice_parts:
        raise UsageError("Voice cannot be empty.")

    resolved_parts: list[str] = []

    for voice_part in voice_parts:
        if voice_part.endswith(".pt"):
            voice_path = Path(voice_part).expanduser()
            if not voice_path.is_absolute():
                voice_path = Path.cwd() / voice_path
        else:
            voice_path = voices_dir / f"{voice_part}.pt"

        if not voice_path.exists():
            raise UsageError(f"Local voice file not found: {voice_path}")

        resolved_parts.append(str(voice_path))

    return ",".join(resolved_parts)


def list_available_voices(repo_id: str, model_dir: Path | None) -> list[str]:
    """List available voices from local assets or built-in fallback data."""

    _ = repo_id  # reserved for future parity with remote model repo selection

    if model_dir is not None:
        assets = resolve_local_assets(model_dir)
        local_voices = sorted(path.stem for path in assets.voices_dir.glob("*.pt"))
        if local_voices:
            return local_voices

    return list(FALLBACK_VOICES)
