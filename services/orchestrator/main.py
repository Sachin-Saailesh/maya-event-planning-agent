"""
Maya Orchestrator — FastAPI application.
REST + WebSocket endpoints for session management and real-time voice interaction.
"""
from __future__ import annotations

import os
import uuid
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from session_manager import SessionManager
from ws_handler import handle_ws_session
from conversation import generate_summary_text

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    app.state.session_mgr = SessionManager()

    # Initialize database (optional, degrades gracefully)
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        if db.enabled:
            await db.create_tables()
            app.state.db = db
            logger.info("Database connected and tables ready")
        else:
            app.state.db = None
    except Exception as e:
        logger.info(f"Database not available: {e}")
        app.state.db = None

    # Initialize Redis (optional, degrades gracefully)
    try:
        from redis_store import RedisStore
        redis = RedisStore()
        if redis.enabled and await redis.ping():
            app.state.redis = redis
            logger.info("Redis connected")
        else:
            app.state.redis = None
    except Exception as e:
        logger.info(f"Redis not available: {e}")
        app.state.redis = None

    # Initialize RAG memory (optional)
    try:
        from rag import RAGMemory
        rag = RAGMemory()
        app.state.rag = rag if rag.enabled else None
    except Exception as e:
        app.state.rag = None

    yield

    # Cleanup
    if getattr(app.state, "redis", None):
        await app.state.redis.close()


app = FastAPI(title="Maya Orchestrator", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST endpoints ─────────────────────────────────────────────────

from livekit import api


@app.post("/session")
async def create_session():
    """Create a new planning session."""
    mgr: SessionManager = app.state.session_mgr
    session_id = str(uuid.uuid4())
    session = mgr.create_session(session_id)

    # Generate LiveKit token for the client
    token = api.AccessToken(
        os.getenv("LIVEKIT_API_KEY", "devkey"),
        os.getenv("LIVEKIT_API_SECRET", "secret"),
    )
    token.with_identity(f"user-{session_id[:8]}")
    token.with_name("Maya Planner User")
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=session_id,
        can_publish=True,
        can_subscribe=True,
    ))

    return {
        "session_id": session_id,
        "state": session["state"],
        "livekit_token": token.to_jwt(),
        "livekit_url": os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session state, transcript, and summary."""
    mgr: SessionManager = app.state.session_mgr
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "state": session["state"],
        "transcript": session["transcript"],
        "summary": session.get("summary"),
        "conversation_summary": session.get("conversation_summary", ""),
    }


@app.get("/session/{session_id}/snapshot")
async def get_session_snapshot(session_id: str):
    """
    Get session snapshot for reconnection.
    Returns state, summary, and recent transcripts.
    """
    mgr: SessionManager = app.state.session_mgr

    # Try Redis cache first
    if getattr(app.state, "redis", None):
        cached = await app.state.redis.get_session_snapshot(session_id)
        if cached:
            return cached

    # Fall back to in-memory
    snapshot = mgr.get_snapshot(session_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Session not found")
    return snapshot


@app.post("/session/{session_id}/export")
async def export_session(session_id: str):
    """Generate and return the decor brief."""
    mgr: SessionManager = app.state.session_mgr
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    summary = generate_summary_text(session["state"])
    mgr.set_summary(session_id, summary)

    # Persist to database
    db = getattr(app.state, "db", None)
    if db:
        await db.save_session(session_id, session["state"], summary,
                              session.get("conversation_summary"))

    return {
        "session_id": session_id,
        "summary_text": summary,
        "state": session["state"],
    }


# ── TTS endpoint (bypasses browser speechSynthesis WebRTC lock) ───

from fastapi.responses import StreamingResponse

@app.get("/tts")
async def text_to_speech(text: str):
    """
    Convert text to speech using OpenAI TTS.
    Returns audio/mpeg bytes — played by HTMLAudioElement
    which is immune to the macOS WebRTC/speechSynthesis hardware mutex.
    """
    from openai import AsyncOpenAI
    from fastapi.responses import Response

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = await client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="mp3",
    )

    # .content gives the raw MP3 bytes directly
    audio_bytes = response.content

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )


# ── WebSocket endpoint ────────────────────────────────────────────

@app.websocket("/ws/session/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str):
    """Real-time bidirectional communication for a planning session."""
    mgr: SessionManager = app.state.session_mgr
    session = mgr.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    await websocket.accept()
    try:
        await handle_ws_session(websocket, session_id, mgr)
    except WebSocketDisconnect:
        pass
