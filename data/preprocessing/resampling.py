"""Resample a :class:`RasterLayer` to a target spatial resolution.

Changes the grid step (degrees/pixel) while preserving the geographic extent.
Continuous fields use order-1 (bilinear) interpolation; categorical/label
fields should pass ``method="nearest"``. NaN gaps are handled by resampling a
validity mask alongside the data so interpolation never smears missing regions.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.ndimage import zoom

from data.preprocessing.raster import GeoTransform, RasterLayer
from utils.exceptions import RasterProcessingError
from utils.logger import get_logger

logger = get_logger(__name__)

ResampleMethod = Literal["nearest", "bilinear"]
_ORDER = {"nearest": 0, "bilinear": 1}


def resample(
    layer: RasterLayer,
    target_resolution_deg: float,
    method: ResampleMethod = "bilinear",
) -> RasterLayer:
    """Resample a raster to a new (isotropic) resolution.

    Args:
        layer: The source raster.
        target_resolution_deg: Desired degrees-per-pixel for both axes.
        method: ``"bilinear"`` (default, continuous) or ``"nearest"``.

    Returns:
        A new :class:`RasterLayer` at the requested resolution.

    Raises:
        RasterProcessingError: If the resolution is non-positive or the method
            is unknown.
    """
    if target_resolution_deg <= 0:
        raise RasterProcessingError(
            "target_resolution_deg must be positive",
            details={"value": target_resolution_deg},
        )
    if method not in _ORDER:
        raise RasterProcessingError("Unknown resample method", details={"method": method})

    row_factor = layer.transform.pixel_height / target_resolution_deg
    col_factor = layer.transform.pixel_width / target_resolution_deg
    new_rows = max(1, round(layer.rows * row_factor))
    new_cols = max(1, round(layer.cols * col_factor))
    zoom_rows = new_rows / layer.rows
    zoom_cols = new_cols / layer.cols

    resampled = _zoom_with_nan(layer.data, (zoom_rows, zoom_cols), _ORDER[method])

    new_transform = GeoTransform(
        west=layer.transform.west,
        north=layer.transform.north,
        pixel_width=layer.transform.pixel_width / zoom_cols,
        pixel_height=layer.transform.pixel_height / zoom_rows,
    )
    logger.debug(
        "Resampled raster %s from %s to %s (%s)",
        layer.name,
        layer.shape,
        resampled.shape,
        method,
    )
    return layer.with_data(resampled, transform=new_transform)


def resample_to_match(
    layer: RasterLayer, reference: RasterLayer, method: ResampleMethod = "bilinear"
) -> RasterLayer:
    """Resample ``layer`` so its grid step matches ``reference``.

    Args:
        layer: The raster to resample.
        reference: The raster whose resolution should be matched.
        method: Interpolation method.

    Returns:
        A resampled copy of ``layer`` sharing ``reference``'s resolution.
    """
    return resample(layer, reference.transform.pixel_width, method=method)


def _zoom_with_nan(data: np.ndarray, factors: tuple[float, float], order: int) -> np.ndarray:
    """Zoom an array while keeping NaN regions from bleeding into valid cells."""
    mask = np.isnan(data)
    if not mask.any():
        return zoom(data, factors, order=order, mode="nearest")

    filled = np.where(mask, 0.0, data)
    weight = (~mask).astype(float)
    zoomed_values = zoom(filled, factors, order=order, mode="nearest")
    zoomed_weight = zoom(weight, factors, order=order, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        result = zoomed_values / zoomed_weight
    result[zoomed_weight < 1e-6] = np.nan
    return result
