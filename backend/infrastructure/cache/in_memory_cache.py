import time
from typing import Any, Optional


class InMemoryCache:
    """Simple in-memory cache with TTL support.
    Not shared across gunicorn workers — each worker has its own instance.
    For production with multiple workers, use RedisCache instead.
    """

    def __init__(self):
        self._store: dict[str, dict] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry["ttl"] is not None and time.time() - entry["timestamp"] > entry["ttl"]:
            del self._store[key]
            return None
        return entry["data"]

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        self._store[key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": ttl,
        }

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# Singleton for app-wide use
cache = InMemoryCache()
