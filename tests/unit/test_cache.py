"""Unit tests for storage.cache."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from storage.cache.disk_cache import DiskCache
from storage.cache.memory_cache import MemoryCache
from storage.cache.raster_cache import RasterCache


def test_memory_cache_set_get_roundtrip() -> None:
    cache: MemoryCache[str] = MemoryCache(default_ttl_seconds=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_memory_cache_expires() -> None:
    cache: MemoryCache[str] = MemoryCache(default_ttl_seconds=60)
    cache.set("key1", "value1", ttl_seconds=-1)
    assert cache.get("key1") is None


def test_memory_cache_invalidate_prefix() -> None:
    cache: MemoryCache[str] = MemoryCache(default_ttl_seconds=60)
    cache.set("v1:region:IN-TN", "a")
    cache.set("v1:region:IN-KA", "b")
    cache.set("v2:region:IN-TN", "c")
    cache.invalidate_prefix("v1:")
    assert cache.get("v1:region:IN-TN") is None
    assert cache.get("v1:region:IN-KA") is None
    assert cache.get("v2:region:IN-TN") == "c"


def test_disk_cache_set_get_roundtrip(tmp_path: Path) -> None:
    cache = DiskCache(cache_dir=tmp_path)
    cache.set("mykey", {"a": 1, "b": [1, 2, 3]}, ttl_seconds=60)
    result = cache.get("mykey")
    assert result == {"a": 1, "b": [1, 2, 3]}


def test_disk_cache_expires(tmp_path: Path) -> None:
    cache = DiskCache(cache_dir=tmp_path)
    cache.set("mykey", "value", ttl_seconds=-1)
    assert cache.get("mykey") is None


def test_disk_cache_invalidate(tmp_path: Path) -> None:
    cache = DiskCache(cache_dir=tmp_path)
    cache.set("mykey", "value", ttl_seconds=60)
    cache.invalidate("mykey")
    assert cache.get("mykey") is None


def test_raster_cache_set_get_roundtrip(tmp_path: Path) -> None:
    cache = RasterCache(cache_dir=tmp_path)
    array = np.random.rand(10, 10).astype(np.float32)
    cache.set("state1:temperature_2m", array)
    result = cache.get("state1:temperature_2m")
    assert result is not None
    np.testing.assert_array_equal(result, array)


def test_raster_cache_missing_key_returns_none(tmp_path: Path) -> None:
    cache = RasterCache(cache_dir=tmp_path)
    assert cache.get("nonexistent") is None
