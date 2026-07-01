"""NASA POWER connector.

Downloads daily agro-climatology point time series from the public NASA POWER
REST API (https://power.larc.nasa.gov/). No credentials are required, which
makes this connector the reference implementation for the ingestion contract.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from data.ingestion.base import BaseDatasetConnector
from data.ingestion.download_manager import DownloadResult

# Map canonical climate-variable identifiers to NASA POWER parameter codes.
_POWER_PARAMETERS: dict[str, str] = {
    "temperature_2m": "T2M",
    "precipitation": "PRECTOTCORR",
    "relative_humidity": "RH2M",
    "wind_speed_10m": "WS10M",
}

# Geographic centroid of India, used when no explicit point is requested.
_DEFAULT_LATITUDE = 22.0
_DEFAULT_LONGITUDE = 79.0


class NASAPowerConnector(BaseDatasetConnector):
    """Connector for the NASA POWER daily point API."""

    DATASET_NAME = "nasa_power"

    def download(
        self,
        *,
        variables: list[str] | None = None,
        dates: list[str] | None = None,
        latitude: float = _DEFAULT_LATITUDE,
        longitude: float = _DEFAULT_LONGITUDE,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download a NASA POWER daily point time series as JSON.

        Args:
            variables: Climate variables to request; defaults to all available.
            dates: ISO dates defining the coverage window; defaults to the last
                available week. Only the first and last are used as start/end.
            latitude: Point latitude (defaults to India's centroid).
            longitude: Point longitude (defaults to India's centroid).
            **kwargs: Unused; accepted for interface compatibility.

        Returns:
            A :class:`DownloadResult` for the stored JSON file.
        """
        resolved_vars = self._resolve_variables(variables)
        resolved_dates = list(dates) if dates else list(self.available_dates())
        power_params = ",".join(_POWER_PARAMETERS[v] for v in resolved_vars)
        start = _to_power_date(min(resolved_dates))
        end = _to_power_date(max(resolved_dates))

        url = f"{self._settings.nasa_power_base_url}/temporal/daily/point"
        params = {
            "parameters": power_params,
            "community": str(self._descriptor.default_params.get("community", "AG")),
            "longitude": longitude,
            "latitude": latitude,
            "start": start,
            "end": end,
            "format": "JSON",
        }
        filename = f"nasa_power_{start}_{end}_{latitude}_{longitude}.json"
        dest = self._raw_path(filename)

        self._logger.info("Requesting NASA POWER %s for %s..%s", power_params, start, end)
        result = self._downloader.download(url, dest, params=params)
        return self._finalize_download(
            result,
            variables=resolved_vars,
            dates=resolved_dates,
            extra={"latitude": str(latitude), "longitude": str(longitude)},
        )


def _to_power_date(iso_date: str) -> str:
    """Convert ``YYYY-MM-DD`` to NASA POWER's ``YYYYMMDD`` format."""
    return date.fromisoformat(iso_date).strftime("%Y%m%d")
