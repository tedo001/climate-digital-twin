"""Format readers/writers converting GeoTIFF and NetCDF to :class:`RasterLayer`.

This is the only module that touches the heavy GIS stack (Rasterio, Xarray),
and it does so through *lazy* imports so the rest of the processing layer stays
importable — and unit-testable — in environments without GDAL/HDF5 installed.

Supported formats are dispatched by file extension:

* ``.tif`` / ``.tiff`` → GeoTIFF via Rasterio
* ``.nc`` / ``.nc4`` / ``.netcdf`` → NetCDF via Xarray
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from data.preprocessing.raster import GeoTransform, RasterLayer
from utils.exceptions import RasterReadError, UnsupportedFormatError
from utils.logger import get_logger

logger = get_logger(__name__)

_GEOTIFF_SUFFIXES = {".tif", ".tiff"}
_NETCDF_SUFFIXES = {".nc", ".nc4", ".netcdf"}


def load_raster(path: Path | str, **kwargs: Any) -> RasterLayer:
    """Read a raster file into a :class:`RasterLayer`, dispatching by extension.

    Args:
        path: Path to a GeoTIFF or NetCDF file.
        **kwargs: Forwarded to the format-specific reader (e.g. ``variable``,
            ``band`` for NetCDF/GeoTIFF respectively).

    Returns:
        The decoded :class:`RasterLayer`.

    Raises:
        UnsupportedFormatError: If the extension is neither GeoTIFF nor NetCDF.
        RasterReadError: If decoding fails.
    """
    suffix = Path(path).suffix.lower()
    if suffix in _GEOTIFF_SUFFIXES:
        return read_geotiff(path, **kwargs)
    if suffix in _NETCDF_SUFFIXES:
        return read_netcdf(path, **kwargs)
    raise UnsupportedFormatError(
        "No reader registered for file extension",
        details={"path": str(path), "suffix": suffix},
    )


def read_geotiff(path: Path | str, band: int = 1) -> RasterLayer:
    """Read a single band of a GeoTIFF into a :class:`RasterLayer`.

    Args:
        path: Path to the GeoTIFF file.
        band: 1-indexed band to read.

    Returns:
        The decoded :class:`RasterLayer` (nodata cells converted to ``nan``).

    Raises:
        RasterReadError: If Rasterio is unavailable or reading fails.
    """
    try:
        import rasterio
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RasterReadError(
            "Rasterio is required to read GeoTIFF files", details={"path": str(path)}
        ) from exc

    try:
        with rasterio.open(path) as dataset:
            array = dataset.read(band).astype(float)
            transform = dataset.transform
            crs = str(dataset.crs) if dataset.crs else "EPSG:4326"
            nodata = dataset.nodata
    except (OSError, ValueError, IndexError) as exc:
        raise RasterReadError(
            "Failed to read GeoTIFF", details={"path": str(path), "error": str(exc)}
        ) from exc

    if nodata is not None:
        array = np.where(array == nodata, np.nan, array)

    geo = GeoTransform(
        west=transform.c,
        north=transform.f,
        pixel_width=abs(transform.a),
        pixel_height=abs(transform.e),
    )
    return RasterLayer(data=array, transform=geo, crs=crs, nodata=nodata, name=Path(path).stem)


def read_netcdf(
    path: Path | str,
    variable: str | None = None,
    *,
    time_index: int = 0,
) -> RasterLayer:
    """Read one variable/time-slice of a NetCDF file into a :class:`RasterLayer`.

    Args:
        path: Path to the NetCDF file.
        variable: Name of the data variable to read; defaults to the sole
            (or first) data variable in the file.
        time_index: Index along the time dimension to extract, if present.

    Returns:
        The decoded :class:`RasterLayer`.

    Raises:
        RasterReadError: If Xarray is unavailable or reading fails.
    """
    try:
        import xarray as xr
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RasterReadError(
            "Xarray is required to read NetCDF files", details={"path": str(path)}
        ) from exc

    try:
        with xr.open_dataset(path) as dataset:
            var_name = variable or _default_variable(dataset)
            data_array = dataset[var_name]
            data_array = _select_time(data_array, time_index)
            lat_name, lon_name = _coordinate_names(data_array)
            values, lats, lons = _oriented_grid(data_array, lat_name, lon_name)
    except KeyError as exc:
        raise RasterReadError(
            "Variable not found in NetCDF", details={"path": str(path), "variable": variable}
        ) from exc
    except (OSError, ValueError) as exc:
        raise RasterReadError(
            "Failed to read NetCDF", details={"path": str(path), "error": str(exc)}
        ) from exc

    pixel_height = float(abs(lats[1] - lats[0])) if lats.size > 1 else 1.0
    pixel_width = float(abs(lons[1] - lons[0])) if lons.size > 1 else 1.0
    geo = GeoTransform(
        west=float(lons.min()) - pixel_width / 2.0,
        north=float(lats.max()) + pixel_height / 2.0,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
    )
    return RasterLayer(data=values.astype(float), transform=geo, crs="EPSG:4326", name=var_name)


def write_geotiff(layer: RasterLayer, path: Path | str) -> Path:
    """Persist a :class:`RasterLayer` as a single-band GeoTIFF.

    Primarily used to materialize processed rasters (and by the test-suite for
    round-trip verification).

    Args:
        layer: The raster to write.
        path: Destination ``.tif``/``.tiff`` path.

    Returns:
        The path written.

    Raises:
        RasterReadError: If Rasterio is unavailable or writing fails.
    """
    try:
        import rasterio
        from rasterio.transform import from_origin
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RasterReadError(
            "Rasterio is required to write GeoTIFF files", details={"path": str(path)}
        ) from exc

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(
        layer.transform.west,
        layer.transform.north,
        layer.transform.pixel_width,
        layer.transform.pixel_height,
    )
    nodata = layer.nodata if layer.nodata is not None else -9999.0
    array = np.where(np.isnan(layer.data), nodata, layer.data)
    try:
        with rasterio.open(
            dest,
            "w",
            driver="GTiff",
            height=layer.rows,
            width=layer.cols,
            count=1,
            dtype="float64",
            crs=layer.crs,
            transform=transform,
            nodata=nodata,
        ) as dataset:
            dataset.write(array, 1)
    except (OSError, ValueError) as exc:  # pragma: no cover - defensive
        raise RasterReadError(
            "Failed to write GeoTIFF", details={"path": str(dest), "error": str(exc)}
        ) from exc
    return dest


def _default_variable(dataset: Any) -> str:
    """Pick the sole/first data variable in an Xarray dataset."""
    names = list(dataset.data_vars)
    if not names:
        raise RasterReadError("NetCDF file contains no data variables")
    return str(names[0])


def _select_time(data_array: Any, time_index: int) -> Any:
    """Reduce a possible time dimension to a single 2-D slice."""
    for candidate in ("time", "valid_time", "t"):
        if candidate in data_array.dims:
            return data_array.isel({candidate: time_index})
    return data_array


def _coordinate_names(data_array: Any) -> tuple[str, str]:
    """Resolve the latitude and longitude coordinate names of an array."""
    lat_name = next((c for c in ("lat", "latitude", "y") if c in data_array.coords), None)
    lon_name = next((c for c in ("lon", "longitude", "x") if c in data_array.coords), None)
    if lat_name is None or lon_name is None:
        raise RasterReadError(
            "Could not identify lat/lon coordinates", details={"dims": list(data_array.dims)}
        )
    return lat_name, lon_name


def _oriented_grid(
    data_array: Any, lat_name: str, lon_name: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(values, lats, lons)`` with latitudes ordered north→south."""
    array = data_array.transpose(lat_name, lon_name)
    lats = np.asarray(array[lat_name].values, dtype=float)
    lons = np.asarray(array[lon_name].values, dtype=float)
    values = np.asarray(array.values, dtype=float)
    if lats.size > 1 and lats[0] < lats[-1]:
        # Flip so row 0 is the northern-most band (our convention).
        values = values[::-1, :]
        lats = lats[::-1]
    return values, lats, lons
