"""SatelliteFrame domain model.

Per SAD Section 20 ("Additional satellite missions"), every satellite
ingestion connector (Sentinel, MODIS, INSAT, Oceansat...) produces this same
typed object, so downstream assimilation code is mission-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from core.models.metadata import DatasetMetadata
from core.models.region import BoundingBox


@dataclass(frozen=True)
class SatelliteFrame:
    """A single satellite-derived raster observation for one variable/time.

    Attributes:
        variable_name: Canonical climate variable this frame represents.
        mission: Satellite mission/sensor name (e.g. ``"sentinel-2"``).
        acquired_at: Timestamp the frame was acquired/captured.
        bounding_box: Spatial extent covered by ``data``.
        data: 2D array of shape ``(height, width)`` holding the raster values.
        resolution_deg: Approximate per-pixel resolution in degrees.
        crs: Coordinate reference system identifier (e.g. ``"EPSG:4326"``).
        metadata: Provenance metadata for this frame.
        nodata_value: Sentinel value in ``data`` representing missing pixels.
    """

    variable_name: str
    mission: str
    acquired_at: datetime
    bounding_box: BoundingBox
    data: np.ndarray
    resolution_deg: float
    crs: str
    metadata: DatasetMetadata
    nodata_value: float = field(default=float("nan"))

    def __post_init__(self) -> None:
        if self.data.ndim != 2:
            raise ValueError(f"SatelliteFrame.data must be 2D, got shape {self.data.shape}")
        if self.resolution_deg <= 0:
            raise ValueError("resolution_deg must be positive")

    @property
    def valid_pixel_fraction(self) -> float:
        """Fraction of pixels in ``data`` that are not the nodata sentinel.

        Returns:
            A value in ``[0, 1]`` indicating raster completeness.
        """
        total = self.data.size
        if total == 0:
            return 0.0
        if np.isnan(self.nodata_value):
            valid = np.count_nonzero(~np.isnan(self.data))
        else:
            valid = np.count_nonzero(self.data != self.nodata_value)
        return float(valid) / float(total)
