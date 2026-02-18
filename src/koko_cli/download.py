from __future__ import annotations

import argparse
import sys
from pathlib import Path

from huggingface_hub import snapshot_download
from pydantic import ValidationError

from .errors import UsageError
from .models import DownloadCommand, format_validation_error
from .settings import SettingsSnapshot, get_settings, snapshot_settings


def normalize_voice_name(value: str) -> str:
    """Normalize a voice token to a bare voice id (without path/ext)."""

    token = value.strip()
    if not token:
        raise UsageError("Voice names cannot be empty.")

    if token.endswith(".pt"):
        token = Path(token).name.removesuffix(".pt")

    if token.startswith("voices/"):
        token = token.removeprefix("voices/")

    if not token:
        raise UsageError(f"Invalid voice token: {value!r}")

    return token


def build_allow_patterns(voices: str) -> list[str]:
    """Build Hugging Face snapshot patterns for requested assets."""

    base_patterns = ["config.json", "kokoro-v1_0.pth"]

    if voices.strip().lower() == "all":
        return [*base_patterns, "voices/*.pt"]

    voice_patterns: list[str] = []
    for token in voices.split(","):
        voice_name = normalize_voice_name(token)
        voice_patterns.append(f"voices/{voice_name}.pt")

    ordered = dict.fromkeys([*base_patterns, *sorted(voice_patterns)])
    return list(ordered)


def download_model_assets(model_dir: Path, repo_id: str, voices: str) -> Path:
    """Download Kokoro model artifacts into a local directory."""

    target = model_dir.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    allow_patterns = build_allow_patterns(voices=voices)

    snapshot_download(
        repo_id=repo_id,
        allow_patterns=allow_patterns,
        local_dir=target,
    )

    return target


def parse_args(argv: list[str] | None = None, settings: SettingsSnapshot | None = None) -> argparse.Namespace:
    """Parse CLI args for the model downloader."""

    active_settings = settings or snapshot_settings(get_settings())

    parser = argparse.ArgumentParser(
        prog="koko-download-model",
        description="Download Kokoro-82M model assets for local offline use.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=active_settings.default_model_dir,
        help=f"Destination directory (default: {active_settings.default_model_dir})",
    )
    parser.add_argument(
        "--repo-id",
        default=active_settings.repo_id,
        help=f"Hugging Face model repo ID (default: {active_settings.repo_id})",
    )
    parser.add_argument(
        "--voices",
        default="all",
        help="Voice ids to download: 'all' or comma-separated list (e.g. af_heart,bf_emma)",
    )
    return parser.parse_args(argv)


def validate_download_namespace(namespace: argparse.Namespace) -> DownloadCommand:
    """Validate parsed downloader arguments."""

    try:
        return DownloadCommand.model_validate(vars(namespace))
    except ValidationError as error:
        raise UsageError(format_validation_error(error)) from error


def main(argv: list[str] | None = None) -> int:
    """Entrypoint for the model downloader command."""

    try:
        settings = snapshot_settings(get_settings())
        namespace = parse_args(argv, settings=settings)
        command = validate_download_namespace(namespace)

        output_dir = download_model_assets(
            model_dir=command.model_dir,
            repo_id=command.repo_id,
            voices=command.voices,
        )
        print(output_dir)
        return 0
    except UsageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except ValidationError as error:
        print(f"error: {format_validation_error(error)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
