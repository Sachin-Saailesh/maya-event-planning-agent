"""
OpenAI Whisper STT client with retry/timeout logic.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import time
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for Whisper STT")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def transcribe(
    audio_bytes: bytes,
    *,
    model: str = "whisper-1",
    language: str = "en",
    max_retries: int = 3,
    timeout: float = 30.0,
) -> str:
    """
    Transcribe audio bytes using OpenAI Whisper API.
    Returns transcript text. Retries on failure with exponential backoff.
    """
    client = _get_client()

    for attempt in range(max_retries):
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.webm"

            start_t = time.perf_counter()
            transcript = await asyncio.wait_for(
                client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language,
                    response_format="text",
                ),
                timeout=timeout,
            )
            duration_ms = (time.perf_counter() - start_t) * 1000
            txt = transcript.strip()
            logger.info(f"[METRICS] STT Whisper duration: {duration_ms:.1f}ms (length: {len(txt)})")
            return txt

        except asyncio.TimeoutError:
            logger.warning(f"Whisper timeout (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            logger.error(f"Whisper error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)

    return ""
