"""
Simple energy-based Voice Activity Detection.
Detects speech start/end based on a static volume threshold.
"""
from __future__ import annotations

import logging
import os
import struct
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    """Energy-based VAD for speech detection."""

    def __init__(
        self,
        energy_threshold: Optional[float] = None,
        silence_duration_ms: Optional[int] = None,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
    ):
        self.energy_threshold = energy_threshold or float(os.getenv("VAD_ENERGY_THRESHOLD", "0.04"))
        self.silence_duration_ms = silence_duration_ms or int(os.getenv("VAD_SILENCE_MS", "700"))
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms

        self._speech_started = False
        self._silence_frames = 0
        self._speech_frames = 0
        self._max_silence_frames = self.silence_duration_ms // frame_duration_ms
        # Require 150ms (5 frames at 30ms each) of continuous speech to trigger barge-in.
        # This prevents keyboard clicks, throat clears, or brief noises from interrupting.
        self._min_speech_frames = 5

    def process_frame(self, pcm_data: bytes) -> Optional[str]:
        """
        Process a PCM16 audio frame.
        Returns: "speech_start", "speech_end", or None
        """
        energy = self._compute_energy(pcm_data)

        if energy > self.energy_threshold:
            self._silence_frames = 0
            if not self._speech_started:
                self._speech_frames += 1
                if self._speech_frames >= self._min_speech_frames:
                    self._speech_started = True
                    return "speech_start"
            return None
        else:
            if self._speech_started:
                self._silence_frames += 1
                if self._silence_frames >= self._max_silence_frames:
                    self._speech_started = False
                    self._silence_frames = 0
                    self._speech_frames = 0
                    return "speech_end"
            else:
                self._speech_frames = 0
            return None

    def reset(self):
        self._speech_started = False
        self._silence_frames = 0
        self._speech_frames = 0

    @property
    def is_speaking(self) -> bool:
        return self._speech_started

    @staticmethod
    def _compute_energy(pcm_data: bytes) -> float:
        """Compute RMS energy of PCM16 audio."""
        if len(pcm_data) < 2:
            return 0.0
        n_samples = len(pcm_data) // 2
        # Use memoryview for fast slicing of bytes without creating copies
        mv = memoryview(pcm_data)
        # Cast slice to bytes for struct.unpack
        samples = struct.unpack(f"<{n_samples}h", bytes(mv[:n_samples * 2]))
        if not samples:
            return 0.0
        rms = (sum(s * s for s in samples) / n_samples) ** 0.5
        return rms / 32768.0
