"""Data-ingestion layer: connectors that download and validate source datasets.

Public entry points:

* :class:`~data.ingestion.base.BaseDatasetConnector` (aliased
  :class:`~data.ingestion.base.BaseDataConnector`) — the abstract base every
  connector extends.
* :class:`~data.ingestion.download_manager.DownloadManager` — the shared,
  retrying, checksum-verifying HTTP downloader.

Concrete connectors live in :mod:`data.ingestion.connectors` and are resolved
lazily via ``config/dataset_registry.yaml`` (their dotted ``connector_class``
paths), so this package need not import them eagerly.
"""

from __future__ import annotations

from data.ingestion.base import BaseDataConnector, BaseDatasetConnector
from data.ingestion.download_manager import (
    DownloadManager,
    DownloadResult,
    ProgressReporter,
    compute_checksum,
)

__all__ = [
    "BaseDataConnector",
    "BaseDatasetConnector",
    "DownloadManager",
    "DownloadResult",
    "ProgressReporter",
    "compute_checksum",
]
