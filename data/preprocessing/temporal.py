"""Temporal alignment of heterogeneous climate time series.

Different sources arrive at different cadences (ERA5 hourly, NASA POWER daily,
MODIS 16-day). Before fusion they must share a common temporal grid. These
helpers resample each series to a target frequency and align them onto one
:class:`pandas.DataFrame` indexed by time, filling short gaps by interpolation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

import pandas as pd

from utils.exceptions import TemporalAlignmentError
from utils.logger import get_logger

logger = get_logger(__name__)

AggMethod = Literal["mean", "sum", "min", "max", "median"]
FillMethod = Literal["interpolate", "ffill", "bfill", "none"]


def resample_series(series: pd.Series, freq: str, agg: AggMethod = "mean") -> pd.Series:
    """Resample a single time-indexed series to ``freq``.

    Args:
        series: A series indexed by a :class:`~pandas.DatetimeIndex`.
        freq: Target pandas offset alias (e.g. ``"D"``, ``"h"``, ``"ME"``).
        agg: Aggregation applied within each resampled bin.

    Returns:
        The resampled series.

    Raises:
        TemporalAlignmentError: If the series is not datetime-indexed.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TemporalAlignmentError(
            "Series must have a DatetimeIndex to resample", details={"name": series.name}
        )
    resampler = series.resample(freq)
    return getattr(resampler, agg)()


def align_time_series(
    series_map: Mapping[str, pd.Series],
    freq: str,
    *,
    agg: AggMethod = "mean",
    fill: FillMethod = "interpolate",
) -> pd.DataFrame:
    """Align multiple named series onto one common temporal grid.

    Args:
        series_map: Mapping of column name → datetime-indexed series.
        freq: Target frequency all series are resampled to.
        agg: Aggregation used when down-sampling each series.
        fill: Gap-filling strategy applied after alignment.

    Returns:
        A :class:`pandas.DataFrame` indexed by the shared time grid, one column
        per input series.

    Raises:
        TemporalAlignmentError: If ``series_map`` is empty.
    """
    if not series_map:
        raise TemporalAlignmentError("No series provided to align")

    resampled = {
        name: resample_series(series, freq, agg=agg) for name, series in series_map.items()
    }
    frame = pd.DataFrame(resampled).sort_index()
    filled = _apply_fill(frame, fill)
    logger.debug("Aligned %d series onto %s grid (%d rows)", frame.shape[1], freq, len(filled))
    return filled


def align_to_reference(
    series: pd.Series, reference_index: pd.DatetimeIndex, *, fill: FillMethod = "interpolate"
) -> pd.Series:
    """Reindex a series onto a reference time index, filling gaps.

    Args:
        series: The series to align.
        reference_index: The target datetime index.
        fill: Gap-filling strategy for newly-introduced timestamps.

    Returns:
        The series reindexed onto ``reference_index``.
    """
    reindexed = series.reindex(series.index.union(reference_index))
    reindexed = _apply_fill(reindexed.to_frame(name=series.name or "value"), fill)
    return reindexed[series.name or "value"].reindex(reference_index)


def _apply_fill(frame: pd.DataFrame, fill: FillMethod) -> pd.DataFrame:
    """Apply the requested gap-filling strategy to a frame."""
    if fill == "none":
        return frame
    if fill == "interpolate":
        return frame.interpolate(method="time").ffill().bfill()
    if fill == "ffill":
        return frame.ffill()
    if fill == "bfill":
        return frame.bfill()
    raise TemporalAlignmentError("Unknown fill method", details={"fill": fill})
