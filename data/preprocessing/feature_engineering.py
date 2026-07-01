"""Feature engineering over processed rasters and aligned time series.

Bridges cleaned inputs to model-ready features (SAD Section 8, Feature
Generator). Spatial helpers reduce grids to per-region scalars; temporal
helpers derive lags, rolling statistics, and anomalies from aligned series.
All functions are pure and independently unit-testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.models.region import BoundingBox
from data.preprocessing.clipping import clip_to_bbox
from data.preprocessing.raster import RasterLayer
from utils.exceptions import FeatureEngineeringError
from utils.logger import get_logger

logger = get_logger(__name__)


def aggregate_to_bbox(layer: RasterLayer, bbox: BoundingBox) -> float:
    """Return the nan-aware mean of a raster within a bounding box.

    Args:
        layer: The source raster.
        bbox: The region extent to summarize.

    Returns:
        The area-mean value over ``bbox`` (``nan`` if no valid cells fall in it).
    """
    return clip_to_bbox(layer, bbox).mean()


def spatial_gradient_magnitude(layer: RasterLayer) -> RasterLayer:
    """Compute the per-cell spatial gradient magnitude of a raster.

    Args:
        layer: The source raster.

    Returns:
        A raster whose cells hold ``sqrt(d/drow^2 + d/dcol^2)`` — useful as a
        front/edge feature (e.g. temperature gradients).
    """
    d_rows, d_cols = np.gradient(np.nan_to_num(layer.data, nan=float(layer.mean())))
    magnitude = np.hypot(d_rows, d_cols)
    return layer.with_data(magnitude, name=f"{layer.name}_gradient" if layer.name else None)


def rolling_mean(series: pd.Series, window: int, *, min_periods: int = 1) -> pd.Series:
    """Return the trailing rolling mean of a series.

    Args:
        series: The input series.
        window: Rolling window length (number of samples).
        min_periods: Minimum observations required to emit a value.

    Returns:
        The rolling-mean series.

    Raises:
        FeatureEngineeringError: If ``window`` is not positive.
    """
    if window <= 0:
        raise FeatureEngineeringError("Rolling window must be positive", details={"window": window})
    return series.rolling(window=window, min_periods=min_periods).mean()


def add_lag_features(frame: pd.DataFrame, column: str, lags: list[int]) -> pd.DataFrame:
    """Append lagged copies of a column to a frame.

    Args:
        frame: The source frame.
        column: Column to lag.
        lags: Positive lag offsets (in rows) to add as ``<column>_lag<k>``.

    Returns:
        A new frame with the added lag columns.

    Raises:
        FeatureEngineeringError: If ``column`` is absent or a lag is non-positive.
    """
    if column not in frame.columns:
        raise FeatureEngineeringError("Unknown column for lag features", details={"column": column})
    result = frame.copy()
    for lag in lags:
        if lag <= 0:
            raise FeatureEngineeringError("Lag must be positive", details={"lag": lag})
        result[f"{column}_lag{lag}"] = frame[column].shift(lag)
    return result


def temporal_anomaly(series: pd.Series, climatology: float | None = None) -> pd.Series:
    """Return the anomaly of a series relative to a climatological baseline.

    Args:
        series: The input series.
        climatology: Baseline to subtract; defaults to the series mean.

    Returns:
        The anomaly series (``series - climatology``).
    """
    baseline = series.mean() if climatology is None else climatology
    return series - baseline


def build_feature_frame(
    aligned: pd.DataFrame,
    *,
    rolling_window: int = 3,
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """Assemble a model-ready feature frame from aligned variable series.

    For every column it adds a rolling mean, an anomaly, and the requested lag
    features, then drops rows left incomplete by the widest lag.

    Args:
        aligned: A time-indexed frame of aligned variables.
        rolling_window: Window for the rolling-mean feature per column.
        lags: Lag offsets to add per column (defaults to ``[1]``).

    Returns:
        The engineered feature frame.

    Raises:
        FeatureEngineeringError: If ``aligned`` is empty.
    """
    if aligned.empty:
        raise FeatureEngineeringError("Cannot engineer features from an empty frame")
    lags = lags or [1]
    result = aligned.copy()
    for column in aligned.columns:
        result[f"{column}_roll{rolling_window}"] = rolling_mean(aligned[column], rolling_window)
        result[f"{column}_anomaly"] = temporal_anomaly(aligned[column])
        result = add_lag_features(result, column, lags)
    return result.dropna()
