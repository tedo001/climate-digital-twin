"""Unit tests for data.preprocessing.readers (GeoTIFF / NetCDF I/O).

The GeoTIFF tests require Rasterio and the NetCDF tests require Xarray; each is
skipped automatically if its dependency is unavailable, so the suite still runs
in a minimal environment.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from data.preprocessing.raster import GeoTransform, RasterLayer
from data.preprocessing.readers import load_raster
from utils.exceptions import UnsupportedFormatError


def _layer() -> RasterLayer:
    gt = GeoTransform(west=68.0, north=38.0, pixel_width=1.0, pixel_height=1.0)
    data = np.arange(400, dtype=float).reshape(20, 20)
    data[3, 4] = np.nan
    return RasterLayer(data=data, transform=gt, name="temperature_2m")


def test_load_raster_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFormatError):
        load_raster("somefile.csv")


def test_geotiff_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("rasterio")
    from data.preprocessing.readers import read_geotiff, write_geotiff

    src = _layer()
    path = tmp_path / "layer.tif"
    write_geotiff(src, path)

    back = read_geotiff(path)
    assert back.shape == src.shape
    assert back.transform.pixel_width == pytest.approx(1.0)
    assert back.transform.west == pytest.approx(68.0)
    # nodata cell survives the round-trip as nan
    assert np.isnan(back.data[3, 4])
    np.testing.assert_allclose(np.nan_to_num(back.data), np.nan_to_num(src.data), rtol=1e-6)


def test_load_raster_dispatches_geotiff(tmp_path: Path) -> None:
    pytest.importorskip("rasterio")
    from data.preprocessing.readers import write_geotiff

    path = tmp_path / "dispatch.tiff"
    write_geotiff(_layer(), path)
    out = load_raster(path)
    assert out.shape == (20, 20)


def test_netcdf_roundtrip(tmp_path: Path) -> None:
    xr = pytest.importorskip("xarray")
    from data.preprocessing.readers import read_netcdf

    lats = np.arange(38.0, 18.0, -1.0)  # north→south, 20 rows
    lons = np.arange(68.0, 88.0, 1.0)  # 20 cols
    values = np.arange(400, dtype=float).reshape(20, 20)
    dataset = xr.Dataset({"t2m": (("lat", "lon"), values)}, coords={"lat": lats, "lon": lons})
    path = tmp_path / "layer.nc"
    dataset.to_netcdf(path)

    back = read_netcdf(path, variable="t2m")
    assert back.shape == (20, 20)
    assert back.name == "t2m"
    assert back.transform.pixel_width == pytest.approx(1.0)
    # north-most row corresponds to the largest latitude
    assert back.transform.north == pytest.approx(38.5)


def test_netcdf_ascending_latitude_is_reoriented(tmp_path: Path) -> None:
    xr = pytest.importorskip("xarray")
    from data.preprocessing.readers import read_netcdf

    lats = np.arange(18.0, 38.0, 1.0)  # ascending → must be flipped to north-up
    lons = np.arange(68.0, 88.0, 1.0)
    values = np.tile(lats.reshape(-1, 1), (1, 20))  # each row equals its latitude
    dataset = xr.Dataset({"t2m": (("lat", "lon"), values)}, coords={"lat": lats, "lon": lons})
    path = tmp_path / "asc.nc"
    dataset.to_netcdf(path)

    back = read_netcdf(path)
    # After reorientation, row 0 must hold the northern-most latitude (37).
    assert back.data[0, 0] == pytest.approx(37.0)
