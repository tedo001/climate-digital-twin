"""India Meteorological Department connector — architecture-ready stub."""

from __future__ import annotations

from data.ingestion.connectors._stub_base import StubConnector


class IMDConnector(StubConnector):
    """Registered IMD connector; bulk public API access is currently limited."""

    DATASET_NAME = "imd"
