from __future__ import annotations


class KokoError(RuntimeError):
    """Base exception for CLI failures."""


class UsageError(KokoError):
    """Raised for invalid command usage."""


class PlaybackError(KokoError):
    """Raised when playback fails."""
