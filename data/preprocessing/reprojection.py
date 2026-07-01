"""Reproject a :class:`RasterLayer` between coordinate reference systems.

Same-CRS requests short-circuit to a no-op copy (so the common EPSG:4326 case
needs no GDAL). Genuine reprojection is delegated to Rasterio's warp engine via
a lazy import, keeping the numeric core free of a hard GDAL dependency.
"""

from __future__ import annotations

import numpy as np

from data.preprocessing.raster import GeoTransform, RasterLayer
from utils.exceptions import RasterProcessingError
from utils.logger import get_logger

logger = get_logger(__name__)


def reproject(layer: RasterLayer, dst_crs: str) -> RasterLayer:
    """Reproject a raster to ``dst_crs``.

    Args:
        layer: The source raster.
        dst_crs: Target CRS identifier (e.g. ``"EPSG:3857"``).

    Returns:
        A new :class:`RasterLayer` in the destination CRS. If the source is
        already in ``dst_crs``, an independent copy is returned unchanged.

    Raises:
        RasterProcessingError: If Rasterio is unavailable or warping fails.
    """
    if _normalize_crs(layer.crs) == _normalize_crs(dst_crs):
        return layer.with_data(np.array(layer.data, copy=True))

    try:
        import rasterio
        from rasterio.transform import from_origin
        from rasterio.warp import Resampling, calculate_default_transform
        from rasterio.warp import reproject as rio_reproject
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RasterProcessingError(
            "Rasterio is required for CRS reprojection",
            details={"src_crs": layer.crs, "dst_crs": dst_crs},
        ) from exc

    src_transform = from_origin(
        layer.transform.west,
        layer.transform.north,
        layer.transform.pixel_width,
        layer.transform.pixel_height,
    )
    left = layer.transform.west
    top = layer.transform.north
    right = left + layer.cols * layer.transform.pixel_width
    bottom = top - layer.rows * layer.transform.pixel_height

    try:
        dst_transform, width, height = calculate_default_transform(
            layer.crs, dst_crs, layer.cols, layer.rows, left, bottom, right, top
        )
        destination = np.full((height, width), np.nan, dtype=float)
        rio_reproject(
            source=np.where(np.isnan(layer.data), -9999.0, layer.data),
            destination=destination,
            src_transform=src_transform,
            src_crs=layer.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            src_nodata=-9999.0,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    except (ValueError, rasterio.errors.RasterioError) as exc:
        raise RasterProcessingError(
            "Reprojection failed", details={"dst_crs": dst_crs, "error": str(exc)}
        ) from exc

    new_transform = GeoTransform(
        west=dst_transform.c,
        north=dst_transform.f,
        pixel_width=abs(dst_transform.a),
        pixel_height=abs(dst_transform.e),
    )
    logger.debug("Reprojected raster %s from %s to %s", layer.name, layer.crs, dst_crs)
    return layer.with_data(destination, transform=new_transform, crs=dst_crs)


def _normalize_crs(crs: str) -> str:
    """Normalize a CRS string for equality comparison (case/space-insensitive)."""
    return crs.replace(" ", "").upper()
