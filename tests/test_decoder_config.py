"""Unit tests for AcousticDecoderConfig and sweet spot calibration."""

import pytest
from yapclean_care.decoder_config import (
    AcousticDecoderConfig,
    get_sweet_spot_config,
)


def test_decoder_config_defaults() -> None:
    """Verify default decoder config enforces anti-hallucination settings."""
    cfg = AcousticDecoderConfig()
    assert cfg.repetition_penalty == 1.10
    assert cfg.condition_on_previous_text is False
    assert cfg.no_repeat_ngram_size == 0
    assert cfg.compression_ratio_threshold == 2.4


def test_decoder_config_faster_whisper_kwargs() -> None:
    """Verify export to faster-whisper transcribe() arguments."""
    cfg = AcousticDecoderConfig(repetition_penalty=1.12, condition_on_previous_text=False)
    kwargs = cfg.to_faster_whisper_kwargs()

    assert kwargs["repetition_penalty"] == 1.12
    assert kwargs["condition_on_previous_text"] is False
    assert kwargs["no_repeat_ngram_size"] == 0
    assert kwargs["compression_ratio_threshold"] == 2.4
    assert isinstance(kwargs["temperature"], list)


def test_decoder_config_whisper_cpp_flags() -> None:
    """Verify export to whisper.cpp CLI flags."""
    cfg = AcousticDecoderConfig(condition_on_previous_text=False)
    flags = cfg.to_whisper_cpp_flags()

    assert "--no-context" in flags


def test_get_sweet_spot_config_per_model() -> None:
    """Verify empirical sweet-spot penalties for specific model families."""
    base_cfg = get_sweet_spot_config("base")
    assert base_cfg.repetition_penalty == 1.12
    assert base_cfg.condition_on_previous_text is False
    assert base_cfg.no_repeat_ngram_size == 0

    small_cfg = get_sweet_spot_config("small")
    assert small_cfg.repetition_penalty == 1.08
    assert small_cfg.condition_on_previous_text is False

    large_cfg = get_sweet_spot_config("large-v3")
    assert large_cfg.repetition_penalty == 1.10
    assert large_cfg.condition_on_previous_text is False

    distil_cfg = get_sweet_spot_config("distil-large-v3")
    assert distil_cfg.repetition_penalty == 1.10


def test_decoder_config_immutability() -> None:
    """Verify AcousticDecoderConfig is frozen and cannot be mutated at runtime."""
    cfg = AcousticDecoderConfig()
    with pytest.raises(Exception):
        cfg.repetition_penalty = 1.25  # type: ignore
