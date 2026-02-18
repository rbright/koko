from __future__ import annotations

import tempfile
from pathlib import Path

from kokoro import KModel

from .audio import play_audio, write_wav
from .errors import UsageError
from .models import SpeakCommand, VoicesCommand
from .offline import (
    configure_offline_environment,
    list_available_voices,
    resolve_local_assets,
    resolve_model_dir,
    resolve_voice_source,
)
from .settings import SettingsSnapshot
from .synthesis import build_local_model, build_pipeline, pipeline_lang_code, synthesize_waveform
from .text import resolve_lang_code, resolve_text


def list_voices(command: VoicesCommand, settings: SettingsSnapshot) -> list[str]:
    """Resolve the list of available voices for a command."""

    resolved_model_dir = resolve_model_dir(
        model_dir=command.model_dir,
        offline=command.offline,
        require_local_assets=False,
        default_local_model_dir=settings.default_model_dir,
    )

    force_local_assets = command.offline or command.model_dir is not None

    local_model_dir: Path | None = None
    if resolved_model_dir is not None:
        try:
            local_model_dir = resolve_local_assets(resolved_model_dir).model_dir
        except UsageError:
            if force_local_assets:
                raise

    return list_available_voices(repo_id=command.repo_id, model_dir=local_model_dir)


def run_voices(command: VoicesCommand, settings: SettingsSnapshot) -> int:
    """List voices to stdout."""

    for voice_name in list_voices(command=command, settings=settings):
        print(voice_name)
    return 0


def run_speak(command: SpeakCommand, settings: SettingsSnapshot) -> int:
    """Synthesize speech for a parsed speak command."""

    text = resolve_text(
        message_parts=command.message,
        input_file=command.input_file,
    )
    lang_code = resolve_lang_code(lang_code=command.lang_code, voice=command.voice)
    device = None if command.device == "auto" else command.device

    configure_offline_environment(command.offline)

    resolved_model_dir = resolve_model_dir(
        model_dir=command.model_dir,
        offline=command.offline,
        require_local_assets=True,
        default_local_model_dir=settings.default_model_dir,
    )
    force_local_assets = command.offline or command.model_dir is not None

    local_assets = None
    if resolved_model_dir is not None:
        try:
            local_assets = resolve_local_assets(resolved_model_dir)
        except UsageError:
            if force_local_assets:
                raise

    voice_source = command.voice
    model: KModel | bool = True

    if local_assets is not None:
        voice_source = resolve_voice_source(voice=command.voice, voices_dir=local_assets.voices_dir)
        model = build_local_model(
            assets=local_assets,
            repo_id=command.repo_id,
            device=device,
        )

    pipeline = build_pipeline(
        lang_code=pipeline_lang_code(lang_code),
        repo_id=command.repo_id,
        device=device,
        model=model,
    )

    waveform = synthesize_waveform(
        pipeline=pipeline,
        text=text,
        voice=voice_source,
        speed=command.speed,
        split_pattern=command.split_pattern,
        lang_code=lang_code,
    )

    output_path = command.output.resolve() if command.output else None
    if output_path is not None:
        write_wav(path=output_path, waveform=waveform)
        print(output_path)

    if command.play:
        play_path = output_path
        cleanup_path: Path | None = None

        if play_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_file.close()
            play_path = Path(temp_file.name)
            cleanup_path = play_path
            write_wav(path=play_path, waveform=waveform)

        try:
            play_audio(play_path)
        finally:
            if cleanup_path is not None:
                cleanup_path.unlink(missing_ok=True)

    return 0
