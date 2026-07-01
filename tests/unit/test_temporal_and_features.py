"""Unit tests for temporal alignment and feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.models.region import BoundingBox
from data.preprocessing.feature_engineering import (
    add_lag_features,
    aggregate_to_bbox,
    build_feature_frame,
    rolling_mean,
    spatial_gradient_magnitude,
    temporal_anomaly,
)
from data.preprocessing.raster import GeoTransform, RasterLayer
from data.preprocessing.temporal import (
    align_time_series,
    align_to_reference,
    resample_series,
)
from utils.exceptions import FeatureEngineeringError, TemporalAlignmentError


def _hourly(n: int = 48, name: str = "s") -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.Series(np.arange(n, dtype=float), index=idx, name=name)


# --------------------------- temporal --------------------------- #
def test_resample_series_daily_mean() -> None:
    out = resample_series(_hourly(48), "D", agg="mean")
    assert len(out) == 2
    assert out.iloc[0] == pytest.approx(np.arange(24).mean())


def test_resample_requires_datetime_index() -> None:
    with pytest.raises(TemporalAlignmentError):
        resample_series(pd.Series([1.0, 2.0]), "D")


def test_align_time_series_common_grid() -> None:
    s1 = _hourly(48, "era5")
    s2 = pd.Series([1.0, 2.0], index=pd.date_range("2024-01-01", periods=2, freq="D"), name="power")
    frame = align_time_series({"era5": s1, "power": s2}, "D")
    assert list(frame.columns) == ["era5", "power"]
    assert len(frame) == 2
    assert not frame.isna().any().any()


def test_align_time_series_empty_raises() -> None:
    with pytest.raises(TemporalAlignmentError):
        align_time_series({}, "D")


def test_align_to_reference_fills_gaps() -> None:
    s = pd.Series([1.0, 3.0], index=pd.to_datetime(["2024-01-01", "2024-01-03"]), name="x")
    ref = pd.date_range("2024-01-01", periods=3, freq="D")
    out = align_to_reference(s, ref)
    assert out.loc["2024-01-02"] == pytest.approx(2.0)  # linear interpolation


# --------------------------- features --------------------------- #
def test_rolling_mean_window() -> None:
    out = rolling_mean(pd.Series([1.0, 2.0, 3.0, 4.0]), 2)
    assert out.iloc[-1] == pytest.approx(3.5)


def test_rolling_mean_rejects_bad_window() -> None:
    with pytest.raises(FeatureEngineeringError):
        rolling_mean(pd.Series([1.0]), 0)


def test_add_lag_features() -> None:
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    out = add_lag_features(frame, "a", [1, 2])
    assert "a_lag1" in out.columns and "a_lag2" in out.columns
    assert out["a_lag1"].iloc[1] == 1.0


def test_add_lag_unknown_column_raises() -> None:
    with pytest.raises(FeatureEngineeringError):
        add_lag_features(pd.DataFrame({"a": [1.0]}), "b", [1])


def test_temporal_anomaly_default_baseline() -> None:
    s = pd.Series([1.0, 2.0, 3.0])
    out = temporal_anomaly(s)
    assert out.iloc[0] == pytest.approx(-1.0)  # 1 - mean(2)


def test_build_feature_frame_adds_columns_and_drops_na() -> None:
    idx = pd.date_range("2024-01-01", periods=6, freq="D")
    frame = pd.DataFrame({"t": np.arange(6, dtype=float)}, index=idx)
    feats = build_feature_frame(frame, rolling_window=2, lags=[1])
    assert {"t", "t_roll2", "t_anomaly", "t_lag1"}.issubset(feats.columns)
    assert not feats.isna().any().any()


def test_build_feature_frame_empty_raises() -> None:
    with pytest.raises(FeatureEngineeringError):
        build_feature_frame(pd.DataFrame())


def test_aggregate_to_bbox_area_mean() -> None:
    gt = GeoTransform(west=0.0, north=10.0, pixel_width=1.0, pixel_height=1.0)
    layer = RasterLayer(data=np.ones((10, 10)) * 5.0, transform=gt)
    val = aggregate_to_bbox(layer, BoundingBox(min_lat=2.0, min_lon=2.0, max_lat=6.0, max_lon=6.0))
    assert val == pytest.approx(5.0)


def test_spatial_gradient_magnitude_shape() -> None:
    gt = GeoTransform(west=0.0, north=10.0, pixel_width=1.0, pixel_height=1.0)
    layer = RasterLayer(data=np.arange(100, dtype=float).reshape(10, 10), transform=gt, name="t")
    out = spatial_gradient_magnitude(layer)
    assert out.shape == (10, 10)
    assert out.name == "t_gradient"
