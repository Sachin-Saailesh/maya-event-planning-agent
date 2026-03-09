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

# How often to log energy (every N frames) to avoid flooding logs
_ENERGY_LOG_INTERVAL = 50
_frame_count = 0


class VoiceActivityDetector:
    """Energy-based VAD for speech detection."""

    def __init__(
        self,
        energy_threshold: Optional[float] = None,
        silence_duration_ms: Optional[int] = None,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
    ):
        # Lowered from 0.04 to 0.005 because Chrome's autoGainControl heavily
        # compresses mic audio, producing much lower amplitude values.
        self.energy_threshold = energy_threshold or float(os.getenv("VAD_ENERGY_THRESHOLD", "0.005"))
        self.silence_duration_ms = silence_duration_ms or int(os.getenv("VAD_SILENCE_MS", "700"))
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms

        self._speech_started = False
        self._silence_ms = 0.0
        self._speech_ms = 0.0
        self._frame_count = 0
        
        # Require 100ms of continuous speech to trigger speech_start.
        self._min_speech_ms = 100.0

    def process_frame(self, pcm_data: bytes, duration_ms: float = 10.0) -> Optional[str]:
        """
        Process a PCM16 audio frame.
        Returns: "speech_start", "speech_end", or None
        """
        energy = self._compute_energy(pcm_data)
        self._frame_count += 1

        # Log energy periodically so we can see actual audio levels in logs
        if self._frame_count % _ENERGY_LOG_INTERVAL == 0:
            logger.info(
                f"[VAD] frame={self._frame_count} energy={energy:.6f} "
                f"threshold={self.energy_threshold:.6f} "
                f"speaking={self._speech_started} "
                f"speech_ms={self._speech_ms:.0f} silence_ms={self._silence_ms:.0f}"
            )

        if energy > self.energy_threshold:
            self._silence_ms = 0.0
            if not self._speech_started:
                self._speech_ms += duration_ms
                if self._speech_ms >= self._min_speech_ms:
                    self._speech_started = True
                    logger.info(f"[VAD] >>> speech_start (energy={energy:.6f})")
                    return "speech_start"
            return None
        else:
            if self._speech_started:
                self._silence_ms += duration_ms
                if self._silence_ms >= self.silence_duration_ms:
                    self._speech_started = False
                    self._silence_ms = 0.0
                    self._speech_ms = 0.0
                    logger.info(f"[VAD] <<< speech_end")
                    return "speech_end"
            else:
                self._speech_ms = 0.0
            return None

    def reset(self):
        self._speech_started = False
        self._silence_ms = 0.0
        self._speech_ms = 0.0

    @property
    def is_speaking(self) -> bool:
        return self._speech_started

    @staticmethod
    def _compute_energy(pcm_data: bytes) -> float:
        """Compute RMS energy of PCM16 audio."""
        if len(pcm_data) < 2:
            return 0.0
        n_samples = len(pcm_data) // 2
        samples = struct.unpack(f"<{n_samples}h", pcm_data[:n_samples * 2])
        if not samples:
            return 0.0
        rms = (sum(s * s for s in samples) / n_samples) ** 0.5
        return rms / 32768.0
