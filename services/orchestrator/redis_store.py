"""
Redis session cache for Maya voice agent.
Provides fast session state snapshots for reconnection.
Degrades gracefully if Redis is not available.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_REDIS_AVAILABLE = False
try:
    import redis.asyncio as aioredis
    _REDIS_AVAILABLE = True
except ImportError:
    logger.info("redis package not installed — Redis caching disabled")


class RedisStore:
    """Async Redis store for active session caching."""

    def __init__(self, redis_url: str = None):
        self._enabled = _REDIS_AVAILABLE
        self._client = None
        self._ttl = int(os.getenv("REDIS_SESSION_TTL", "3600"))  # 1 hour default

        if not self._enabled:
            return

        url = redis_url or os.getenv("REDIS_URL", "")
        if not url:
            self._enabled = False
            return

        try:
            self._client = aioredis.from_url(url, decode_responses=True)
        except Exception as e:
            logger.error(f"Redis init failed: {e}")
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def ping(self) -> bool:
        """Check if Redis is reachable."""
        if not self._enabled:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def save_session_snapshot(self, session_id: str, snapshot: dict[str, Any]):
        """Cache session state snapshot for fast reconnection."""
        if not self._enabled:
            return
        try:
            key = f"maya:session:{session_id}"
            await self._client.setex(key, self._ttl, json.dumps(snapshot, default=str))
        except Exception as e:
            logger.error(f"Redis save failed: {e}")

    async def get_session_snapshot(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get cached session snapshot."""
        if not self._enabled:
            return None
        try:
            key = f"maya:session:{session_id}"
            data = await self._client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
        return None

    async def delete_session(self, session_id: str):
        """Remove session from cache."""
        if not self._enabled:
            return
        try:
            key = f"maya:session:{session_id}"
            await self._client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
