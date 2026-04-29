"""
Semantic NLU parse-result cache.

OrderedDict LRU keyed by sha256(slot:normalized_text)[:16].
TTL = 3600 s, max = 512 entries.
Only consulted when NLU_BACKEND=llm — the rule-based path is fast enough
that caching adds no value there.
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)

_MAX_SIZE = 512
_TTL = 3600  # seconds


def _make_key(slot: str, text: str) -> str:
    # Normalise: lowercase + collapse whitespace + strip punctuation
    normalized = " ".join(text.lower().split())
    raw = f"{slot}:{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class SemanticCache:
    """
    LRU in-process cache for LLM NLU parse results.

    Avoids redundant gpt-4o-mini calls when the same user phrasing is
    seen again for the same slot (common across sessions for colour/flower
    names like "gold and maroon" or "jasmine").
    """

    def __init__(self, max_size: int = _MAX_SIZE, ttl: int = _TTL):
        self._max_size = max_size
        self._ttl = ttl
        self._store: OrderedDict[str, tuple[dict[str, Any], float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    # ── Public API ────────────────────────────────────────────────

    def get(self, slot: str, text: str) -> dict[str, Any] | None:
        """Return cached parse result or None on miss / expiry."""
        key = _make_key(slot, text)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        result, ts = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            self._misses += 1
            return None
        self._store.move_to_end(key)
        self._hits += 1
        logger.debug("[SEMANTIC_CACHE] hit slot=%s key=%s", slot, key)
        return result

    def put(self, slot: str, text: str, result: dict[str, Any]) -> None:
        """Store a parse result. Evicts the oldest entry if over capacity."""
        key = _make_key(slot, text)
        self._store[key] = (result, time.time())
        self._store.move_to_end(key)
        if len(self._store) > self._max_size:
            evicted = self._store.popitem(last=False)
            logger.debug("[SEMANTIC_CACHE] evicted key=%s", evicted[0])

    # ── Diagnostics ───────────────────────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return round(self._hits / total, 3) if total else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "size": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }

    def __len__(self) -> int:
        return len(self._store)
