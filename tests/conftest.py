"""Shared pytest fixtures for the Climate Digital Twin test suite."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_storage_dir(tmp_path: Path) -> Path:
    """Provide an isolated temp directory for storage-layer tests.

    Args:
        tmp_path: Pytest's built-in temp directory fixture.

    Returns:
        A fresh, empty directory unique to the test.
    """
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return storage_dir
