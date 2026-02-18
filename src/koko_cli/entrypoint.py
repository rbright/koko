from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from pydantic import ValidationError

from .errors import UsageError
from .models import VoicesCommand, format_validation_error
from .parsers import (
    parse_speak_args,
    parse_voices_args,
    split_command,
    validate_speak_namespace,
    validate_voices_namespace,
)
from .service import run_speak, run_voices
from .settings import SettingsSnapshot, get_settings, snapshot_settings


def load_settings() -> SettingsSnapshot:
    """Load runtime settings snapshot for command defaults."""

    return snapshot_settings(get_settings())


def main(
    argv: Sequence[str] | None = None,
    *,
    load_settings_fn: Callable[[], SettingsSnapshot] | None = None,
) -> int:
    """Run koko CLI."""

    args = list(argv) if argv is not None else sys.argv[1:]
    command, remaining_args = split_command(args)

    resolve_settings = load_settings_fn or load_settings

    try:
        settings = resolve_settings()

        if command == "voices":
            voices_namespace = parse_voices_args(remaining_args, settings=settings)
            voices_command = validate_voices_namespace(voices_namespace)
            return run_voices(command=voices_command, settings=settings)

        speak_namespace = parse_speak_args(remaining_args, settings=settings)
        speak_command = validate_speak_namespace(speak_namespace)

        if speak_command.list_voices or speak_command.voice == "?":
            voices_command = VoicesCommand(
                repo_id=speak_command.repo_id,
                model_dir=speak_command.model_dir,
                offline=speak_command.offline,
            )
            return run_voices(command=voices_command, settings=settings)

        return run_speak(command=speak_command, settings=settings)
    except UsageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except ValidationError as error:
        print(f"error: {format_validation_error(error)}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as error:  # noqa: BLE001
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
