"""Unified cache manager facade.

Combines :class:`MemoryCache`, :class:`DiskCache`, and :class:`RasterCache`
behind one dependency-injectable object so callers don't need to wire three
separate caches by hand. All cache keys should incorporate the current
``ClimateState`` version per SAD Section 15.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from storage.cache.disk_cache import DiskCache
from storage.cache.memory_cache import MemoryCache
from storage.cache.raster_cache import RasterCache
from utils.decorators import memoize
from utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Facade exposing memory, disk, and raster caches through one interface.

    Args:
        memory_cache: Injected memory cache instance.
        disk_cache: Injected disk cache instance.
        raster_cache: Injected raster cache instance.
    """

    def __init__(
        self,
        memory_cache: MemoryCache[Any] | None = None,
        disk_cache: DiskCache | None = None,
        raster_cache: RasterCache | None = None,
    ) -> None:
        self.memory = memory_cache or MemoryCache()
        self.disk = disk_cache or DiskCache()
        self.raster = raster_cache or RasterCache()

    @staticmethod
    def versioned_key(state_version: str, *parts: str) -> str:
        """Build a cache key that incorporates the state version for freshness.

        Args:
            state_version: Current ``ClimateState.state_id``.
            *parts: Additional key components (e.g. region, variable, horizon).

        Returns:
            A colon-joined cache key string.
        """
        return ":".join([state_version, *parts])

    def get_or_compute_disk(self, key: str, compute_fn: Any, ttl_seconds: int | None = None) -> Any:
        """Return a disk-cached value, computing and storing it if absent.

        Args:
            key: Cache key.
            compute_fn: Zero-argument callable producing the value on a cache miss.
            ttl_seconds: Optional TTL override.

        Returns:
            The cached or freshly computed value.
        """
        cached = self.disk.get(key)
        if cached is not None:
            return cached
        value = compute_fn()
        self.disk.set(key, value, ttl_seconds=ttl_seconds)
        return value

    def get_or_compute_raster(self, key: str, compute_fn: Any) -> np.ndarray:
        """Return a raster-cached array, computing and storing it if absent.

        Args:
            key: Cache key, typically including state version + variable name.
            compute_fn: Zero-argument callable producing the array on a cache miss.

        Returns:
            The cached or freshly computed :class:`numpy.ndarray`.
        """
        cached = self.raster.get(key)
        if cached is not None:
            return cached
        array = compute_fn()
        self.raster.set(key, array)
        return array

    def invalidate_all_for_version(self, state_version: str) -> None:
        """Invalidate every memory-cache entry tied to a stale state version.

        Args:
            state_version: The now-stale ``ClimateState.state_id``.
        """
        self.memory.invalidate_prefix(state_version)
        logger.info("Invalidated caches for stale state version %s", state_version)


@memoize
def get_cache_manager() -> CacheManager:
    """Return a process-wide memoized :class:`CacheManager` instance.

    Returns:
        A :class:`CacheManager` singleton, suitable for dependency injection
        into controllers and domain services.
    """
    return CacheManager()
