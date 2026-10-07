"""
Assistive Audio Buffer & Dynamic VAD for YapClean Care.

Implements:
1. Pre-roll Continuous Ring Buffer (1.5s circular window): Captures initial breath
   and fragmented phonemes before physical or hotkey trigger activation.
2. Dynamic VAD & Silence Accommodator (1.6s pause tolerance): Prevents premature
   speech cutoffs during spastic breathing blocks or dysarthric hesitation.
"""

from __future__ import annotations

import collections
import time
from typing import Deque, List, Optional


class PreRollAudioBuffer:
    """Circular ring buffer preserving continuous pre-roll audio frames."""

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 512, preroll_seconds: float = 1.5) -> None:
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.preroll_seconds = preroll_seconds
        # Calculate maximum chunks needed for the pre-roll window
        chunks_per_sec = sample_rate / chunk_size
        self.max_chunks = int(chunks_per_sec * preroll_seconds)
        self._buffer: Deque[bytes] = collections.deque(maxlen=self.max_chunks)

    def push(self, chunk: bytes) -> None:
        """Add a raw PCM chunk to circular buffer."""
        self._buffer.append(chunk)

    def get_preroll_data(self) -> bytes:
        """Retrieve all currently held pre-roll audio as contiguous bytes."""
        return b"".join(self._buffer)

    def clear(self) -> None:
        """Clear the ring buffer (e.g. between sessions)."""
        self._buffer.clear()

    @property
    def buffered_seconds(self) -> float:
        """Calculate duration of held audio in seconds."""
        total_bytes = sum(len(c) for c in self._buffer)
        bytes_per_second = self.sample_rate * 2  # 16-bit PCM
        return total_bytes / bytes_per_second if bytes_per_second else 0.0


class DynamicAtypicalVAD:
    """Voice Activity Detector calibrated for atypical speech pauses."""

    def __init__(
        self,
        silence_threshold_seconds: float = 1.6,
        energy_threshold: float = 300.0,
    ) -> None:
        self.silence_threshold_seconds = silence_threshold_seconds
        self.energy_threshold = energy_threshold
        self._last_speech_time: Optional[float] = None
        self._speech_detected = False

    def process_frame(self, audio_chunk: bytes, timestamp: Optional[float] = None) -> bool:
        """Process a PCM chunk and evaluate whether dictation should continue.
        
        Args:
            audio_chunk: Raw 16-bit PCM audio bytes.
            timestamp: Optional monotonic timestamp.
            
        Returns:
            True if voice session is active; False if silence threshold exceeded.
        """
        now = timestamp if timestamp is not None else time.monotonic()
        if not audio_chunk:
            return True

        # Calculate RMS energy for 16-bit little-endian samples
        sample_count = len(audio_chunk) // 2
        if sample_count == 0:
            return True

        # Simple energy estimation
        energy = 0
        for i in range(0, len(audio_chunk), 2):
            val = int.from_bytes(audio_chunk[i:i+2], byteorder="little", signed=True)
            energy += abs(val)
        avg_energy = energy / sample_count

        if avg_energy >= self.energy_threshold:
            self._last_speech_time = now
            self._speech_detected = True
            return True

        # If speech was already detected, check pause duration
        if self._speech_detected and self._last_speech_time is not None:
            silence_duration = now - self._last_speech_time
            if silence_duration >= self.silence_threshold_seconds:
                return False  # End of speech session reached

        return True

    def reset(self) -> None:
        """Reset VAD state for a new recording."""
        self._last_speech_time = None
        self._speech_detected = False
