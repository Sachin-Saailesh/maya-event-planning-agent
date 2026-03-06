"""
Session manager — in-memory store for active planning sessions.
Enhanced with connection tracking, memory fields, barge-in support,
and optional persistent storage.
"""
from __future__ import annotations

import copy
import os
import sys
import logging
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "schema"))

from maya_schema.state import create_empty_state
from maya_schema.patches import apply_patch

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages planning sessions in memory with pub-sub connection tracking."""

    def __init__(self):
        self._sessions: dict[str, dict[str, Any]] = {}
        self._connections: dict[str, list[WebSocket]] = {}

    def create_session(self, session_id: str) -> dict[str, Any]:
        session = {
            "state": create_empty_state(),
            "transcript": [],
            "current_slot": None,
            "pending_confirmation": None,
            "summary": None,
            # Advanced features
            "conversation_summary": "",
            "recent_turns": [],
            "turn_count": 0,
            "spoken_sentences": [],  # for barge-in tracking
        }
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self._sessions.get(session_id)

    def add_transcript(self, session_id: str, speaker: str, text: str, is_final: bool):
        session = self._sessions.get(session_id)
        if session:
            entry = {
                "speaker": speaker,
                "text": text,
                "is_final": is_final,
            }
            session["transcript"].append(entry)

    def get_current_slot(self, session_id: str) -> str | None:
        session = self._sessions.get(session_id)
        if session:
            return session.get("current_slot")
        return None

    def set_current_slot(self, session_id: str, slot: str | None):
        session = self._sessions.get(session_id)
        if session:
            session["current_slot"] = slot

    def get_pending_confirmation(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if session:
            return session.get("pending_confirmation")
        return None

    def set_pending_confirmation(self, session_id: str, confirmation: dict[str, Any] | None):
        session = self._sessions.get(session_id)
        if session:
            session["pending_confirmation"] = confirmation

    def apply_state_patch(self, session_id: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if not session:
            return {}
        state = session["state"]
        # apply_patch expects a list of operations, modify state in place
        new_state = apply_patch(state, ops)
        session["state"] = new_state
        return new_state

    def set_summary(self, session_id: str, summary: str):
        session = self._sessions.get(session_id)
        if session:
            session["summary"] = summary

    def get_state(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if session:
            return session["state"]
        return None

    # ── Pub-Sub Connection Tracking ─────────────────────────────

    def add_connection(self, session_id: str, websocket: WebSocket):
        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(websocket)

    def remove_connection(self, session_id: str, websocket: WebSocket):
        if session_id in self._connections and websocket in self._connections[session_id]:
            self._connections[session_id].remove(websocket)

    async def broadcast(self, session_id: str, event_type: str, payload: dict[str, Any]):
        import json
        from maya_schema.events import create_event
        event = create_event(event_type, session_id, payload)
        text_data = json.dumps(event)

        if session_id in self._connections:
            dead = []
            for ws in self._connections[session_id]:
                try:
                    await ws.send_text(text_data)
                except Exception:
                    dead.append(ws)
            # Clean up dead connections
            for ws in dead:
                self._connections[session_id].remove(ws)

    # ── Rolling Memory ──────────────────────────────────────────

    def get_turn_count(self, session_id: str) -> int:
        session = self._sessions.get(session_id)
        return session.get("turn_count", 0) if session else 0

    def increment_turn_count(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session["turn_count"] = session.get("turn_count", 0) + 1

    def set_conversation_summary(self, session_id: str, summary: str):
        session = self._sessions.get(session_id)
        if session:
            session["conversation_summary"] = summary

    def get_conversation_summary(self, session_id: str) -> str:
        session = self._sessions.get(session_id)
        return session.get("conversation_summary", "") if session else ""

    # ── Barge-in Tracking ───────────────────────────────────────

    def add_spoken_sentence(self, session_id: str, sentence: str):
        session = self._sessions.get(session_id)
        if session and sentence:
            session.setdefault("spoken_sentences", []).append(sentence)

    def get_spoken_sentences(self, session_id: str) -> list[str]:
        session = self._sessions.get(session_id)
        return session.get("spoken_sentences", []) if session else []

    def clear_spoken_sentences(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session["spoken_sentences"] = []

    # ── Session Snapshot (for reconnection) ─────────────────────

    def get_snapshot(self, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        return {
            "state": session["state"],
            "summary": session.get("summary"),
            "conversation_summary": session.get("conversation_summary", ""),
            "recent_transcripts": session["transcript"][-10:],
            "current_slot": session.get("current_slot"),
            "turn_count": session.get("turn_count", 0),
        }
