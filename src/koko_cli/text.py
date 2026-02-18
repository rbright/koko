from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .constants import LANG_ALIASES, SUPPORTED_LANG_CODES
from .errors import UsageError


def positive_float(value: str) -> float:
    """argparse validator for positive float values."""

    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def resolve_text(message_parts: Sequence[str], input_file: str | None) -> str:
    """Resolve input text from message args, file, or stdin."""

    if input_file and message_parts:
        raise UsageError("Provide either message args or --input-file, not both.")

    if input_file is not None:
        if input_file == "-":
            text = sys.stdin.read()
        else:
            text = Path(input_file).read_text(encoding="utf-8")
    elif message_parts:
        text = " ".join(message_parts)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        raise UsageError("No input text provided. Pass a message, --input-file, or pipe stdin.")

    normalized_text = text.strip()
    if not normalized_text:
        raise UsageError("Input text is empty after trimming whitespace.")

    return normalized_text


def resolve_lang_code(lang_code: str | None, voice: str) -> str:
    """Resolve language code from explicit value or voice prefix."""

    if lang_code:
        normalized = LANG_ALIASES.get(lang_code.lower(), lang_code.lower())
        if normalized not in SUPPORTED_LANG_CODES:
            valid = ", ".join(sorted(SUPPORTED_LANG_CODES))
            raise UsageError(f"Unsupported language code '{lang_code}'. Valid values: {valid}")
        return normalized

    first_voice = voice.split(",", maxsplit=1)[0].strip()
    if first_voice.endswith(".pt"):
        first_voice = Path(first_voice).stem

    prefix = first_voice.split("_", maxsplit=1)[0]
    if prefix and prefix[0] in SUPPORTED_LANG_CODES:
        return prefix[0]

    return "a"
