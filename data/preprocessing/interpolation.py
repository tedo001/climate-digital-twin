"""Spatial interpolation: gap-filling grids and gridding scattered points.

Two complementary needs are covered:

* :func:`interpolate_missing` fills ``nan`` holes *inside* an otherwise-complete
  raster (e.g. cloud-masked satellite cells) using SciPy's ``griddata``.
* :func:`interpolate_points_to_grid` turns scattered station observations into a
  regular grid via inverse-distance weighting (IDW), the fusion entry point
  described in SAD Section 10.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.interpolate import griddata

from data.preprocessing.raster import GeoTransform, RasterLayer
from utils.exceptions import RasterProcessingError
from utils.logger import get_logger

logger = get_logger(__name__)

GridMethod = Literal["nearest", "linear", "cubic"]


def interpolate_missing(layer: RasterLayer, method: GridMethod = "linear") -> RasterLayer:
    """Fill missing (``nan``) cells by interpolating from valid neighbours.

    Args:
        layer: The raster with gaps to fill.
        method: ``griddata`` interpolation method.

    Returns:
        A new raster with interior gaps filled. Cells outside the convex hull of
        valid samples (which ``linear``/``cubic`` cannot reach) are backfilled
        with nearest-neighbour values so the output has no residual ``nan``
        where any valid data exists.

    Raises:
        RasterProcessingError: If the raster has no valid samples to interpolate.
    """
    mask = np.isnan(layer.data)
    if not mask.any():
        return layer.with_data(np.array(layer.data, copy=True))
    if mask.all():
        raise RasterProcessingError(
            "Cannot interpolate a fully-missing raster", details={"name": layer.name}
        )

    rows, cols = np.indices(layer.data.shape)
    valid = ~mask
    points = np.column_stack((rows[valid], cols[valid]))
    values = layer.data[valid]
    targets = np.column_stack((rows[mask], cols[mask]))

    filled = layer.data.copy()
    interp = griddata(points, values, targets, method=method)
    if np.isnan(interp).any():
        nearest = griddata(points, values, targets, method="nearest")
        interp = np.where(np.isnan(interp), nearest, interp)
    filled[mask] = interp
    logger.debug("Interpolated %d missing cells in %s", int(mask.sum()), layer.name)
    return layer.with_data(filled)


def interpolate_points_to_grid(
    lons: np.ndarray,
    lats: np.ndarray,
    values: np.ndarray,
    transform: GeoTransform,
    shape: tuple[int, int],
    *,
    power: float = 2.0,
    crs: str = "EPSG:4326",
    name: str | None = None,
) -> RasterLayer:
    """Grid scattered point samples onto a regular raster using IDW.

    Args:
        lons: 1-D array of sample longitudes.
        lats: 1-D array of sample latitudes.
        values: 1-D array of sample values (same length as ``lons``/``lats``).
        transform: Target grid geotransform.
        shape: Target grid shape ``(rows, cols)``.
        power: IDW distance exponent (higher → more local).
        crs: CRS of the output grid.
        name: Optional layer name.

    Returns:
        A :class:`RasterLayer` of IDW-interpolated values.

    Raises:
        RasterProcessingError: If inputs are empty or mismatched in length.
    """
    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)
    values = np.asarray(values, dtype=float)
    if not (lons.size == lats.size == values.size) or lons.size == 0:
        raise RasterProcessingError(
            "Point arrays must be non-empty and equal length",
            details={"lons": lons.size, "lats": lats.size, "values": values.size},
        )

    rows, cols = shape
    grid = np.empty((rows, cols), dtype=float)
    col_lons = transform.west + (np.arange(cols) + 0.5) * transform.pixel_width
    row_lats = transform.north - (np.arange(rows) + 0.5) * transform.pixel_height

    for r in range(rows):
        for c in range(cols):
            d2 = (lons - col_lons[c]) ** 2 + (lats - row_lats[r]) ** 2
            exact = np.isclose(d2, 0.0)
            if exact.any():
                grid[r, c] = float(values[exact][0])
                continue
            weights = 1.0 / np.power(d2, power / 2.0)
            grid[r, c] = float(np.sum(weights * values) / np.sum(weights))

    return RasterLayer(data=grid, transform=transform, crs=crs, name=name)
