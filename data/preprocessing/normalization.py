"""Normalization and physical unit conversions for processed grids.

Two concerns live here:

* **Statistical normalization** (min-max, z-score) used to condition inputs for
  the AI layer, returning both the transformed grid and the :class:`NormalizationStats`
  needed to invert or reapply the transform consistently.
* **Unit harmonization** (Kelvin→Celsius, metres→millimetres, Pascals→hPa) so
  that heterogeneous source datasets share the canonical units declared in
  :data:`config.constants.DEFAULT_VARIABLE_UNITS`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from data.preprocessing.raster import RasterLayer
from utils.exceptions import NormalizationError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class NormalizationStats:
    """Parameters describing an applied normalization, for inversion/reuse.

    Attributes:
        method: ``"min_max"`` or ``"z_score"``.
        offset: Value subtracted before scaling (min or mean).
        scale: Value divided by after offsetting (range or std).
    """

    method: str
    offset: float
    scale: float

    def denormalize(self, array: np.ndarray) -> np.ndarray:
        """Invert the normalization on ``array``."""
        return array * self.scale + self.offset


def min_max_normalize(layer: RasterLayer) -> tuple[RasterLayer, NormalizationStats]:
    """Scale a raster's valid cells into ``[0, 1]``.

    Args:
        layer: The source raster.

    Returns:
        A ``(normalized_layer, stats)`` tuple.

    Raises:
        NormalizationError: If the layer has no valid cells or is constant.
    """
    valid = layer.data[~np.isnan(layer.data)]
    if valid.size == 0:
        raise NormalizationError(
            "Cannot normalize a fully-missing raster", details={"name": layer.name}
        )
    minimum = float(valid.min())
    maximum = float(valid.max())
    span = maximum - minimum
    if span == 0:
        raise NormalizationError(
            "Cannot min-max normalize a constant raster", details={"value": minimum}
        )
    normalized = (layer.data - minimum) / span
    return layer.with_data(normalized), NormalizationStats("min_max", minimum, span)


def z_score_normalize(layer: RasterLayer) -> tuple[RasterLayer, NormalizationStats]:
    """Standardize a raster's valid cells to zero mean and unit variance.

    Args:
        layer: The source raster.

    Returns:
        A ``(normalized_layer, stats)`` tuple.

    Raises:
        NormalizationError: If the layer has no valid cells or zero variance.
    """
    valid = layer.data[~np.isnan(layer.data)]
    if valid.size == 0:
        raise NormalizationError(
            "Cannot normalize a fully-missing raster", details={"name": layer.name}
        )
    mean = float(valid.mean())
    std = float(valid.std())
    if std == 0:
        raise NormalizationError("Cannot z-score normalize zero-variance raster")
    normalized = (layer.data - mean) / std
    return layer.with_data(normalized), NormalizationStats("z_score", mean, std)


def kelvin_to_celsius(layer: RasterLayer) -> RasterLayer:
    """Convert a temperature grid from Kelvin to degrees Celsius."""
    return layer.with_data(layer.data - 273.15)


def metres_to_millimetres(layer: RasterLayer) -> RasterLayer:
    """Convert an accumulation grid (e.g. precipitation) from metres to mm."""
    return layer.with_data(layer.data * 1000.0)


def pascals_to_hectopascals(layer: RasterLayer) -> RasterLayer:
    """Convert a pressure grid from Pascals to hectopascals (hPa)."""
    return layer.with_data(layer.data / 100.0)


def fraction_to_percent(layer: RasterLayer) -> RasterLayer:
    """Convert a ``[0, 1]`` fractional grid to a ``[0, 100]`` percentage."""
    return layer.with_data(layer.data * 100.0)
