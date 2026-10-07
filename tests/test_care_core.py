"""
Unit tests for YapClean Care Core Modules:
- Audio Pre-roll buffer & Dynamic VAD
- Active OS Keyboard Layout Auto-Translator
"""

from __future__ import annotations

import pytest

from yapclean_care.audio_buffer import DynamicAtypicalVAD, PreRollAudioBuffer
from yapclean_care.layout_translator import LayoutTranslator


def test_preroll_audio_buffer_push_and_clear():
    buf = PreRollAudioBuffer(sample_rate=16000, chunk_size=512, preroll_seconds=1.5)
    assert buf.buffered_seconds == 0.0

    chunk = b"\x00\x01" * 256  # 512 bytes
    for _ in range(10):
        buf.push(chunk)

    data = buf.get_preroll_data()
    assert len(data) == 512 * 10
    assert buf.buffered_seconds > 0.1

    buf.clear()
    assert len(buf.get_preroll_data()) == 0
    assert buf.buffered_seconds == 0.0


def test_dynamic_vad_spastic_pause_accommodation():
    vad = DynamicAtypicalVAD(silence_threshold_seconds=1.6, energy_threshold=100.0)

    # Active speech chunk
    speech_chunk = b"\x50\x20" * 256  # high energy
    silence_chunk = b"\x01\x00" * 256  # very low energy

    t0 = 1000.0
    # Process speech
    assert vad.process_frame(speech_chunk, timestamp=t0) is True

    # 1.0s pause (spastic hesitation) -> should NOT cut off (below 1.6s)
    assert vad.process_frame(silence_chunk, timestamp=t0 + 1.0) is True

    # 1.5s pause -> still should NOT cut off
    assert vad.process_frame(silence_chunk, timestamp=t0 + 1.5) is True

    # 1.7s pause -> exceeds 1.6s threshold, dictation concludes
    assert vad.process_frame(silence_chunk, timestamp=t0 + 1.7) is False


def test_layout_translator_mismatch_detection():
    translator = LayoutTranslator(default_target_lang="en")

    # Mismatch: User speaks Russian, target layout is English
    assert translator.should_translate("ru", "en") is True
    assert translator.should_translate("bg", "en") is True
    assert translator.should_translate("uk", "en") is True

    # Match: User speaks English, target layout is English
    assert translator.should_translate("en", "en") is False
    assert translator.should_translate("en-US", "en") is False

    # Translation prompt generation
    prompt = translator.format_translation_prompt("Здравей свят", "bg", "en")
    assert "from bg to en" in prompt
    assert "Здравей свят" in prompt
