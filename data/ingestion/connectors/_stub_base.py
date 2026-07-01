"""Shared base for architecture-ready connectors without live API access.

INSAT, Oceansat, and IMD are registered and fully wired into the ingestion
architecture, but their upstream public APIs are currently limited. These
connectors therefore expose the full contract — :meth:`metadata`,
:meth:`available_variables`, :meth:`available_dates`, and :meth:`validate` all
work — while :meth:`download` raises :class:`ConnectorNotImplementedError` so
the unavailability is explicit rather than silent (SAD scope note).
"""

from __future__ import annotations

from typing import Any, NoReturn

from data.ingestion.base import BaseDatasetConnector
from utils.exceptions import ConnectorNotImplementedError


class StubConnector(BaseDatasetConnector):
    """Base for registered-but-not-yet-live connectors."""

    def download(
        self,
        *,
        variables: list[str] | None = None,
        dates: list[str] | None = None,
        **kwargs: Any,
    ) -> NoReturn:
        """Raise :class:`ConnectorNotImplementedError` — no live API yet.

        Raises:
            ConnectorNotImplementedError: Always; the architecture is ready but
                the upstream public API is not currently available.
        """
        note = str(self._descriptor.default_params.get("note", "live API unavailable"))
        raise ConnectorNotImplementedError(
            f"Connector '{self.name}' is architecture-ready but not live",
            details={"dataset": self.name, "note": note},
        )
