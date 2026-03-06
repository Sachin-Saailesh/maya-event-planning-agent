"""
Persistent storage layer for Maya voice agent.
Async SQLAlchemy models for sessions, transcripts, and conversation summaries.
"""
from __future__ import annotations

import os
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Try to import async database dependencies ──────────────────────
_DB_AVAILABLE = False
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy import String, Text, Float, JSON, select
    _DB_AVAILABLE = True
except ImportError:
    logger.info("SQLAlchemy not installed — database persistence disabled")


# ── Models ─────────────────────────────────────────────────────────

if _DB_AVAILABLE:
    class Base(DeclarativeBase):
        pass

    class SessionModel(Base):
        __tablename__ = "sessions"

        id: Mapped[str] = mapped_column(String(36), primary_key=True)
        state: Mapped[dict] = mapped_column(JSON, default=dict)
        summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        conversation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        created_at: Mapped[float] = mapped_column(Float, default=time.time)
        updated_at: Mapped[float] = mapped_column(Float, default=time.time)

    class TranscriptModel(Base):
        __tablename__ = "transcripts"

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        session_id: Mapped[str] = mapped_column(String(36), index=True)
        speaker: Mapped[str] = mapped_column(String(10))
        text: Mapped[str] = mapped_column(Text)
        is_final: Mapped[bool] = mapped_column(default=True)
        ts: Mapped[float] = mapped_column(Float, default=time.time)

    class ConversationSummaryModel(Base):
        __tablename__ = "conversation_summaries"

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        session_id: Mapped[str] = mapped_column(String(36), index=True)
        summary: Mapped[str] = mapped_column(Text)
        turn_count: Mapped[int] = mapped_column(default=0)
        ts: Mapped[float] = mapped_column(Float, default=time.time)


# ── Database Manager ──────────────────────────────────────────────

class DatabaseManager:
    """Async database manager for persistent session storage."""

    def __init__(self, database_url: str = None):
        self._enabled = _DB_AVAILABLE
        self._engine = None
        self._session_factory = None

        if not self._enabled:
            return

        url = database_url or os.getenv("DATABASE_URL", "")
        if not url:
            self._enabled = False
            return

        try:
            self._engine = create_async_engine(url, echo=False)
            self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        except Exception as e:
            logger.error(f"Database init failed: {e}")
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def create_tables(self):
        """Create all tables if they don't exist."""
        if not self._enabled:
            return
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")

    async def save_session(self, session_id: str, state: dict, summary: str = None,
                           conversation_summary: str = None):
        """Save or update a session in the database."""
        if not self._enabled:
            return
        try:
            async with self._session_factory() as db:
                existing = await db.get(SessionModel, session_id)
                if existing:
                    existing.state = state
                    existing.summary = summary
                    existing.conversation_summary = conversation_summary
                    existing.updated_at = time.time()
                else:
                    session = SessionModel(
                        id=session_id,
                        state=state,
                        summary=summary,
                        conversation_summary=conversation_summary,
                    )
                    db.add(session)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    async def load_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Load a session from the database."""
        if not self._enabled:
            return None
        try:
            async with self._session_factory() as db:
                session = await db.get(SessionModel, session_id)
                if session:
                    return {
                        "id": session.id,
                        "state": session.state,
                        "summary": session.summary,
                        "conversation_summary": session.conversation_summary,
                        "created_at": session.created_at,
                        "updated_at": session.updated_at,
                    }
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
        return None

    async def save_transcript(self, session_id: str, speaker: str, text: str, is_final: bool):
        """Save a transcript entry."""
        if not self._enabled:
            return
        try:
            async with self._session_factory() as db:
                entry = TranscriptModel(
                    session_id=session_id,
                    speaker=speaker,
                    text=text,
                    is_final=is_final,
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")

    async def load_transcripts(self, session_id: str) -> list[dict[str, Any]]:
        """Load all transcripts for a session."""
        if not self._enabled:
            return []
        try:
            async with self._session_factory() as db:
                result = await db.execute(
                    select(TranscriptModel)
                    .where(TranscriptModel.session_id == session_id)
                    .order_by(TranscriptModel.ts)
                )
                rows = result.scalars().all()
                return [
                    {"speaker": r.speaker, "text": r.text, "is_final": r.is_final, "ts": r.ts}
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Failed to load transcripts: {e}")
        return []

    async def save_conversation_summary(self, session_id: str, summary: str, turn_count: int):
        """Save a rolling conversation summary."""
        if not self._enabled:
            return
        try:
            async with self._session_factory() as db:
                entry = ConversationSummaryModel(
                    session_id=session_id,
                    summary=summary,
                    turn_count=turn_count,
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save conversation summary: {e}")
