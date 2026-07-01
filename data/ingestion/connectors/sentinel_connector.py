"""Sentinel connector (Copernicus Sentinel Hub).

Sentinel Hub uses OAuth2 client-credentials. The client id/secret are read from
:class:`config.settings.Settings` (never hardcoded); when absent,
:class:`MissingCredentialsError` is raised.
"""

from __future__ import annotations

from typing import Any

from data.ingestion.base import BaseDatasetConnector
from data.ingestion.download_manager import DownloadResult
from utils.exceptions import MissingCredentialsError


class SentinelConnector(BaseDatasetConnector):
    """Connector for Sentinel-2 L2A imagery via the Sentinel Hub process API."""

    DATASET_NAME = "sentinel"

    def download(
        self,
        *,
        variables: list[str] | None = None,
        dates: list[str] | None = None,
        bbox: tuple[float, float, float, float] = (68.0, 6.0, 98.0, 38.0),
        **kwargs: Any,
    ) -> DownloadResult:
        """Request a Sentinel Hub processed image for a bounding box and window.

        Args:
            variables: Variables to derive; defaults to all available.
            dates: ISO dates defining the temporal window; defaults to recent.
            bbox: ``(min_lon, min_lat, max_lon, max_lat)`` (defaults to India).
            **kwargs: Unused; accepted for interface compatibility.

        Returns:
            A :class:`DownloadResult` for the stored image file.

        Raises:
            MissingCredentialsError: If Sentinel Hub OAuth credentials are absent.
        """
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        resolved_vars = self._resolve_variables(variables)
        resolved_dates = list(dates) if dates else list(self.available_dates())

        url = f"{self._settings.sentinel_hub_base_url}/api/v1/process"
        body = {
            "input": {
                "bounds": {"bbox": list(bbox)},
                "data": [
                    {
                        "type": str(
                            self._descriptor.default_params.get("collection", "sentinel-2-l2a")
                        ),
                        "dataFilter": {
                            "timeRange": {
                                "from": f"{min(resolved_dates)}T00:00:00Z",
                                "to": f"{max(resolved_dates)}T23:59:59Z",
                            }
                        },
                    }
                ],
            },
            "output": {"responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
        }
        filename = f"sentinel_{min(resolved_dates)}_{max(resolved_dates)}.tiff"
        dest = self._raw_path(filename)

        self._logger.info("Requesting Sentinel Hub image for bbox %s", bbox)
        result = self._downloader.download(
            url, dest, method="POST", json_body=body, headers=headers
        )
        return self._finalize_download(
            result,
            variables=resolved_vars,
            dates=resolved_dates,
            extra={"bbox": ",".join(str(c) for c in bbox)},
        )

    def _access_token(self) -> str:
        """Obtain an OAuth2 bearer token via client-credentials.

        Returns:
            The access token string reported by the Sentinel Hub OAuth endpoint.

        Raises:
            MissingCredentialsError: If client id/secret are not configured.
        """
        client_id = self._settings.sentinel_client_id
        client_secret = self._settings.sentinel_client_secret
        if not client_id or not client_secret:
            raise MissingCredentialsError(
                "Sentinel Hub credentials not configured; set "
                "CDT_SENTINEL_CLIENT_ID and CDT_SENTINEL_CLIENT_SECRET",
                details={"dataset": self.name},
            )
        response = self._downloader.session.post(
            f"{self._settings.sentinel_hub_base_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=self._settings.request_timeout_seconds,
        )
        response.raise_for_status()
        return str(response.json()["access_token"])
