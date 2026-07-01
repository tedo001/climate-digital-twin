"""Unit tests for climate.assimilation.assimilation_engine."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from climate.assimilation.assimilation_engine import AssimilationEngine
from climate.assimilation.bias_correction import BiasCalibration, BiasCorrection
from config.constants import ClimateVariableName as V
from config.constants import ClimateVariableUnit as U
from config.constants import StateType
from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.region import BoundingBox, Region, RegionLevel
from utils.exceptions import AssimilationError

_REGION = Region(
    region_id="IN-TN",
    name="Tamil Nadu",
    level=RegionLevel.STATE,
    bounding_box=BoundingBox(min_lat=8.0, min_lon=76.0, max_lat=13.0, max_lon=80.0),
)
_VALID_TIME = datetime(2024, 1, 1, tzinfo=UTC)


def _state(source: str, value: float, confidence: float = 0.85, variable: V = V.TEMPERATURE_2M):
    unit = U.CELSIUS if variable == V.TEMPERATURE_2M else U.MILLIMETER
    var = ClimateVariable(
        name=variable, unit=unit, value=value, source=source, confidence=confidence
    )
    return ClimateState(
        valid_time=_VALID_TIME,
        state_type=StateType.HISTORICAL,
        variables={"IN-TN": {variable: var}},
        regions={"IN-TN": _REGION},
    )


def test_assimilate_empty_raises() -> None:
    with pytest.raises(AssimilationError):
        AssimilationEngine().assimilate([])


def test_assimilate_single_source_passthrough_value() -> None:
    unified = AssimilationEngine().assimilate([_state("era5", 30.0)])
    var = unified.get_variable("IN-TN", V.TEMPERATURE_2M)
    assert var is not None
    assert var.value == pytest.approx(30.0)
    assert var.source == "assimilated:era5"


def test_assimilate_weighted_fusion_of_multiple_sources() -> None:
    engine = AssimilationEngine(source_weights={"era5": 3.0, "nasa_power": 1.0})
    unified = engine.assimilate(
        [_state("era5", 30.0, confidence=1.0), _state("nasa_power", 34.0, confidence=1.0)]
    )
    var = unified.get_variable("IN-TN", V.TEMPERATURE_2M)
    # weighted mean: (3*30 + 1*34) / 4 = 31.0
    assert var.value == pytest.approx(31.0)
    assert var.quality_flag == "verified"  # 2 agreeing sources
    assert var.source == "assimilated:era5+nasa_power"


def test_assimilate_tracks_confidence_per_variable() -> None:
    unified = AssimilationEngine().assimilate(
        [_state("era5", 30.0, 0.9), _state("nasa_power", 30.0, 0.9)]
    )
    var = unified.get_variable("IN-TN", V.TEMPERATURE_2M)
    assert 0.0 < var.confidence <= 1.0


def test_assimilate_applies_bias_correction_before_fusion() -> None:
    bias = BiasCorrection()
    # remove a known +5 warm bias in the modis source
    bias.register("modis", V.TEMPERATURE_2M, BiasCalibration(scale=1.0, offset=-5.0))
    engine = AssimilationEngine(bias_correction=bias)
    unified = engine.assimilate([_state("modis", 35.0, confidence=1.0)])
    assert unified.get_variable("IN-TN", V.TEMPERATURE_2M).value == pytest.approx(30.0)


def test_assimilate_merges_distinct_variables_from_sources() -> None:
    unified = AssimilationEngine().assimilate(
        [
            _state("era5", 30.0, variable=V.TEMPERATURE_2M),
            _state("gpm", 5.0, variable=V.PRECIPITATION),
        ]
    )
    region_vars = unified.variables["IN-TN"]
    assert V.TEMPERATURE_2M in region_vars
    assert V.PRECIPITATION in region_vars


def test_assimilate_sets_lineage_and_type() -> None:
    unified = AssimilationEngine().assimilate(
        [_state("era5", 30.0)], state_type=StateType.NOWCAST, parent_version_id="parent-123"
    )
    assert unified.state_type == StateType.NOWCAST
    assert unified.parent_version_id == "parent-123"


def test_disagreeing_sources_lower_confidence_flag() -> None:
    unified = AssimilationEngine().assimilate(
        [_state("era5", 5.0, 0.5), _state("nasa_power", 60.0, 0.5)]
    )
    var = unified.get_variable("IN-TN", V.TEMPERATURE_2M)
    assert var.confidence < 0.5
