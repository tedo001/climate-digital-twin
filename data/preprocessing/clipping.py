"""Clip a :class:`RasterLayer` to a geographic bounding box.

Pure-NumPy index arithmetic — no GIS dependency — so clipping is fast and
trivially testable. The output grid keeps the source resolution and CRS.
"""

from __future__ import annotations

import numpy as np

from core.models.region import BoundingBox
from data.preprocessing.raster import GeoTransform, RasterLayer
from utils.exceptions import RasterProcessingError
from utils.logger import get_logger

logger = get_logger(__name__)


def clip_to_bbox(layer: RasterLayer, bbox: BoundingBox) -> RasterLayer:
    """Crop a raster to the cells intersecting ``bbox``.

    Args:
        layer: The source raster.
        bbox: Target extent (inclusive of any cell it touches).

    Returns:
        A new :class:`RasterLayer` covering only the requested extent.

    Raises:
        RasterProcessingError: If ``bbox`` does not overlap the raster.
    """
    transform = layer.transform
    # Column range from longitudes (west→east).
    col_start = int(np.floor((bbox.min_lon - transform.west) / transform.pixel_width))
    col_stop = int(np.ceil((bbox.max_lon - transform.west) / transform.pixel_width))
    # Row range from latitudes (north→south, so max_lat maps to the top row).
    row_start = int(np.floor((transform.north - bbox.max_lat) / transform.pixel_height))
    row_stop = int(np.ceil((transform.north - bbox.min_lat) / transform.pixel_height))

    col_start = max(col_start, 0)
    row_start = max(row_start, 0)
    col_stop = min(col_stop, layer.cols)
    row_stop = min(row_stop, layer.rows)

    if row_start >= row_stop or col_start >= col_stop:
        raise RasterProcessingError(
            "Clip bounding box does not overlap raster extent",
            details={"bbox": str(bbox), "raster_bounds": str(layer.bounds)},
        )

    clipped = layer.data[row_start:row_stop, col_start:col_stop]
    new_west = transform.west + col_start * transform.pixel_width
    new_north = transform.north - row_start * transform.pixel_height
    new_transform = GeoTransform(
        west=new_west,
        north=new_north,
        pixel_width=transform.pixel_width,
        pixel_height=transform.pixel_height,
    )
    logger.debug("Clipped raster %s from %s to %s", layer.name, layer.shape, clipped.shape)
    return layer.with_data(np.array(clipped, copy=True), transform=new_transform)
