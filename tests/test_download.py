from __future__ import annotations

from pathlib import Path

import pytest

from koko_cli import download
from koko_cli.errors import UsageError


def test_normalize_voice_name_handles_path_and_extension() -> None:
    assert download.normalize_voice_name("af_heart") == "af_heart"
    assert download.normalize_voice_name("voices/af_heart.pt") == "af_heart"
    assert download.normalize_voice_name("/tmp/voices/af_heart.pt") == "af_heart"


def test_normalize_voice_name_rejects_empty_value() -> None:
    with pytest.raises(UsageError, match="Voice names cannot be empty"):
        download.normalize_voice_name("   ")


def test_build_allow_patterns_for_all_voices() -> None:
    patterns = download.build_allow_patterns("all")
    assert patterns == ["config.json", "kokoro-v1_0.pth", "voices/*.pt"]


def test_build_allow_patterns_for_specific_voices() -> None:
    patterns = download.build_allow_patterns("af_heart,voices/bf_emma.pt,af_heart")

    assert patterns == [
        "config.json",
        "kokoro-v1_0.pth",
        "voices/af_heart.pt",
        "voices/bf_emma.pt",
    ]


def test_download_model_assets_calls_snapshot_download(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called: dict[str, object] = {}

    def fake_snapshot_download(**kwargs: object) -> str:
        called.update(kwargs)
        return str(tmp_path)

    monkeypatch.setattr(download, "snapshot_download", fake_snapshot_download)

    output_dir = download.download_model_assets(
        model_dir=tmp_path / "model-dir",
        repo_id="hexgrad/Kokoro-82M",
        voices="af_heart",
    )

    assert output_dir == (tmp_path / "model-dir").resolve()
    assert called["repo_id"] == "hexgrad/Kokoro-82M"
    assert called["allow_patterns"] == ["config.json", "kokoro-v1_0.pth", "voices/af_heart.pt"]
    assert called["local_dir"] == (tmp_path / "model-dir").resolve()
