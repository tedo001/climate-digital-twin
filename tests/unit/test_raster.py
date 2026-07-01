"""Unit tests for data.preprocessing.raster (RasterLayer / GeoTransform)."""

from __future__ import annotations

import numpy as np
import pytest

from data.preprocessing.raster import GeoTransform, RasterLayer


def _layer() -> RasterLayer:
    gt = GeoTransform(west=0.0, north=10.0, pixel_width=1.0, pixel_height=1.0)
    return RasterLayer(data=np.arange(100, dtype=float).reshape(10, 10), transform=gt, name="v")


def test_geotransform_rejects_non_positive_pixels() -> None:
    with pytest.raises(ValueError):
        GeoTransform(west=0.0, north=0.0, pixel_width=0.0, pixel_height=1.0)


def test_geotransform_roundtrip_xy_rowcol() -> None:
    gt = GeoTransform(west=0.0, north=10.0, pixel_width=1.0, pixel_height=1.0)
    lon, lat = gt.xy(0, 0)
    assert (lon, lat) == (0.5, 9.5)
    assert gt.rowcol(lon, lat) == (0, 0)


def test_raster_rejects_non_2d() -> None:
    gt = GeoTransform(west=0.0, north=1.0, pixel_width=1.0, pixel_height=1.0)
    with pytest.raises(ValueError):
        RasterLayer(data=np.zeros((2, 2, 2)), transform=gt)


def test_raster_shape_and_bounds() -> None:
    layer = _layer()
    assert layer.shape == (10, 10)
    bounds = layer.bounds
    assert bounds.min_lon == 0.0 and bounds.max_lon == 10.0
    assert bounds.max_lat == 10.0 and bounds.min_lat == 0.0


def test_raster_lons_lats_are_cell_centres() -> None:
    layer = _layer()
    assert layer.lons()[0] == 0.5
    assert layer.lats()[0] == 9.5  # north-most row


def test_raster_missing_mask_and_mean() -> None:
    layer = _layer()
    data = layer.data.copy()
    data[0, 0] = np.nan
    layer = layer.with_data(data)
    assert layer.missing_mask().sum() == 1
    assert layer.mean() == pytest.approx(np.nanmean(data))


def test_raster_with_data_is_independent_copy() -> None:
    layer = _layer()
    new = layer.with_data(np.zeros((10, 10)), name="w")
    assert new.name == "w"
    assert layer.name == "v"  # original unchanged
    assert np.all(new.data == 0.0)
