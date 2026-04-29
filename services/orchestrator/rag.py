"""
Long-term memory (RAG) for Maya voice agent.
Uses ChromaDB for vector storage and semantic search over conversation history.
Degrades gracefully if ChromaDB is not installed.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CHROMA_AVAILABLE = False
try:
    import chromadb
    _CHROMA_AVAILABLE = True
except ImportError:
    logger.info("chromadb not installed — RAG long-term memory disabled")


class RAGMemory:
    """Vector-based long-term memory using ChromaDB."""

    def __init__(self, persist_dir: str = None):
        self._enabled = _CHROMA_AVAILABLE
        self._client = None
        self._collection = None

        if not self._enabled:
            return

        try:
            persist = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "/tmp/maya_chroma")
            self._client = chromadb.PersistentClient(path=persist)
            self._collection = self._client.get_or_create_collection(
                name="maya_conversations",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB initialized at {persist}")
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def embed_and_store(self, session_id: str, text_chunk: str, turn_index: int):
        """Embed and store a conversation chunk for later retrieval."""
        if not self._enabled or not text_chunk.strip():
            return

        try:
            doc_id = f"{session_id}_{turn_index}"
            self._collection.upsert(
                ids=[doc_id],
                documents=[text_chunk],
                metadatas=[{
                    "session_id": session_id,
                    "turn_index": turn_index,
                }],
            )
        except Exception as e:
            logger.error(f"RAG embed failed: {e}")

    def semantic_search(self, session_id: str, query: str, top_k: int = 3) -> list[str]:
        """Search for semantically similar conversation chunks."""
        if not self._enabled:
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"session_id": session_id},
            )
            if results and results["documents"]:
                return results["documents"][0]
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
        return []

    def embed_turns(self, session_id: str, turns: list[dict[str, Any]], start_index: int = 0):
        """Embed multiple conversation turns in batch."""
        if not self._enabled:
            return

        for i, turn in enumerate(turns):
            speaker = "User" if turn.get("speaker") == "user" else "Maya"
            text = f"{speaker}: {turn.get('text', '')}"
            self.embed_and_store(session_id, text, start_index + i)

    def semantic_search_with_fallback(
        self,
        session_id: str,
        query: str,
        transcript: list[dict[str, Any]],
        top_k: int = 3,
    ) -> str:
        """
        Cosine-similarity search over stored turns (ChromaDB).
        Falls back to a sliding window of the last 6 transcript turns when:
          - ChromaDB is disabled / unavailable
          - No result passes the distance threshold (< 0.7)

        Returns a formatted context string ready to inject into an LLM prompt.
        Returns empty string if nothing is available.
        """
        if self._enabled:
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where={"session_id": session_id},
                )
                if results and results.get("documents") and results.get("distances"):
                    docs = results["documents"][0]
                    dists = results["distances"][0]
                    # cosine space: distance 0 = identical, 1 = orthogonal
                    relevant = [
                        doc for doc, dist in zip(docs, dists)
                        if dist < 0.7
                    ]
                    if relevant:
                        return "Relevant conversation context:\n" + "\n".join(relevant)
            except Exception as exc:
                logger.warning("RAG cosine search failed, using sliding-window fallback: %s", exc)

        # Sliding-window fallback — last 6 turns from in-memory transcript
        recent = transcript[-6:] if len(transcript) > 6 else transcript
        if not recent:
            return ""
        lines = []
        for turn in recent:
            speaker = "User" if turn.get("speaker") == "user" else "Maya"
            lines.append(f"{speaker}: {turn.get('text', '')}")
        return "Recent conversation:\n" + "\n".join(lines)
