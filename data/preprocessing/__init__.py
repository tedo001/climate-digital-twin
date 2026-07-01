"""Climate processing layer: reusable pipelines from raw rasters to ClimateState.

This subpackage turns heterogeneous ingested files (GeoTIFF, NetCDF) into a
standardized, immutable :class:`~core.models.climate_state.ClimateState`
(SAD Section 6). It is organized as small, pure, composable operations —

* I/O edge: :mod:`~data.preprocessing.readers` (GeoTIFF/NetCDF ↔ RasterLayer),
* raster ops: reprojection, clipping, resampling, interpolation, missing-value
  handling, normalization,
* temporal ops: :mod:`~data.preprocessing.temporal` alignment,
* features: :mod:`~data.preprocessing.feature_engineering`,
* orchestration: :mod:`~data.preprocessing.pipeline`,
* output edge: :mod:`~data.preprocessing.state_builder`.

The numeric core depends only on NumPy/SciPy/Pandas; the heavy GIS stack
(Rasterio/Xarray) is imported lazily inside the readers so the rest of the
layer stays importable without GDAL/HDF5.
"""

from __future__ import annotations

from data.preprocessing.clipping import clip_to_bbox
from data.preprocessing.feature_engineering import (
    add_lag_features,
    aggregate_to_bbox,
    build_feature_frame,
    rolling_mean,
    spatial_gradient_magnitude,
    temporal_anomaly,
)
from data.preprocessing.interpolation import interpolate_missing, interpolate_points_to_grid
from data.preprocessing.missing import (
    count_missing,
    fill_constant,
    fill_with_mean,
    mask_sentinel,
    missing_fraction,
)
from data.preprocessing.normalization import (
    NormalizationStats,
    fraction_to_percent,
    kelvin_to_celsius,
    metres_to_millimetres,
    min_max_normalize,
    pascals_to_hectopascals,
    z_score_normalize,
)
from data.preprocessing.pipeline import (
    PipelineStep,
    ProcessingPipeline,
    build_raster_pipeline,
)
from data.preprocessing.raster import GeoTransform, RasterLayer
from data.preprocessing.readers import (
    load_raster,
    read_geotiff,
    read_netcdf,
    write_geotiff,
)
from data.preprocessing.reprojection import reproject
from data.preprocessing.resampling import resample, resample_to_match
from data.preprocessing.state_builder import ClimateStateBuilder, build_climate_state
from data.preprocessing.temporal import (
    align_time_series,
    align_to_reference,
    resample_series,
)

__all__ = [
    # state builder
    "ClimateStateBuilder",
    # raster core
    "GeoTransform",
    # normalization
    "NormalizationStats",
    "PipelineStep",
    # pipeline
    "ProcessingPipeline",
    "RasterLayer",
    "add_lag_features",
    # features
    "aggregate_to_bbox",
    # temporal
    "align_time_series",
    "align_to_reference",
    "build_climate_state",
    "build_feature_frame",
    "build_raster_pipeline",
    "clip_to_bbox",
    "count_missing",
    "fill_constant",
    "fill_with_mean",
    "fraction_to_percent",
    "interpolate_missing",
    "interpolate_points_to_grid",
    "kelvin_to_celsius",
    # readers
    "load_raster",
    # missing values
    "mask_sentinel",
    "metres_to_millimetres",
    "min_max_normalize",
    "missing_fraction",
    "pascals_to_hectopascals",
    "read_geotiff",
    "read_netcdf",
    # raster ops
    "reproject",
    "resample",
    "resample_series",
    "resample_to_match",
    "rolling_mean",
    "spatial_gradient_magnitude",
    "temporal_anomaly",
    "write_geotiff",
    "z_score_normalize",
]
