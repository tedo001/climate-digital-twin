"""MODIS connector (Terra/Aqua) via NASA Earthdata / LP DAAC."""

from __future__ import annotations

from data.ingestion.connectors._earthdata_base import EarthdataConnector


class MODISConnector(EarthdataConnector):
    """Connector for MODIS vegetation/temperature products (e.g. MOD13Q1)."""

    DATASET_NAME = "modis"
    FILE_EXTENSION = ".hdf"

    def _granule_url(self, product: str, iso_date: str) -> str:
        """Build the LP DAAC granule URL for a MODIS product and date."""
        return f"{self._settings.modis_base_url}/data/{product}/{iso_date}/granule{self.FILE_EXTENSION}"
