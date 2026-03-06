"""
Event protocol types for Maya voice agent.
All events between orchestrator and clients/workers use this envelope.
"""
from __future__ import annotations

import time
from typing import Any


class EventType:
    """Event type constants."""
    # Client → Server
    CLIENT_AUDIO_STARTED = "client.audio.started"
    CLIENT_SPEECH_STARTED = "client.speech.started"
    CLIENT_TRANSCRIPT_PARTIAL = "client.transcript.partial"
    CLIENT_TRANSCRIPT_FINAL = "client.transcript.final"
    CLIENT_STATE_UPDATE = "client.state.update"
    CLIENT_CONFIRMATION_RESPONSE = "client.confirmation.response"
    CLIENT_BARGE_IN = "client.barge_in"
    CLIENT_IDLE_TIMEOUT = "client.idle.timeout"

    # Server → Client
    SERVER_PROMPT = "server.prompt"
    SERVER_PROMPT_CHUNK = "server.prompt.chunk"
    SERVER_STATE_PATCH = "server.state.patch"
    SERVER_CONFIRMATION_REQUEST = "server.confirmation.request"
    SERVER_SUMMARY_READY = "server.summary.ready"
    SERVER_SPEECH_INTERRUPTED = "server.speech.interrupted"
    SERVER_GUARDRAIL_BLOCKED = "server.guardrail.blocked"
    SERVER_SESSION_RESTORED = "server.session.restored"


def create_event(
    event_type: str,
    session_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a typed event envelope."""
    return {
        "type": event_type,
        "session_id": session_id,
        "timestamp": time.time(),
        "payload": payload or {},
    }
