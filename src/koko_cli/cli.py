from __future__ import annotations

from collections.abc import Sequence

from . import entrypoint, parsers
from .settings import SettingsSnapshot

split_command = parsers.split_command
parse_voices_args = parsers.parse_voices_args
parse_speak_args = parsers.parse_speak_args
validate_voices_namespace = parsers.validate_voices_namespace
validate_speak_namespace = parsers.validate_speak_namespace


def load_settings() -> SettingsSnapshot:
    """Back-compat shim for callers importing from `koko_cli.cli`."""

    return entrypoint.load_settings()


def main(argv: Sequence[str] | None = None) -> int:
    """Back-compat shim for callers importing from `koko_cli.cli`."""

    return entrypoint.main(argv, load_settings_fn=load_settings)


__all__ = [
    "load_settings",
    "main",
    "parse_speak_args",
    "parse_voices_args",
    "split_command",
    "validate_speak_namespace",
    "validate_voices_namespace",
]


if __name__ == "__main__":
    raise SystemExit(main())
