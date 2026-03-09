"""
WebSocket handler for real-time session communication.
Routes incoming events to conversation logic, applies guardrails,
handles barge-in interruptions, and broadcasts responses to all clients.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import logging
from typing import Any

from fastapi import WebSocket

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "schema"))

from maya_schema.events import EventType, create_event
from maya_schema.patches import apply_patch, create_add_patch, create_remove_patch, create_replace_patch, dotted_to_pointer
from maya_schema.state import get_nested

from session_manager import SessionManager
from conversation import (
    get_greeting,
    get_slot_prompt,
    process_user_input,
    resolve_confirmation,
    generate_summary_text,
    COMPLETION_MESSAGE,
    SESSION_ENDED_MESSAGE,
    is_polite_phrase,
    get_polite_response,
    is_end_session_intent,
)
from nlu import get_parser
from guardrails import check_input, check_output, get_guardrail_message
from memory import should_compress, compress_transcript, get_recent_turns
from tools import detect_tool_intent, execute_tool

logger = logging.getLogger(__name__)


async def handle_ws_session(websocket: WebSocket, session_id: str, mgr: SessionManager):
    """Main WebSocket event loop for a planning session."""
    parser = get_parser()

    mgr.add_connection(session_id, websocket)

    try:
        session_data = mgr.get_session(session_id)
        if not session_data["transcript"]:
            # Send greeting only if this is the very first connection
            greeting = get_greeting()
            mgr.add_transcript(session_id, "maya", greeting, True)

            from maya_schema.state import get_next_empty_slot
            state = mgr.get_state(session_id)
            first_slot = get_next_empty_slot(state)
            mgr.set_current_slot(session_id, first_slot)

            await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": greeting})
        else:
            # Reconnection — send restored session state
            state = mgr.get_state(session_id)
            recent = get_recent_turns(session_data["transcript"])
            await _send(websocket, EventType.SERVER_SESSION_RESTORED, session_id, {
                "state": state,
                "transcript": recent,
                "summary": session_data.get("conversation_summary", ""),
            })

        # Main loop
        while True:
            raw = await websocket.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")
            payload = event.get("payload", {})

            if event_type == EventType.CLIENT_SPEECH_STARTED:
                # Fast VAD signal — broadcast to instantly cut off agent TTS
                await mgr.broadcast(session_id, EventType.CLIENT_SPEECH_STARTED, {})

            elif event_type == EventType.CLIENT_TRANSCRIPT_PARTIAL:
                text = payload.get("text", "")
                await mgr.broadcast(session_id, EventType.CLIENT_TRANSCRIPT_PARTIAL, {"text": text})

            elif event_type == EventType.CLIENT_IDLE_TIMEOUT:
                current_slot = mgr.get_current_slot(session_id)
                if current_slot:
                    fallback_msg = f"Are you still there? {get_slot_prompt(current_slot)}"
                    mgr.add_transcript(session_id, "maya", fallback_msg, True)
                    await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": fallback_msg})
                # No response needed if completed

            elif event_type == EventType.CLIENT_TRANSCRIPT_FINAL:
                text = payload.get("text", "")
                if not text.strip():
                    continue

                # ── Guardrail check ─────────────────────────
                guard_result = check_input(text)
                if not guard_result.safe:
                    msg = get_guardrail_message(guard_result.reason)
                    await mgr.broadcast(session_id, EventType.SERVER_GUARDRAIL_BLOCKED, {
                        "reason": guard_result.reason,
                        "message": msg,
                    })
                    continue

                text = guard_result.filtered_text.strip()  # PII-redacted
                
                # Check for empty or purely silent whisper hallucinations
                if not text or len(text) < 2:
                    logger.info(f"Ignoring empty or noise transcript: '{text}'")
                    continue

                # ── Broadcast user transcript to all clients ──
                await mgr.broadcast(session_id, EventType.CLIENT_TRANSCRIPT_FINAL, {"text": text})

                mgr.add_transcript(session_id, "user", text, True)
                mgr.increment_turn_count(session_id)
                state = mgr.get_state(session_id)
                current_slot = mgr.get_current_slot(session_id)
                pending = mgr.get_pending_confirmation(session_id)

                # ── Tool detection ──────────────────────────
                tool_name = detect_tool_intent(text)
                if tool_name:
                    tool_result = await execute_tool(tool_name, {}, state)
                    if tool_result["success"]:
                        tool_msg = tool_result["result"].get("message", "Done!")
                        mgr.add_transcript(session_id, "maya", tool_msg, True)
                        await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": tool_msg})
                    else:
                        await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {
                            "text": f"Sorry, I couldn't do that right now. {tool_result.get('error', '')}",
                        })
                    continue

                # ── Polite / social phrase handling ─────────
                if is_polite_phrase(text) and not pending:
                    polite_ack = get_polite_response()
                    if current_slot:
                        response = f"{polite_ack} {get_slot_prompt(current_slot)}"
                    else:
                        response = f"{polite_ack} {COMPLETION_MESSAGE}"
                    mgr.add_transcript(session_id, "maya", response, True)
                    await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": response})
                    continue

                # ── Conversation logic ──────────────────────
                start_t = time.perf_counter()
                if pending:
                    parsed = await parser.parse(text, pending["slot"], state)
                    intent = parsed["intent"]
                    if intent in ("confirm", "set"):
                        intent = "add"
                    if intent == "deny":
                        intent = "replace"

                    ops, conf_text = resolve_confirmation(
                        intent, pending["slot"],
                        pending["existing_values"],
                        pending["new_values"],
                        state,
                    )

                    if ops:
                        new_state = mgr.apply_state_patch(session_id, ops)
                        await mgr.broadcast(session_id, EventType.SERVER_STATE_PATCH, {"ops": ops, "state": new_state})

                    mgr.set_pending_confirmation(session_id, None)

                    from maya_schema.state import get_next_empty_slot as _gns
                    new_state = mgr.get_state(session_id)
                    next_slot = _gns(new_state)
                    mgr.set_current_slot(session_id, next_slot)

                    response = conf_text
                    if next_slot:
                        response += " " + get_slot_prompt(next_slot)
                    else:
                        response += " " + COMPLETION_MESSAGE

                    # Guardrail output check
                    out_check = check_output(response)
                    response = out_check.filtered_text

                    mgr.add_transcript(session_id, "maya", response, True)
                    await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": response})
                    duration_ms = (time.perf_counter() - start_t) * 1000
                    logger.info(f"[METRICS] Orchestrator Turn (Confirm) duration: {duration_ms:.1f}ms")

                    # Background memory compression
                    asyncio.create_task(_maybe_compress_memory(session_id, mgr))
                    continue

                if not current_slot:
                    # All slots filled — check if user wants to end the session
                    if is_end_session_intent(text):
                        mgr.add_transcript(session_id, "maya", SESSION_ENDED_MESSAGE, True)
                        await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": SESSION_ENDED_MESSAGE})
                        # Signal the frontend to end the session
                        await mgr.broadcast(session_id, "server.session.ended", {})
                    else:
                        # User said something else after completion — invite them again
                        mgr.add_transcript(session_id, "maya", COMPLETION_MESSAGE, True)
                        await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": COMPLETION_MESSAGE})
                    continue

                parsed = await parser.parse(text, current_slot, state)
                result = process_user_input(text, current_slot, parsed, state)

                if result["needs_confirmation"]:
                    mgr.set_pending_confirmation(session_id, result["confirmation_request"])
                    mgr.add_transcript(session_id, "maya", result["confirmation_request"]["message"], True)
                    await mgr.broadcast(session_id, EventType.SERVER_CONFIRMATION_REQUEST, result["confirmation_request"])
                    continue

                if result["patch_ops"]:
                    new_state = mgr.apply_state_patch(session_id, result["patch_ops"])
                    await mgr.broadcast(session_id, EventType.SERVER_STATE_PATCH, {"ops": result["patch_ops"], "state": new_state})

                mgr.set_current_slot(session_id, result["next_slot"])

                response_parts = []
                if result["confirmation_text"]:
                    response_parts.append(result["confirmation_text"])
                if result["next_prompt"]:
                    response_parts.append(result["next_prompt"])
                response = " ".join(response_parts)

                if response:
                    out_check = check_output(response)
                    response = out_check.filtered_text

                    mgr.add_transcript(session_id, "maya", response, True)
                    await mgr.broadcast(session_id, EventType.SERVER_PROMPT, {"text": response})
                    duration_ms = (time.perf_counter() - start_t) * 1000
                    logger.info(f"[METRICS] Orchestrator Turn (Process) duration: {duration_ms:.1f}ms")

                # Background memory compression
                asyncio.create_task(_maybe_compress_memory(session_id, mgr))

            elif event_type == EventType.CLIENT_STATE_UPDATE:
                op = payload.get("op")
                slot = payload.get("slot")
                value = payload.get("value")
                state = mgr.get_state(session_id)

                if op == "add" and slot and value:
                    pointer = dotted_to_pointer(slot)
                    ops = create_add_patch(pointer, [value])
                    new_state = mgr.apply_state_patch(session_id, ops)
                    await mgr.broadcast(session_id, EventType.SERVER_STATE_PATCH, {"ops": ops, "state": new_state})

                elif op == "remove" and slot and value:
                    pointer = dotted_to_pointer(slot)
                    current = get_nested(state, slot) or []
                    ops = create_remove_patch(pointer, [value], current)
                    if ops:
                        new_state = mgr.apply_state_patch(session_id, ops)
                        await mgr.broadcast(session_id, EventType.SERVER_STATE_PATCH, {"ops": ops, "state": new_state})

            elif event_type == EventType.CLIENT_BARGE_IN:
                last_sentence = payload.get("last_spoken_sentence", "")
                mgr.add_spoken_sentence(session_id, last_sentence)
                if last_sentence:
                    mgr.add_transcript(session_id, "system", f"[Maya interrupted after: \"{last_sentence}\"]", True)
                await mgr.broadcast(session_id, EventType.SERVER_SPEECH_INTERRUPTED, {
                    "last_spoken_sentence": last_sentence,
                })
                logger.info(f"Barge-in: Maya interrupted after: {last_sentence}")

            elif event_type == EventType.CLIENT_AUDIO_STARTED:
                pass  # Acknowledged

    finally:
        mgr.remove_connection(session_id, websocket)


async def _maybe_compress_memory(session_id: str, mgr: SessionManager):
    """Background task to compress conversation memory if needed."""
    try:
        turn_count = mgr.get_turn_count(session_id)
        if should_compress(turn_count):
            session = mgr.get_session(session_id)
            transcript = session.get("transcript", [])
            # Compress all but the most recent turns
            old_turns = transcript[:-6] if len(transcript) > 6 else []
            if old_turns:
                summary = compress_transcript(old_turns)
                mgr.set_conversation_summary(session_id, summary)
                logger.info(f"Compressed {len(old_turns)} turns into summary for {session_id}")
    except Exception as e:
        logger.error(f"Memory compression failed: {e}")


async def _send(websocket: WebSocket, event_type: str, session_id: str, payload: dict[str, Any]):
    """Send a typed event to a specific client (used for session restore on reconnect)."""
    event = create_event(event_type, session_id, payload)
    await websocket.send_text(json.dumps(event))
