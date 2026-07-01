"""Oceansat-3 connector (ISRO/MOSDAC) — architecture-ready stub."""

from __future__ import annotations

from data.ingestion.connectors._stub_base import StubConnector


class OceansatConnector(StubConnector):
    """Registered Oceansat connector; live MOSDAC API access is currently limited."""

    DATASET_NAME = "oceansat"
