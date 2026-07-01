"""GPM IMERG precipitation connector via NASA Earthdata / GES DISC."""

from __future__ import annotations

from data.ingestion.connectors._earthdata_base import EarthdataConnector


class GPMConnector(EarthdataConnector):
    """Connector for GPM IMERG half-hourly precipitation products."""

    DATASET_NAME = "gpm"
    FILE_EXTENSION = ".HDF5"

    def _granule_url(self, product: str, iso_date: str) -> str:
        """Build the GES DISC granule URL for a GPM IMERG product and date."""
        return (
            f"{self._settings.gpm_base_url}/data/{product}/{iso_date}/granule{self.FILE_EXTENSION}"
        )
