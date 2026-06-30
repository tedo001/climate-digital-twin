"""Raster-specific disk cache.

Per SAD Section 15 (Map Cache / large raster handling), raster payloads are
cached separately from generic pickled objects because they are large,
homogeneous NumPy arrays best stored via ``numpy.save`` rather than pickling
through :mod:`storage.cache.disk_cache`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from config.paths import RASTER_CACHE_DIR
from utils.exceptions import CacheError
from utils.logger import get_logger

logger = get_logger(__name__)


class RasterCache:
    """Disk cache specialized for NumPy raster arrays.

    Cache keys should always incorporate the owning ``ClimateState`` version
    ID to guarantee freshness correctness (SAD Section 15).

    Args:
        cache_dir: Directory in which raster arrays are stored as ``.npy`` files.
    """

    def __init__(self, cache_dir: Path = RASTER_CACHE_DIR) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.npy"

    def get(self, key: str) -> np.ndarray | None:
        """Retrieve a cached raster array, if present.

        Args:
            key: Cache key, typically ``f"{state_id}:{variable_name}"``.

        Returns:
            The cached :class:`numpy.ndarray`, or ``None`` if absent.
        """
        path = self._path_for_key(key)
        if not path.exists():
            return None
        try:
            return np.load(path, allow_pickle=False)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to load raster cache entry for key '%s': %s", key, exc)
            return None

    def set(self, key: str, array: np.ndarray) -> None:
        """Store a raster array on disk.

        Args:
            key: Cache key, typically ``f"{state_id}:{variable_name}"``.
            array: The NumPy array to persist.

        Raises:
            CacheError: If the array cannot be written to disk.
        """
        path = self._path_for_key(key)
        try:
            np.save(path, array, allow_pickle=False)
        except OSError as exc:
            raise CacheError("Failed to write raster cache entry", details={"key": key}) from exc

    def invalidate(self, key: str) -> None:
        """Remove a single raster cache entry, if present.

        Args:
            key: Cache key to remove.
        """
        self._path_for_key(key).unlink(missing_ok=True)

    def invalidate_state_version(self, state_id: str) -> None:
        """Remove every cached raster tied to a specific state version.

        Args:
            state_id: The ``ClimateState.state_id`` whose rasters should be purged.
        """
        # Keys are hashed, so we cannot pattern-match filenames directly;
        # callers that need bulk invalidation should track keys per state_id
        # externally (e.g. via climate.state_manager) and call invalidate()
        # per key. This method is a documented no-op placeholder hook for
        # that bookkeeping rather than a silent partial implementation.
        logger.debug(
            "invalidate_state_version called for %s; callers must invalidate tracked keys explicitly",
            state_id,
        )
