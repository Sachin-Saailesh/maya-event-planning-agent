"""
Maya Orchestrator — FastAPI application.
REST + WebSocket endpoints for session management and real-time voice interaction.
"""
from __future__ import annotations

import hashlib
import os
import uuid
import logging
from collections import OrderedDict
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from session_manager import SessionManager
from ws_handler import handle_ws_session
from conversation import generate_summary_text

logger = logging.getLogger(__name__)

# ── In-process TTS LRU cache ──────────────────────────────────────
# Avoids re-calling OpenAI for identical phrases (greetings, slot prompts).
_TTS_CACHE_MAX = 200
_tts_cache: OrderedDict[str, bytes] = OrderedDict()


def _tts_cache_get(text: str) -> bytes | None:
    key = hashlib.sha256(text.encode()).hexdigest()
    entry = _tts_cache.get(key)
    if entry is None:
        return None
    _tts_cache.move_to_end(key)
    return entry


def _tts_cache_put(text: str, audio: bytes) -> None:
    key = hashlib.sha256(text.encode()).hexdigest()
    _tts_cache[key] = audio
    _tts_cache.move_to_end(key)
    while len(_tts_cache) > _TTS_CACHE_MAX:
        _tts_cache.popitem(last=False)


async def _prewarm_tts():
    """Pre-warm TTS cache for the greeting and first slot prompt at startup."""
    if not os.getenv("OPENAI_API_KEY"):
        return
    try:
        from openai import AsyncOpenAI
        from conversation import get_greeting, get_slot_prompt
        from maya_schema.state import SLOT_PRIORITY

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        phrases = [get_greeting()]
        if SLOT_PRIORITY:
            phrases.append(get_slot_prompt(SLOT_PRIORITY[0]))

        for phrase in phrases:
            if _tts_cache_get(phrase):
                continue
            resp = await client.audio.speech.create(
                model="tts-1", voice="nova", input=phrase, response_format="mp3"
            )
            _tts_cache_put(phrase, resp.content)
            logger.info("[TTS_CACHE] pre-warmed %d chars", len(phrase))
    except Exception as e:
        logger.warning("[TTS_CACHE] pre-warm failed: %s", e)


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

    # Initialize NLU semantic cache (used when NLU_BACKEND=llm)
    try:
        from semantic_cache import SemanticCache
        app.state.semantic_cache = SemanticCache()
        logger.info("SemanticCache initialized (max=512, ttl=3600s)")
    except Exception as e:
        logger.info(f"SemanticCache not available: {e}")
        app.state.semantic_cache = None

    # Pre-warm TTS cache for high-frequency phrases (non-blocking)
    import asyncio
    asyncio.create_task(_prewarm_tts())

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


@app.get("/tts")
async def text_to_speech(text: str):
    """
    Convert text to speech using OpenAI TTS.
    Returns audio/mpeg bytes — played by HTMLAudioElement
    which is immune to the macOS WebRTC/speechSynthesis hardware mutex.
    Responses are cached in-process to avoid redundant API calls.
    """
    from fastapi.responses import Response

    cached = _tts_cache_get(text)
    if cached:
        logger.debug("[TTS_CACHE] hit len=%d", len(text))
        return Response(content=cached, media_type="audio/mpeg", headers={"Cache-Control": "no-cache"})

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="mp3",
    )
    audio_bytes = response.content
    _tts_cache_put(text, audio_bytes)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )


# ── Image generation endpoint ─────────────────────────────────────

from pydantic import BaseModel
import base64

class GenerateRequest(BaseModel):
    state: dict
    hall_id: str
    session_id: str | None = None

@app.post("/generate")
async def generate_image(req: GenerateRequest):
    """
    Build a rich prompt from decor state + hall, call Gemini (Nano Banana)
    via the Google Generative AI SDK, and return the image as a base64
    data-URL so no external CDN is needed.  Response is synchronous —
    status is always "complete".
    """
    import asyncio
    import google.genai as genai
    from google.genai import types as genai_types

    api_key = os.getenv("NANO_BANANA_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Image generation not configured. Set NANO_BANANA_API_KEY.",
        )

    model_id = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    prompt = _build_image_prompt(req.state, req.hall_id)
    logger.info("Image generation — model: %s | prompt: %s", model_id, prompt)

    try:
        client = genai.Client(api_key=api_key)

        # Run blocking SDK call in a thread so we don't block the event loop
        def _call():
            return client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

        response = await asyncio.get_event_loop().run_in_executor(None, _call)

        # Extract the first image part from the response
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                mime = part.inline_data.mime_type or "image/png"
                raw = part.inline_data.data          # bytes
                b64 = base64.b64encode(raw).decode("utf-8")
                return {
                    "image_url": f"data:{mime};base64,{b64}",
                    "job_id": None,
                    "status": "complete",
                    "prompt": prompt,
                }

        raise HTTPException(status_code=502, detail="Gemini returned no image in the response.")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image generation error — model: %s", model_id)
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@app.get("/generate/{job_id}")
async def poll_generation(_job_id: str):
    """
    Gemini image generation is synchronous so this endpoint should never be
    reached in normal operation, but it is kept for forward-compatibility.
    """
    raise HTTPException(
        status_code=410,
        detail="Async polling is not used with the Gemini image backend. "
               "The /generate POST response always has status='complete'.",
    )


# Hall metadata used to enrich generation prompts
# IDs must match HALL_CONFIG in apps/web/src/slotConfig.js
_HALL_DESCRIPTIONS: dict[str, str] = {
    "grand_lotus":    "grand lotus ballroom with high ceilings, crystal chandeliers, ornate gold-leaf pillars and reflective marble floors",
    "amaravathi":     "Amaravathi Palace with stone arches, dark teak ceilings, royal purple and gold silk drapes",
    "sky_pavilion":   "Sky Pavilion with floor-to-ceiling glass walls, minimalist modern spaces, and panoramic views",
    "temple_gardens": "Temple Gardens Estate with an open-air courtyard, carved stone pathways, and ancient banyan trees",
}



def _build_image_prompt(state: dict, hall_id: str) -> str:
    """
    Compose a rich, state-aware prompt for Gemini image generation.
    The output image should be 1920 × 1080 px (16:9, 1080p full-HD).
    Every filled slot contributes visual detail; empty slots are omitted.
    """
    hall_desc = _HALL_DESCRIPTIONS.get(
        hall_id,
        f"{hall_id.replace('_', ' ')} wedding hall",
    )

    # ── opening frame ──────────────────────────────────────────────
    parts = [
        "Generate a single photorealistic 1920x1080 pixel (1080p full-HD, 16:9 widescreen landscape)"
        f" image of a beautifully decorated South Indian wedding venue inside a {hall_desc}.",
        "The scene is captured with professional event photography lighting, wide-angle perspective,"
        " ultra-high detail, and cinematic depth of field.",
    ]

    # ── color palette ──────────────────────────────────────────────
    colors = [c for c in state.get("primary_colors", []) if c]
    if colors:
        parts.append(
            f"The dominant color palette is {', '.join(colors)},"
            " applied consistently to all fabric, florals, and soft furnishings."
        )

    # ── flowers ────────────────────────────────────────────────────
    flowers = [f for f in state.get("types_of_flowers", []) if f]
    if flowers:
        parts.append(
            f"Fresh {', '.join(flowers)} flowers are arranged abundantly throughout—"
            " in centerpieces, arches, hanging installations, and table runners."
        )

    # ── entrance ───────────────────────────────────────────────────
    entrance = state.get("entrance_decor") or {}
    entrance_details: list[str] = []
    if entrance.get("foyer"):
        entrance_details.append(f"foyer styled with {', '.join(entrance['foyer'])}")
    if entrance.get("garlands"):
        entrance_details.append(f"door garlands of {', '.join(entrance['garlands'])}")
    if entrance.get("name_board"):
        entrance_details.append(f"name board decorated with {', '.join(entrance['name_board'])}")
    if entrance.get("top_decor_at_entrance"):
        entrance_details.append(f"overhead entrance arch featuring {', '.join(entrance['top_decor_at_entrance'])}")
    if entrance_details:
        parts.append(f"The entrance showcases {'; '.join(entrance_details)}.")

    # ── backdrop ───────────────────────────────────────────────────
    backdrop = state.get("backdrop_decor") or {}
    if backdrop.get("enabled") and backdrop.get("types"):
        b_types = backdrop["types"]
        type_desc = {
            "flowers":      "a lush floral wall backdrop",
            "pattern":      "an intricately patterned fabric backdrop",
            "flower_lights": "a flower-and-fairy-light backdrop",
        }
        descs = [type_desc.get(t, t) for t in b_types]
        parts.append(f"The stage features {' combined with '.join(descs)} as the main backdrop.")

    # ── lighting ───────────────────────────────────────────────────
    lights = [l for l in state.get("decor_lights", []) if l]
    if lights:
        parts.append(
            f"Atmospheric lighting includes {', '.join(lights)}, creating a warm and festive glow."
        )

    # ── chandeliers ────────────────────────────────────────────────
    chandeliers = [c for c in state.get("chandeliers", []) if c]
    if chandeliers:
        parts.append(
            f"Ornate {', '.join(chandeliers)} chandeliers hang from the ceiling,"
            " casting elegant reflections across the hall."
        )

    # ── traditional props ──────────────────────────────────────────
    props = [p for p in state.get("props", []) if p]
    if props:
        parts.append(
            f"Traditional South Indian props such as {', '.join(props)} are tastefully placed"
            " to enhance the cultural aesthetic."
        )

    # ── selfie booth ───────────────────────────────────────────────
    selfie = [s for s in state.get("selfie_booth_decor", []) if s]
    if selfie and selfie != ["yes"]:
        parts.append(
            f"A stylish selfie booth decorated with {', '.join(selfie)} is positioned"
            " in a prominent corner of the hall."
        )
    elif selfie:
        parts.append("A dedicated selfie booth is included in the hall décor.")

    # ── general hall décor ─────────────────────────────────────────
    hall_decor = [h for h in state.get("hall_decor", []) if h]
    if hall_decor:
        parts.append(
            f"General hall décor features {', '.join(hall_decor)},"
            " adding cohesion and grandeur throughout the space."
        )

    # ── quality footer ─────────────────────────────────────────────
    parts.append(
        "Overall mood: luxurious, grand, culturally rich South Indian wedding."
        " No people in the frame. Output must be exactly 1920×1080 pixels."
    )

    return " ".join(parts)


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
        await handle_ws_session(
            websocket, session_id, mgr,
            rag=getattr(app.state, "rag", None),
            cache=getattr(app.state, "semantic_cache", None),
        )
    except WebSocketDisconnect:
        pass
