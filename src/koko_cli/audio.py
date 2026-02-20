from __future__ import annotations

import platform
import shutil
import subprocess
import wave
from pathlib import Path

import torch

from .constants import DEFAULT_SAMPLE_RATE
from .errors import PlaybackError


def write_wav(path: Path, waveform: torch.Tensor, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    """Write a mono, signed 16-bit PCM WAV file."""

    clipped = torch.clamp(waveform, min=-1.0, max=1.0)
    pcm = (clipped * 32767.0).to(torch.int16).numpy().tobytes()

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)


def play_audio(path: Path) -> None:
    """Play WAV audio with the first available local player."""

    for command in player_candidates(path):
        executable = command[0]
        if shutil.which(executable) is None:
            continue

        result = subprocess.run(command, check=False)
        if result.returncode == 0:
            return

        raise PlaybackError(f"Audio player '{executable}' exited with status {result.returncode}.")

    candidates = ", ".join(candidate[0] for candidate in player_candidates(path))
    raise PlaybackError(
        f"No supported audio player found in PATH. Install one of: {candidates}, or run with --no-play --output <file>."
    )


def player_candidates(path: Path) -> list[list[str]]:
    """Return preferred playback commands for the current OS."""

    target = str(path)
    os_name = platform.system().lower()

    if os_name == "darwin":
        return [["afplay", target]]

    if os_name == "linux":
        return [
            ["pw-play", target],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", target],
            ["aplay", target],
            ["paplay", target],
        ]

    return [["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", target]]
