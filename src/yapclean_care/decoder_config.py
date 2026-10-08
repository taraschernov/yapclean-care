"""Acoustic Decoder Configuration for Atypical and Dysarthric Speech.

Provides empirically calibrated hyperparameters for Whisper (faster-whisper and whisper.cpp)
to eliminate infinite repetition/hallucination loops on dysarthric speech while preserving
natural repetition in fluent speech.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class AcousticDecoderConfig:
    """Hyperparameters calibrated via Grid Search for atypical speech decoding."""

    repetition_penalty: float = 1.10
    condition_on_previous_text: bool = False
    no_repeat_ngram_size: int = 0
    compression_ratio_threshold: float = 2.4
    log_prob_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    temperatures: tuple[float, ...] = (0.0, 0.2, 0.4)

    def to_faster_whisper_kwargs(self) -> dict[str, Any]:
        """Export decoding arguments formatted for faster-whisper WhisperModel.transcribe()."""
        return {
            "repetition_penalty": self.repetition_penalty,
            "condition_on_previous_text": self.condition_on_previous_text,
            "no_repeat_ngram_size": self.no_repeat_ngram_size,
            "compression_ratio_threshold": self.compression_ratio_threshold,
            "log_prob_threshold": self.log_prob_threshold,
            "no_speech_threshold": self.no_speech_threshold,
            "temperature": list(self.temperatures),
        }

    def to_whisper_cpp_flags(self) -> list[str]:
        """Export decoding flags for whisper.cpp CLI."""
        flags: list[str] = []
        if not self.condition_on_previous_text:
            flags.append("--no-context")
        flags.extend(["--max-len", "0"])
        return flags


# Calibrated sweet spot configurations from empirical Grid Search (19 audio cases)
SWEET_SPOT_PENALTIES: Mapping[str, float] = {
    "base": 1.12,
    "small": 1.08,
    "medium": 1.10,
    "large-v3": 1.10,
    "large-v3-turbo": 1.10,
    "distil-large-v3": 1.10,
}


def get_sweet_spot_config(model_name_or_size: str = "base") -> AcousticDecoderConfig:
    """Return the empirically verified Sweet Spot decoder configuration.

    - base: repetition_penalty=1.12 (Combined WER score 65.9%)
    - small: repetition_penalty=1.08 (Combined WER score 65.6%)
    - default/large: repetition_penalty=1.10

    All configurations enforce:
    - condition_on_previous_text=False (prevents hallucination propagation)
    - no_repeat_ngram_size=0 (protects natural speech repetitions)
    """
    key = model_name_or_size.lower().strip()
    penalty = SWEET_SPOT_PENALTIES.get(key, 1.10)

    return AcousticDecoderConfig(
        repetition_penalty=penalty,
        condition_on_previous_text=False,
        no_repeat_ngram_size=0,
    )
