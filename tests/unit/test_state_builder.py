"""Unit tests for the standardized ClimateState builder."""

from __future__ import annotations

import numpy as np
import pytest

from config.constants import ClimateVariableName, ClimateVariableUnit, StateType
from core.models.climate_state import ClimateState
from core.models.region import BoundingBox, Region, RegionLevel
from data.preprocessing.raster import GeoTransform, RasterLayer
from data.preprocessing.state_builder import ClimateStateBuilder, build_climate_state
from utils.exceptions import StateConstructionError


def _region(region_id: str = "IN-TN") -> Region:
    return Region(
        region_id=region_id,
        name="Tamil Nadu",
        level=RegionLevel.STATE,
        bounding_box=BoundingBox(min_lat=8.0, min_lon=76.0, max_lat=13.0, max_lon=80.0),
    )


def _layer(value: float = 30.0, with_gap: bool = False) -> RasterLayer:
    gt = GeoTransform(west=68.0, north=38.0, pixel_width=1.0, pixel_height=1.0)
    data = np.full((30, 30), value, dtype=float)
    if with_gap:
        # Row 26 / col 9 falls inside the TN bbox clip (rows 25-29, cols 8-11).
        data[26, 9] = np.nan
    return RasterLayer(data=data, transform=gt, name="temperature_2m")


def test_build_climate_state_produces_typed_variable() -> None:
    state = build_climate_state(
        [_region()], {ClimateVariableName.TEMPERATURE_2M: _layer(30.0)}, source="era5"
    )
    assert isinstance(state, ClimateState)
    var = state.get_variable("IN-TN", ClimateVariableName.TEMPERATURE_2M)
    assert var is not None
    assert var.value == pytest.approx(30.0)
    assert var.unit == ClimateVariableUnit.CELSIUS
    assert var.source == "era5"
    assert var.quality_flag == "good"


def test_builder_flags_interpolated_when_gaps_present() -> None:
    state = (
        ClimateStateBuilder(state_type=StateType.NOWCAST)
        .add_region(_region())
        .add_layer(ClimateVariableName.TEMPERATURE_2M, _layer(30.0, with_gap=True), source="era5")
        .build()
    )
    var = state.get_variable("IN-TN", ClimateVariableName.TEMPERATURE_2M)
    assert var is not None
    assert var.quality_flag == "interpolated"
    assert state.state_type == StateType.NOWCAST


def test_builder_requires_regions() -> None:
    builder = ClimateStateBuilder()
    with pytest.raises(StateConstructionError):
        builder.build()


def test_builder_raises_when_no_finite_values() -> None:
    gt = GeoTransform(west=68.0, north=38.0, pixel_width=1.0, pixel_height=1.0)
    empty = RasterLayer(data=np.full((30, 30), np.nan), transform=gt, name="temperature_2m")
    builder = ClimateStateBuilder().add_region(_region())
    builder.add_layer(ClimateVariableName.TEMPERATURE_2M, empty, source="era5")
    with pytest.raises(StateConstructionError):
        builder.build()


def test_builder_skips_region_outside_layer_coverage() -> None:
    # Region far outside the layer extent → that region contributes nothing,
    # so with only that region the build must raise.
    far_region = Region(
        region_id="XX",
        name="Elsewhere",
        level=RegionLevel.CUSTOM,
        bounding_box=BoundingBox(min_lat=-40.0, min_lon=-40.0, max_lat=-30.0, max_lon=-30.0),
    )
    builder = ClimateStateBuilder().add_region(far_region)
    builder.add_layer(ClimateVariableName.TEMPERATURE_2M, _layer(30.0), source="era5")
    with pytest.raises(StateConstructionError):
        builder.build()


def test_state_is_immutable_snapshot() -> None:
    state = build_climate_state(
        [_region()], {ClimateVariableName.TEMPERATURE_2M: _layer(30.0)}, source="era5"
    )
    assert "IN-TN" in state.region_ids()
    assert state.parent_version_id is None
