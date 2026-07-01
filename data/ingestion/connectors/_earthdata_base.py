"""Shared base for NASA Earthdata-authenticated connectors (MODIS/GPM/SMAP).

These datasets are distributed through NASA Earthdata / GES DISC and require a
bearer token, read from :class:`config.settings.Settings.earthdata_token`
(never hardcoded). This base centralizes token resolution and the granule
download + metadata flow so each concrete connector only declares its product
and URL layout.
"""

from __future__ import annotations

from typing import Any

from data.ingestion.base import BaseDatasetConnector
from data.ingestion.download_manager import DownloadResult
from utils.exceptions import MissingCredentialsError


class EarthdataConnector(BaseDatasetConnector):
    """Base class for connectors authenticating against NASA Earthdata.

    Subclasses must define :attr:`DATASET_NAME`, :attr:`FILE_EXTENSION`, and
    implement :meth:`_granule_url`.
    """

    #: File extension used for stored granules (e.g. ``".hdf"``, ``".h5"``).
    FILE_EXTENSION: str = ".dat"

    def _earthdata_headers(self) -> dict[str, str]:
        """Return the Earthdata bearer-auth headers.

        Raises:
            MissingCredentialsError: If no Earthdata token is configured.
        """
        token = self._settings.earthdata_token
        if not token:
            raise MissingCredentialsError(
                "NASA Earthdata token not configured; set CDT_EARTHDATA_TOKEN",
                details={"dataset": self.name},
            )
        return {"Authorization": f"Bearer {token}"}

    def _granule_url(self, product: str, iso_date: str) -> str:
        """Build the download URL for a single granule.

        Args:
            product: The dataset product short-name.
            iso_date: The ``YYYY-MM-DD`` acquisition date.

        Returns:
            A fully-qualified granule download URL.
        """
        raise NotImplementedError

    def download(
        self,
        *,
        variables: list[str] | None = None,
        dates: list[str] | None = None,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download the most recent granule for the requested window.

        Args:
            variables: Variables to derive; defaults to all available.
            dates: ISO dates; the latest is used to select a granule.
            **kwargs: Unused; accepted for interface compatibility.

        Returns:
            A :class:`DownloadResult` for the stored granule.

        Raises:
            MissingCredentialsError: If no Earthdata token is configured.
        """
        headers = self._earthdata_headers()
        resolved_vars = self._resolve_variables(variables)
        resolved_dates = list(dates) if dates else list(self.available_dates())
        target_date = max(resolved_dates)
        product = str(self._descriptor.default_params.get("product", self.name))

        url = self._granule_url(product, target_date)
        filename = f"{self.name}_{product}_{target_date}{self.FILE_EXTENSION}"
        dest = self._raw_path(filename)

        self._logger.info("Requesting %s granule %s for %s", self.name, product, target_date)
        result = self._downloader.download(url, dest, headers=headers)
        return self._finalize_download(
            result, variables=resolved_vars, dates=resolved_dates, version=product
        )
