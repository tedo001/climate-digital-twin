"""SMAP soil-moisture connector via NASA Earthdata / NSIDC DAAC."""

from __future__ import annotations

from data.ingestion.connectors._earthdata_base import EarthdataConnector


class SMAPConnector(EarthdataConnector):
    """Connector for SMAP enhanced L3 soil-moisture products (e.g. SPL3SMP_E)."""

    DATASET_NAME = "smap"
    FILE_EXTENSION = ".h5"

    def _granule_url(self, product: str, iso_date: str) -> str:
        """Build the NSIDC DAAC granule URL for a SMAP product and date."""
        return (
            f"{self._settings.smap_base_url}/data/{product}/{iso_date}/granule{self.FILE_EXTENSION}"
        )
