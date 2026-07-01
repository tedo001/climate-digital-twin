"""Unit tests for the reusable processing pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from core.models.region import BoundingBox
from data.preprocessing.pipeline import (
    PipelineStep,
    ProcessingPipeline,
    build_raster_pipeline,
)
from data.preprocessing.raster import GeoTransform, RasterLayer
from utils.exceptions import PipelineError


def _layer() -> RasterLayer:
    gt = GeoTransform(west=0.0, north=10.0, pixel_width=1.0, pixel_height=1.0)
    data = np.arange(100, dtype=float).reshape(10, 10)
    data[5, 5] = np.nan
    return RasterLayer(data=data, transform=gt, name="temperature_2m")


def test_pipeline_runs_steps_in_order() -> None:
    pipe: ProcessingPipeline[int] = ProcessingPipeline(
        [PipelineStep("add", lambda x: x + 1), PipelineStep("double", lambda x: x * 2)]
    )
    assert pipe.run(3) == 8  # (3+1)*2


def test_pipeline_fluent_add() -> None:
    pipe: ProcessingPipeline[int] = ProcessingPipeline([])
    pipe.add("inc", lambda x: x + 1).add("inc2", lambda x: x + 2)
    assert len(pipe) == 2
    assert pipe.run(0) == 3


def test_pipeline_wraps_step_errors() -> None:
    def boom(_: int) -> int:
        raise ValueError("kaboom")

    pipe: ProcessingPipeline[int] = ProcessingPipeline([PipelineStep("boom", boom)])
    with pytest.raises(PipelineError) as exc_info:
        pipe.run(1)
    assert exc_info.value.details["step"] == "boom"


def test_build_raster_pipeline_full_chain() -> None:
    pipe = build_raster_pipeline(
        clip_bbox=BoundingBox(min_lat=1.0, min_lon=1.0, max_lat=8.0, max_lon=8.0),
        target_resolution_deg=0.5,
        fill_gaps=True,
    )
    step_names = [s.name for s in pipe.steps]
    assert step_names == ["clip", "resample", "fill_missing"]
    out = pipe.run(_layer())
    assert not np.isnan(out.data).any()
    assert out.transform.pixel_width == pytest.approx(0.5)


def test_build_raster_pipeline_selective_stages() -> None:
    pipe = build_raster_pipeline(fill_gaps=False)
    assert len(pipe) == 0
    layer = _layer()
    # An empty pipeline returns the input unchanged.
    assert pipe.run(layer) is layer


def test_build_raster_pipeline_with_normalizer() -> None:
    from data.preprocessing.normalization import min_max_normalize

    pipe = build_raster_pipeline(
        fill_gaps=True, normalizer=lambda layer: min_max_normalize(layer)[0]
    )
    out = pipe.run(_layer())
    assert np.nanmax(out.data) == pytest.approx(1.0)
