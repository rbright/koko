from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from .errors import UsageError
from .models import SpeakCommand, VoicesCommand, format_validation_error
from .settings import SettingsSnapshot
from .text import positive_float, positive_int


def split_command(argv: Sequence[str]) -> tuple[str, list[str]]:
    """Allow `koko`, `koko speak`, and `koko voices` command shapes."""

    if argv and argv[0] in {"speak", "voices"}:
        return argv[0], list(argv[1:])
    return "speak", list(argv)


def parse_voices_args(argv: Sequence[str], settings: SettingsSnapshot) -> argparse.Namespace:
    """Parse args for `koko voices`."""

    parser = argparse.ArgumentParser(prog="koko voices", description="List Kokoro voice IDs")
    parser.add_argument(
        "--repo-id",
        default=settings.repo_id,
        help=f"Hugging Face model repo ID (default: {settings.repo_id})",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=settings.model_dir,
        help="Local model directory containing config/model/voices assets.",
    )
    parser.add_argument(
        "--offline",
        action=argparse.BooleanOptionalAction,
        default=settings.offline,
        help="Use local assets only (default: on). Pass --no-offline to allow network fetches.",
    )
    return parser.parse_args(argv)


def parse_speak_args(argv: Sequence[str], settings: SettingsSnapshot) -> argparse.Namespace:
    """Parse args for `koko` speak command."""

    parser = argparse.ArgumentParser(
        prog="koko",
        description="Local text-to-speech CLI powered by Kokoro-82M",
    )
    parser.add_argument(
        "message",
        nargs="*",
        help="Text to speak. If omitted, reads from stdin.",
    )
    parser.add_argument(
        "-v",
        "--voice",
        default=settings.default_voice,
        help=f"Voice ID (default: {settings.default_voice}). Use '?' to list voices.",
    )
    parser.add_argument(
        "-l",
        "--lang-code",
        default=None,
        help="Language code (a, b, e, f, h, i, j, p, z). Auto-derived from voice by default.",
    )
    parser.add_argument(
        "-s",
        "--speed",
        type=positive_float,
        default=1.0,
        help="Speech speed multiplier (>0).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional WAV output path.",
    )
    parser.add_argument(
        "-f",
        "--input-file",
        type=str,
        default=None,
        help="Read message text from file path, or '-' for stdin.",
    )
    parser.add_argument(
        "--summarize",
        action=argparse.BooleanOptionalAction,
        default=settings.summarize,
        help="Summarize input text into conversational speech before synthesis.",
    )
    parser.add_argument(
        "--llm-base-url",
        default=settings.llm_base_url,
        help=f"OpenAI-compatible API base URL (default: {settings.llm_base_url})",
    )
    parser.add_argument(
        "--llm-model",
        default=settings.llm_model,
        help=f"LLM model id for summarization (default: {settings.llm_model})",
    )
    parser.add_argument(
        "--llm-api-key",
        default=settings.llm_api_key,
        help="Optional API key for the OpenAI-compatible endpoint.",
    )
    parser.add_argument(
        "--llm-timeout-seconds",
        type=positive_float,
        default=settings.llm_timeout_seconds,
        help="LLM request timeout in seconds (>0).",
    )
    parser.add_argument(
        "--llm-max-input-chars",
        type=positive_int,
        default=settings.llm_max_input_chars,
        help="Maximum input characters sent to summarization model (>0).",
    )
    parser.add_argument(
        "--repo-id",
        default=settings.repo_id,
        help=f"Hugging Face model repo ID (default: {settings.repo_id})",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=settings.model_dir,
        help="Local model directory containing config/model/voices assets.",
    )
    parser.add_argument(
        "--offline",
        action=argparse.BooleanOptionalAction,
        default=settings.offline,
        help="Use local assets only (default: on). Pass --no-offline to allow network fetches.",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help="Inference device (default: auto).",
    )
    parser.add_argument(
        "--split-pattern",
        default=r"\n+",
        help=r"Regex pattern used to split text into segments (default: '\n+').",
    )
    parser.add_argument(
        "--play",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Play generated audio using a local audio player (default: on).",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit.",
    )
    return parser.parse_args(argv)


def validate_voices_namespace(namespace: argparse.Namespace) -> VoicesCommand:
    """Validate parsed voice-list command arguments."""

    try:
        return VoicesCommand.model_validate(vars(namespace))
    except ValidationError as error:
        raise UsageError(format_validation_error(error)) from error


def validate_speak_namespace(namespace: argparse.Namespace) -> SpeakCommand:
    """Validate parsed speak command arguments."""

    try:
        return SpeakCommand.model_validate(vars(namespace))
    except ValidationError as error:
        raise UsageError(format_validation_error(error)) from error
