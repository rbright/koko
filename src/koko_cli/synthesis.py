from __future__ import annotations

import re
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol

import torch
from kokoro import KModel, KPipeline

from .constants import MAX_PHONEME_CHARS
from .errors import KokoError, UsageError
from .offline import LocalAssets


class TextPhonemizer(Protocol):
    """Protocol for text->phoneme conversion callables."""

    def __call__(self, text: str) -> tuple[str, None]:
        """Return a phoneme string and optional metadata."""


@contextmanager
def suppress_known_kokoro_warnings() -> Iterator[None]:
    """Silence known third-party warnings emitted during Kokoro model construction."""

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"dropout option adds dropout after all but last recurrent layer.*",
            category=UserWarning,
        )
        warnings.filterwarnings(
            "ignore",
            message=r"`torch\.nn\.utils\.weight_norm` is deprecated.*",
            category=FutureWarning,
        )
        yield


def build_local_model(assets: LocalAssets, repo_id: str, device: str | None) -> KModel:
    """Build a Kokoro model instance from local artifacts."""

    if device == "cuda" and not torch.cuda.is_available():
        raise UsageError("CUDA requested but not available.")

    resolved_device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    with suppress_known_kokoro_warnings():
        model = KModel(
            repo_id=repo_id,
            config=str(assets.config_path),
            model=str(assets.model_path),
        )

    return model.to(resolved_device).eval()


def pipeline_lang_code(lang_code: str) -> str:
    """Map user-facing language codes to a safe Kokoro pipeline code."""

    if lang_code in {"a", "b"}:
        return "e"
    return lang_code


def build_pipeline(lang_code: str, repo_id: str, device: str | None, model: KModel | bool = True) -> KPipeline:
    """Create a configured Kokoro pipeline instance."""

    if model is True:
        with suppress_known_kokoro_warnings():
            return KPipeline(lang_code=lang_code, repo_id=repo_id, device=device, model=model)

    return KPipeline(lang_code=lang_code, repo_id=repo_id, device=device, model=model)


def synthesize_waveform(
    pipeline: KPipeline,
    text: str,
    voice: str,
    speed: float,
    split_pattern: str,
    lang_code: str,
) -> torch.Tensor:
    """Run Kokoro inference and concatenate all generated chunks."""

    if lang_code in {"a", "b"}:
        return synthesize_waveform_english_espeak(
            pipeline=pipeline,
            text=text,
            voice=voice,
            speed=speed,
            split_pattern=split_pattern,
            lang_code=lang_code,
        )

    return synthesize_waveform_pipeline(
        pipeline=pipeline,
        text=text,
        voice=voice,
        speed=speed,
        split_pattern=split_pattern,
    )


def synthesize_waveform_pipeline(
    pipeline: KPipeline,
    text: str,
    voice: str,
    speed: float,
    split_pattern: str,
) -> torch.Tensor:
    """Generate waveform directly through `KPipeline.__call__`."""

    chunks: list[torch.Tensor] = []

    for result in pipeline(text=text, voice=voice, speed=speed, split_pattern=split_pattern):
        audio = result.audio
        if audio is None:
            continue
        chunks.append(audio.detach().cpu())

    return concatenate_audio(chunks)


def synthesize_waveform_english_espeak(
    pipeline: KPipeline,
    text: str,
    voice: str,
    speed: float,
    split_pattern: str,
    lang_code: str,
) -> torch.Tensor:
    """Generate English speech via espeak phonemization + `generate_from_tokens`."""

    phonemizer = build_english_phonemizer(lang_code)
    chunks: list[torch.Tensor] = []

    for segment in split_text_segments(text=text, split_pattern=split_pattern):
        for chunk_text in chunk_segment_for_phoneme_limit(segment=segment, phonemizer=phonemizer):
            phonemes = phonemize_text(phonemizer=phonemizer, text=chunk_text)
            if not phonemes:
                continue

            for result in pipeline.generate_from_tokens(tokens=phonemes, voice=voice, speed=speed):
                audio = result.audio
                if audio is None:
                    continue
                chunks.append(audio.detach().cpu())

    return concatenate_audio(chunks)


def build_english_phonemizer(lang_code: str) -> TextPhonemizer:
    """Build an espeak phonemizer for American/British English."""

    from misaki.espeak import EspeakG2P

    language = "en-gb" if lang_code == "b" else "en-us"
    return EspeakG2P(language=language)


def split_text_segments(text: str, split_pattern: str) -> list[str]:
    """Split text into non-empty segments."""

    if split_pattern:
        raw_segments = re.split(split_pattern, text.strip())
    else:
        raw_segments = [text]

    return [segment.strip() for segment in raw_segments if segment.strip()]


def chunk_segment_for_phoneme_limit(segment: str, phonemizer: TextPhonemizer) -> list[str]:
    """Chunk a segment so each chunk stays under Kokoro's phoneme length limit."""

    if phoneme_length(phonemizer=phonemizer, text=segment) <= MAX_PHONEME_CHARS:
        return [segment]

    chunked_segments: list[str] = []
    sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?;:])\s+", segment) if part.strip()]
    if not sentence_parts:
        sentence_parts = [segment]

    for sentence in sentence_parts:
        if phoneme_length(phonemizer=phonemizer, text=sentence) <= MAX_PHONEME_CHARS:
            chunked_segments.append(sentence)
            continue

        chunked_segments.extend(chunk_sentence_by_words(sentence=sentence, phonemizer=phonemizer))

    return chunked_segments


def chunk_sentence_by_words(sentence: str, phonemizer: TextPhonemizer) -> list[str]:
    """Chunk a sentence by words while enforcing the phoneme limit."""

    words = sentence.split()
    if not words:
        return []

    chunks: list[str] = []
    current_words: list[str] = []

    for word in words:
        candidate_words = [*current_words, word]
        candidate_text = " ".join(candidate_words)

        if phoneme_length(phonemizer=phonemizer, text=candidate_text) <= MAX_PHONEME_CHARS:
            current_words = candidate_words
            continue

        if not current_words:
            raise UsageError(
                "A single token exceeds Kokoro's phoneme limit. Shorten the input text or split it manually."
            )

        chunks.append(" ".join(current_words))
        current_words = [word]

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def phoneme_length(phonemizer: TextPhonemizer, text: str) -> int:
    """Return the number of phoneme characters for a text chunk."""

    return len(phonemize_text(phonemizer=phonemizer, text=text))


def phonemize_text(phonemizer: TextPhonemizer, text: str) -> str:
    """Convert text to a normalized phoneme string."""

    phonemes, _ = phonemizer(text)
    return phonemes.strip()


def concatenate_audio(chunks: list[torch.Tensor]) -> torch.Tensor:
    """Concatenate generated audio chunks into one tensor."""

    if not chunks:
        raise KokoError("Kokoro produced no audio for the provided input.")

    if len(chunks) == 1:
        return chunks[0]

    return torch.cat(chunks)
