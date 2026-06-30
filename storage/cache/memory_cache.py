"""In-process memory cache for hot, small, frequently reused objects.

Per SAD Section 15 (Memory Cache row), this backs region lookups and the
current-state pointer. Larger payloads belong in :mod:`storage.cache.disk_cache`
or :mod:`storage.cache.raster_cache` instead.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

from config.constants import DEFAULT_CACHE_TTL_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class MemoryCache(Generic[T]):
    """A small, thread-safe, TTL-based in-memory cache.

    Args:
        default_ttl_seconds: Default time-to-live applied when ``set`` is
            called without an explicit ``ttl_seconds``.
    """

    def __init__(self, default_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> None:
        self._store: dict[str, _CacheEntry[T]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl_seconds

    def get(self, key: str) -> T | None:
        """Retrieve a cached value if present and not expired.

        Args:
            key: Cache key.

        Returns:
            The cached value, or ``None`` if missing/expired.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: T, ttl_seconds: int | None = None) -> None:
        """Store a value with a time-to-live.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl_seconds: Optional override TTL; falls back to the default.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        with self._lock:
            self._store[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    def invalidate(self, key: str) -> None:
        """Remove a single key from the cache, if present.

        Args:
            key: Cache key to remove.
        """
        with self._lock:
            self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Remove all keys starting with ``prefix``.

        Used to invalidate every cache entry tied to a stale ``ClimateState``
        version (SAD Section 15: "All caches are invalidated by ClimateState
        version change").

        Args:
            prefix: Key prefix to match for removal.
        """
        with self._lock:
            stale_keys = [k for k in self._store if k.startswith(prefix)]
            for k in stale_keys:
                del self._store[k]
            if stale_keys:
                logger.debug(
                    "Invalidated %d memory cache entries with prefix '%s'", len(stale_keys), prefix
                )

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._store.clear()
