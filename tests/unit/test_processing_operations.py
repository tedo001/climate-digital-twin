"""Unit tests for the raster processing operations.

Covers clipping, resampling, reprojection, interpolation, missing-value
handling, and normalization.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.models.region import BoundingBox
from data.preprocessing.clipping import clip_to_bbox
from data.preprocessing.interpolation import interpolate_missing, interpolate_points_to_grid
from data.preprocessing.missing import (
    count_missing,
    fill_constant,
    fill_with_mean,
    mask_sentinel,
    missing_fraction,
)
from data.preprocessing.normalization import (
    kelvin_to_celsius,
    metres_to_millimetres,
    min_max_normalize,
    pascals_to_hectopascals,
    z_score_normalize,
)
from data.preprocessing.raster import GeoTransform, RasterLayer
from data.preprocessing.reprojection import reproject
from data.preprocessing.resampling import resample, resample_to_match
from utils.exceptions import NormalizationError, RasterProcessingError


def _layer(data: np.ndarray | None = None) -> RasterLayer:
    gt = GeoTransform(west=0.0, north=10.0, pixel_width=1.0, pixel_height=1.0)
    if data is None:
        data = np.arange(100, dtype=float).reshape(10, 10)
    return RasterLayer(data=data, transform=gt, name="v")


# --------------------------- clipping --------------------------- #
def test_clip_reduces_extent_and_updates_transform() -> None:
    clipped = clip_to_bbox(
        _layer(), BoundingBox(min_lat=2.0, min_lon=2.0, max_lat=6.0, max_lon=6.0)
    )
    assert clipped.shape == (4, 4)
    assert clipped.transform.west == 2.0
    # Row 4 (lat band [5, 6]) is the top of the clip, so its north edge is 6.0.
    assert clipped.transform.north == 6.0


def test_clip_non_overlapping_raises() -> None:
    with pytest.raises(RasterProcessingError):
        clip_to_bbox(_layer(), BoundingBox(min_lat=50.0, min_lon=50.0, max_lat=60.0, max_lon=60.0))


def test_clip_clamps_to_raster_bounds() -> None:
    clipped = clip_to_bbox(
        _layer(), BoundingBox(min_lat=-5.0, min_lon=-5.0, max_lat=80.0, max_lon=80.0)
    )
    assert clipped.shape == (10, 10)


# --------------------------- resampling --------------------------- #
def test_resample_finer_increases_resolution() -> None:
    out = resample(_layer(), 0.5)
    assert out.shape == (20, 20)
    assert out.transform.pixel_width == pytest.approx(0.5)


def test_resample_coarser_decreases_resolution() -> None:
    out = resample(_layer(), 2.0)
    assert out.shape == (5, 5)


def test_resample_rejects_non_positive() -> None:
    with pytest.raises(RasterProcessingError):
        resample(_layer(), 0.0)


def test_resample_to_match_reference() -> None:
    ref = resample(_layer(), 2.0)
    out = resample_to_match(_layer(), ref)
    assert out.transform.pixel_width == pytest.approx(2.0)


def test_resample_preserves_nan_regions() -> None:
    data = np.ones((10, 10))
    data[:5, :] = np.nan
    out = resample(_layer(data), 0.5)
    assert np.isnan(out.data).any()
    assert np.isfinite(out.data).any()


# --------------------------- reprojection --------------------------- #
def test_reproject_same_crs_is_noop_copy() -> None:
    layer = _layer()
    out = reproject(layer, "epsg:4326")  # different case, same CRS
    assert out.shape == layer.shape
    assert out.data is not layer.data


def test_reproject_to_web_mercator_changes_crs() -> None:
    out = reproject(_layer(), "EPSG:3857")
    assert out.crs == "EPSG:3857"
    assert out.data.size > 0


# --------------------------- interpolation --------------------------- #
def test_interpolate_missing_fills_all_gaps() -> None:
    data = np.arange(100, dtype=float).reshape(10, 10)
    data[5, 5] = np.nan
    data[2, 3] = np.nan
    out = interpolate_missing(_layer(data))
    assert not np.isnan(out.data).any()


def test_interpolate_missing_all_missing_raises() -> None:
    with pytest.raises(RasterProcessingError):
        interpolate_missing(_layer(np.full((10, 10), np.nan)))


def test_interpolate_points_to_grid_idw_exact_at_sample() -> None:
    gt = GeoTransform(west=0.0, north=5.0, pixel_width=1.0, pixel_height=1.0)
    grid = interpolate_points_to_grid(
        np.array([0.5]), np.array([4.5]), np.array([42.0]), gt, (5, 5)
    )
    # Cell (0,0) centre is exactly (0.5, 4.5) → equals the sample value.
    assert grid.data[0, 0] == pytest.approx(42.0)


def test_interpolate_points_to_grid_rejects_empty() -> None:
    gt = GeoTransform(west=0.0, north=5.0, pixel_width=1.0, pixel_height=1.0)
    with pytest.raises(RasterProcessingError):
        interpolate_points_to_grid(np.array([]), np.array([]), np.array([]), gt, (5, 5))


# --------------------------- missing values --------------------------- #
def test_mask_sentinel_converts_to_nan() -> None:
    data = np.array([[1.0, -9999.0], [3.0, 4.0]])
    gt = GeoTransform(west=0.0, north=2.0, pixel_width=1.0, pixel_height=1.0)
    out = mask_sentinel(RasterLayer(data=data, transform=gt), -9999.0)
    assert np.isnan(out.data[0, 1])
    assert count_missing(out) == 1


def test_fill_constant_and_mean() -> None:
    data = np.array([[1.0, np.nan], [3.0, 5.0]])
    gt = GeoTransform(west=0.0, north=2.0, pixel_width=1.0, pixel_height=1.0)
    layer = RasterLayer(data=data, transform=gt)
    assert fill_constant(layer, 0.0).data[0, 1] == 0.0
    assert fill_with_mean(layer).data[0, 1] == pytest.approx(3.0)


def test_missing_fraction() -> None:
    data = np.array([[1.0, np.nan], [np.nan, 4.0]])
    gt = GeoTransform(west=0.0, north=2.0, pixel_width=1.0, pixel_height=1.0)
    assert missing_fraction(RasterLayer(data=data, transform=gt)) == pytest.approx(0.5)


# --------------------------- normalization --------------------------- #
def test_min_max_normalize_range_and_denormalize() -> None:
    layer = _layer()
    out, stats = min_max_normalize(layer)
    assert np.nanmin(out.data) == pytest.approx(0.0)
    assert np.nanmax(out.data) == pytest.approx(1.0)
    np.testing.assert_allclose(stats.denormalize(out.data), layer.data)


def test_z_score_normalize_mean_std() -> None:
    out, stats = z_score_normalize(_layer())
    assert np.nanmean(out.data) == pytest.approx(0.0, abs=1e-9)
    assert np.nanstd(out.data) == pytest.approx(1.0, abs=1e-9)
    assert stats.method == "z_score"


def test_normalize_constant_raster_raises() -> None:
    with pytest.raises(NormalizationError):
        min_max_normalize(_layer(np.full((10, 10), 5.0)))


def test_unit_conversions() -> None:
    gt = GeoTransform(west=0.0, north=1.0, pixel_width=1.0, pixel_height=1.0)
    k = RasterLayer(data=np.array([[300.0]]), transform=gt)
    assert kelvin_to_celsius(k).data[0, 0] == pytest.approx(26.85)
    m = RasterLayer(data=np.array([[0.005]]), transform=gt)
    assert metres_to_millimetres(m).data[0, 0] == pytest.approx(5.0)
    pa = RasterLayer(data=np.array([[101325.0]]), transform=gt)
    assert pascals_to_hectopascals(pa).data[0, 0] == pytest.approx(1013.25)
