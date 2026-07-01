"""ERA5 reanalysis connector (Copernicus Climate Data Store).

ERA5 is served through the Copernicus CDS API, which requires a personal API
key. The key is read from :class:`config.settings.Settings.cds_api_key` (never
hardcoded); when absent, :class:`MissingCredentialsError` is raised so the
misconfiguration is explicit.
"""

from __future__ import annotations

from typing import Any

from data.ingestion.base import BaseDatasetConnector
from data.ingestion.download_manager import DownloadResult
from utils.exceptions import MissingCredentialsError

# Map canonical identifiers to CDS ERA5 single-levels variable names.
_ERA5_VARIABLES: dict[str, str] = {
    "temperature_2m": "2m_temperature",
    "precipitation": "total_precipitation",
    "surface_pressure": "surface_pressure",
    "wind_speed_10m": "10m_wind_speed",
    "relative_humidity": "relative_humidity",
}


class ERA5Connector(BaseDatasetConnector):
    """Connector for ERA5 hourly reanalysis on single levels."""

    DATASET_NAME = "era5"

    def download(
        self,
        *,
        variables: list[str] | None = None,
        dates: list[str] | None = None,
        **kwargs: Any,
    ) -> DownloadResult:
        """Submit an ERA5 retrieval request and download the resulting file.

        Args:
            variables: Climate variables to request; defaults to all available.
            dates: ISO dates to retrieve; defaults to the last available week.
            **kwargs: Unused; accepted for interface compatibility.

        Returns:
            A :class:`DownloadResult` for the stored NetCDF file.

        Raises:
            MissingCredentialsError: If no CDS API key is configured.
        """
        auth = self._resolve_auth()
        resolved_vars = self._resolve_variables(variables)
        resolved_dates = list(dates) if dates else list(self.available_dates())
        cds_variables = [_ERA5_VARIABLES[v] for v in resolved_vars]

        url = f"{self._settings.era5_cds_url}/resources/reanalysis-era5-single-levels"
        body = {
            "product_type": str(self._descriptor.default_params.get("product_type", "reanalysis")),
            "format": str(self._descriptor.default_params.get("format", "netcdf")),
            "variable": cds_variables,
            "date": f"{min(resolved_dates)}/{max(resolved_dates)}",
            "time": [f"{h:02d}:00" for h in range(24)],
        }
        filename = f"era5_{min(resolved_dates)}_{max(resolved_dates)}.nc"
        dest = self._raw_path(filename)

        self._logger.info("Submitting ERA5 request for %d variable(s)", len(cds_variables))
        result = self._downloader.download(url, dest, method="POST", json_body=body, auth=auth)
        return self._finalize_download(
            result, variables=resolved_vars, dates=resolved_dates, version="reanalysis-era5"
        )

    def _resolve_auth(self) -> tuple[str, str]:
        """Return ``(uid, key)`` CDS basic-auth credentials from settings.

        Raises:
            MissingCredentialsError: If ``cds_api_key`` is not configured.
        """
        key = self._settings.cds_api_key
        if not key:
            raise MissingCredentialsError(
                "CDS API key not configured; set CDT_CDS_API_KEY",
                details={"dataset": self.name},
            )
        uid, _, secret = key.partition(":")
        return (uid, secret) if secret else (uid, uid)
