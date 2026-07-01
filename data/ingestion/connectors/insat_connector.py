"""INSAT-3D/3DR connector (ISRO/MOSDAC) — architecture-ready stub."""

from __future__ import annotations

from data.ingestion.connectors._stub_base import StubConnector


class INSATConnector(StubConnector):
    """Registered INSAT connector; live MOSDAC API access is currently limited."""

    DATASET_NAME = "insat"
