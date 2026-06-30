"""Disk-backed cache for expensive results that should persist across sessions.

Per SAD Section 15 (Disk Cache row), this backs preprocessing results too
expensive to recompute every Streamlit rerun. Backed by ``joblib`` for
robust pickling of NumPy/Pandas/Xarray objects.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import joblib

from config.paths import DISK_CACHE_DIR
from config.settings import get_settings
from utils.exceptions import CacheError
from utils.logger import get_logger

logger = get_logger(__name__)


class DiskCache:
    """A simple, file-based, TTL-aware cache keyed by arbitrary strings.

    Args:
        cache_dir: Directory in which cache entries are stored.
    """

    def __init__(self, cache_dir: Path = DISK_CACHE_DIR) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._settings = get_settings()

    def _path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.joblib"

    def _meta_path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.meta.json"

    def get(self, key: str) -> Any | None:
        """Retrieve a cached value if present and not expired.

        Args:
            key: Cache key.

        Returns:
            The cached value, or ``None`` if missing, expired, or caching disabled.
        """
        if not self._settings.enable_disk_cache:
            return None

        data_path = self._path_for_key(key)
        meta_path = self._meta_path_for_key(key)
        if not data_path.exists() or not meta_path.exists():
            return None

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if meta.get("expires_at", 0) < time.time():
            self.invalidate(key)
            return None

        try:
            return joblib.load(data_path)
        except (OSError, EOFError, ValueError) as exc:
            logger.warning("Failed to load disk cache entry for key '%s': %s", key, exc)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store a value on disk with a time-to-live.

        Args:
            key: Cache key.
            value: A joblib/pickle-serializable value.
            ttl_seconds: Optional override TTL; falls back to settings default.

        Raises:
            CacheError: If serialization to disk fails.
        """
        if not self._settings.enable_disk_cache:
            return

        ttl = ttl_seconds if ttl_seconds is not None else self._settings.cache_ttl_seconds
        data_path = self._path_for_key(key)
        meta_path = self._meta_path_for_key(key)
        try:
            joblib.dump(value, data_path)
            meta_path.write_text(
                json.dumps({"key": key, "expires_at": time.time() + ttl}), encoding="utf-8"
            )
        except OSError as exc:
            raise CacheError("Failed to write disk cache entry", details={"key": key}) from exc

    def invalidate(self, key: str) -> None:
        """Remove a cache entry from disk, if present.

        Args:
            key: Cache key to remove.
        """
        for path in (self._path_for_key(key), self._meta_path_for_key(key)):
            path.unlink(missing_ok=True)

    def clear(self) -> None:
        """Remove every entry from the disk cache directory."""
        for path in self._cache_dir.glob("*"):
            path.unlink(missing_ok=True)
