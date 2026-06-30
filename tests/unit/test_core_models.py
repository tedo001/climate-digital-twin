"""Unit tests for core domain models."""

from __future__ import annotations

from datetime import datetime

import pytest

from config.constants import ClimateVariableName, ClimateVariableUnit, StateType
from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.prediction import Prediction
from core.models.region import BoundingBox, Region, RegionLevel


def _make_region(region_id: str = "IN-TN") -> Region:
    return Region(
        region_id=region_id,
        name="Tamil Nadu",
        level=RegionLevel.STATE,
        bounding_box=BoundingBox(min_lat=8.1, min_lon=76.2, max_lat=13.6, max_lon=80.3),
    )


def test_bounding_box_rejects_invalid_order() -> None:
    with pytest.raises(ValueError):
        BoundingBox(min_lat=10.0, min_lon=70.0, max_lat=5.0, max_lon=80.0)


def test_climate_state_requires_matching_regions() -> None:
    variable = ClimateVariable(
        name=ClimateVariableName.TEMPERATURE_2M,
        unit=ClimateVariableUnit.CELSIUS,
        value=28.5,
        source="era5",
        confidence=0.9,
    )
    with pytest.raises(ValueError):
        ClimateState(
            valid_time=datetime(2026, 6, 1),
            state_type=StateType.HISTORICAL,
            variables={"IN-TN": {ClimateVariableName.TEMPERATURE_2M: variable}},
            regions={},  # missing IN-TN -> should raise
        )


def test_climate_state_with_updated_variables_creates_new_version() -> None:
    region = _make_region()
    original_var = ClimateVariable(
        name=ClimateVariableName.TEMPERATURE_2M,
        unit=ClimateVariableUnit.CELSIUS,
        value=28.5,
        source="era5",
        confidence=0.9,
    )
    state = ClimateState(
        valid_time=datetime(2026, 6, 1),
        state_type=StateType.HISTORICAL,
        variables={"IN-TN": {ClimateVariableName.TEMPERATURE_2M: original_var}},
        regions={"IN-TN": region},
    )

    updated_var = ClimateVariable(
        name=ClimateVariableName.TEMPERATURE_2M,
        unit=ClimateVariableUnit.CELSIUS,
        value=30.0,
        source="era5",
        confidence=0.95,
    )
    new_state = state.with_updated_variables(
        {"IN-TN": {ClimateVariableName.TEMPERATURE_2M: updated_var}}
    )

    assert new_state.state_id != state.state_id
    assert new_state.parent_version_id == state.state_id
    assert new_state.get_variable("IN-TN", ClimateVariableName.TEMPERATURE_2M).value == 30.0
    # Original state remains unchanged (immutability).
    assert state.get_variable("IN-TN", ClimateVariableName.TEMPERATURE_2M).value == 28.5


def test_prediction_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError):
        Prediction(
            region_id="IN-TN",
            variable_name=ClimateVariableName.PRECIPITATION,
            horizon_days=7,
            predicted_value=12.3,
            unit="mm",
            confidence_score=1.5,
            model_name="monsoon_lstm",
            model_version="0.1.0",
            based_on_state_id="abc-123",
        )


def test_prediction_is_available_property() -> None:
    pred = Prediction(
        region_id="IN-TN",
        variable_name=ClimateVariableName.PRECIPITATION,
        horizon_days=7,
        predicted_value=12.3,
        unit="mm",
        confidence_score=0.0,
        model_name="monsoon_lstm",
        model_version="unavailable",
        based_on_state_id="abc-123",
    )
    assert pred.is_available is False
