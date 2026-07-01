"""Lightweight in-memory raster abstraction for the processing layer.

:class:`RasterLayer` is a NumPy-backed, dependency-light representation of a
single 2-D geospatial grid (one variable, one time slice). Every processing
operation — reprojection, clipping, resampling, interpolation, normalization —
consumes and returns a :class:`RasterLayer`, so the heavy GIS libraries
(Rasterio/Xarray) are only ever touched at the I/O edges (see
:mod:`data.preprocessing.readers`), never in the numeric core.

The grid convention is north-up, row 0 at the top (``north`` edge). Cell
``(row, col)`` covers ``[west + col*pw, west + (col+1)*pw]`` in longitude and
``[north - (row+1)*ph, north - row*ph]`` in latitude, with the sample located
at the cell centre. Missing samples are represented by ``numpy.nan`` in
:attr:`RasterLayer.data`; :attr:`RasterLayer.nodata` records the sentinel used
by the source file, if any.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from core.models.region import BoundingBox


@dataclass(frozen=True, slots=True)
class GeoTransform:
    """Affine mapping between pixel indices and geographic coordinates.

    Attributes:
        west: Longitude of the left edge of column 0 (decimal degrees).
        north: Latitude of the top edge of row 0 (decimal degrees).
        pixel_width: Longitude span of one column (positive degrees).
        pixel_height: Latitude span of one row (positive degrees, north→south).
    """

    west: float
    north: float
    pixel_width: float
    pixel_height: float

    def __post_init__(self) -> None:
        if self.pixel_width <= 0 or self.pixel_height <= 0:
            raise ValueError("pixel_width and pixel_height must be positive")

    def xy(self, row: int, col: int) -> tuple[float, float]:
        """Return the ``(lon, lat)`` centre of cell ``(row, col)``."""
        lon = self.west + (col + 0.5) * self.pixel_width
        lat = self.north - (row + 0.5) * self.pixel_height
        return lon, lat

    def rowcol(self, lon: float, lat: float) -> tuple[int, int]:
        """Return the ``(row, col)`` index containing coordinate ``(lon, lat)``."""
        col = int(np.floor((lon - self.west) / self.pixel_width))
        row = int(np.floor((self.north - lat) / self.pixel_height))
        return row, col


@dataclass(frozen=True, slots=True)
class RasterLayer:
    """A single NumPy-backed geospatial grid with provenance.

    Attributes:
        data: 2-D array of shape ``(rows, cols)``; missing cells are ``nan``.
        transform: Pixel↔coordinate mapping.
        crs: Coordinate reference system identifier (default ``"EPSG:4326"``).
        nodata: Source nodata sentinel, if any (already converted to ``nan``).
        name: Optional variable/layer name (e.g. ``"temperature_2m"``).
        attrs: Free-form metadata carried alongside the grid.
    """

    data: np.ndarray
    transform: GeoTransform
    crs: str = "EPSG:4326"
    nodata: float | None = None
    name: str | None = None
    attrs: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.data.ndim != 2:
            raise ValueError(f"RasterLayer.data must be 2-D, got shape {self.data.shape}")

    @property
    def rows(self) -> int:
        """Number of grid rows (latitude bands)."""
        return int(self.data.shape[0])

    @property
    def cols(self) -> int:
        """Number of grid columns (longitude bands)."""
        return int(self.data.shape[1])

    @property
    def shape(self) -> tuple[int, int]:
        """Grid shape as ``(rows, cols)``."""
        return (self.rows, self.cols)

    @property
    def bounds(self) -> BoundingBox:
        """The geographic extent of the grid as a :class:`BoundingBox`."""
        min_lon = self.transform.west
        max_lon = self.transform.west + self.cols * self.transform.pixel_width
        max_lat = self.transform.north
        min_lat = self.transform.north - self.rows * self.transform.pixel_height
        return BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    def lons(self) -> np.ndarray:
        """Return the 1-D array of column-centre longitudes."""
        return self.transform.west + (np.arange(self.cols) + 0.5) * self.transform.pixel_width

    def lats(self) -> np.ndarray:
        """Return the 1-D array of row-centre latitudes (north→south)."""
        return self.transform.north - (np.arange(self.rows) + 0.5) * self.transform.pixel_height

    def missing_mask(self) -> np.ndarray:
        """Return a boolean mask that is ``True`` where samples are missing."""
        return np.isnan(self.data)

    def with_data(self, data: np.ndarray, **overrides: object) -> RasterLayer:
        """Return a copy of this layer with ``data`` (and optional field overrides).

        Args:
            data: The replacement 2-D array.
            **overrides: Any :class:`RasterLayer` field to override (e.g.
                ``transform``, ``crs``, ``name``).

        Returns:
            A new, independent :class:`RasterLayer`.
        """
        return replace(self, data=np.asarray(data, dtype=float), **overrides)  # type: ignore[arg-type]

    def mean(self) -> float:
        """Return the nan-aware mean of all samples (``nan`` if fully missing)."""
        if np.all(self.missing_mask()):
            return float("nan")
        return float(np.nanmean(self.data))
