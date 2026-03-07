"""
Rolling summary memory for Maya voice agent.
Compresses old conversation turns into summaries to prevent context overflow.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# How many recent turns to keep in full
RECENT_TURNS_LIMIT = int(os.getenv("RECENT_TURNS_LIMIT", "4"))
# Compress every N turns
COMPRESS_INTERVAL = int(os.getenv("COMPRESS_INTERVAL", "4"))


def should_compress(turn_count: int) -> bool:
    """Check if it's time to compress the conversation history."""
    return turn_count > 0 and turn_count % COMPRESS_INTERVAL == 0


def compress_transcript(turns: list[dict[str, Any]]) -> str:
    """
    Compress a list of conversation turns into a summary string.
    Uses extractive summarization (free, no API calls).
    
    For LLM-powered summarization, set SUMMARY_BACKEND=llm.
    """
    if not turns:
        return ""

    backend = os.getenv("SUMMARY_BACKEND", "extractive")
    
    if backend == "llm":
        return _compress_with_llm(turns)
    return _compress_extractive(turns)


def _compress_extractive(turns: list[dict[str, Any]]) -> str:
    """Simple extractive summarization — captures key decisions."""
    summary_parts = []
    
    for turn in turns:
        speaker = turn.get("speaker", "unknown")
        text = turn.get("text", "")
        
        if speaker == "user":
            # Extract user preferences mentioned
            if any(kw in text.lower() for kw in ["want", "like", "prefer", "gold", "maroon",
                                                   "rose", "jasmine", "floral", "yes", "no"]):
                summary_parts.append(f"User said: {text}")
        elif speaker == "maya":
            # Capture Maya's confirmations
            if text.startswith("Got it:"):
                summary_parts.append(f"Maya confirmed: {text}")
    
    if not summary_parts:
        return "Conversation in progress about wedding decoration planning."
    
    return " | ".join(summary_parts)


def _compress_with_llm(turns: list[dict[str, Any]]) -> str:
    """LLM-powered summarization using OpenAI."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        transcript_text = "\n".join(
            f"{t['speaker']}: {t['text']}" for t in turns
        )
        
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": (
                    "Summarize this wedding decoration planning conversation concisely. "
                    "Focus on decisions made: colors chosen, flowers selected, etc. "
                    "Keep it under 100 words."
                )},
                {"role": "user", "content": transcript_text},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        return _compress_extractive(turns)


def build_context(summary: str, recent_turns: list[dict[str, Any]]) -> str:
    """
    Build context string for the agent from summary + recent turns.
    This is what gets sent to the LLM/NLU for context.
    """
    parts = []
    
    if summary:
        parts.append(f"Previous conversation summary: {summary}")
        parts.append("---")
    
    if recent_turns:
        parts.append("Recent conversation:")
        for turn in recent_turns:
            speaker = "User" if turn.get("speaker") == "user" else "Maya"
            parts.append(f"  {speaker}: {turn.get('text', '')}")
    
    return "\n".join(parts)


def get_recent_turns(transcript: list[dict[str, Any]], limit: int = None) -> list[dict[str, Any]]:
    """Get the most recent N turns from the transcript."""
    limit = limit or RECENT_TURNS_LIMIT
    return transcript[-limit:] if len(transcript) > limit else transcript
