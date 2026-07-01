"""Missing-value handling for :class:`RasterLayer` grids.

Distinct from :mod:`data.preprocessing.interpolation`, these helpers apply
*non-spatial* strategies — constant fill, statistical fill, sentinel masking —
plus quality metrics used to decide whether a layer is fit for assimilation.
"""

from __future__ import annotations

import numpy as np

from data.preprocessing.raster import RasterLayer
from utils.logger import get_logger

logger = get_logger(__name__)


def mask_sentinel(layer: RasterLayer, sentinel: float, *, rtol: float = 0.0) -> RasterLayer:
    """Convert a nodata sentinel value into ``nan``.

    Args:
        layer: The source raster.
        sentinel: The value to treat as missing (e.g. ``-9999``).
        rtol: Relative tolerance for the comparison (0 → exact match).

    Returns:
        A new raster with sentinel cells set to ``nan``.
    """
    mask = np.isclose(layer.data, sentinel, rtol=rtol) if rtol > 0 else layer.data == sentinel
    return layer.with_data(np.where(mask, np.nan, layer.data), nodata=sentinel)


def fill_constant(layer: RasterLayer, value: float) -> RasterLayer:
    """Replace every missing cell with a constant ``value``."""
    return layer.with_data(np.where(np.isnan(layer.data), value, layer.data))


def fill_with_mean(layer: RasterLayer) -> RasterLayer:
    """Replace missing cells with the layer's nan-aware mean.

    Returns:
        A new raster with gaps filled by the mean of valid cells. If the layer
        is entirely missing, it is returned unchanged.
    """
    if np.all(np.isnan(layer.data)):
        return layer.with_data(np.array(layer.data, copy=True))
    return fill_constant(layer, float(np.nanmean(layer.data)))


def missing_fraction(layer: RasterLayer) -> float:
    """Return the fraction of cells that are missing, in ``[0, 1]``."""
    total = layer.data.size
    return float(np.isnan(layer.data).sum() / total) if total else 0.0


def count_missing(layer: RasterLayer) -> int:
    """Return the number of missing cells in the layer."""
    return int(np.isnan(layer.data).sum())
