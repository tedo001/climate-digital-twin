"""Unit tests for ClimateState serialization and the persistent StateStore."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from climate.versioning.serialization import state_from_dict, state_to_dict
from climate.versioning.state_store import StateStore
from config.constants import ClimateVariableName as V
from config.constants import ClimateVariableUnit as U
from config.constants import StateType
from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.region import BoundingBox, Region, RegionLevel
from storage.db.duckdb_connector import DuckDBConnector
from utils.exceptions import StateNotFoundError

_REGION = Region(
    region_id="IN-TN",
    name="Tamil Nadu",
    level=RegionLevel.STATE,
    bounding_box=BoundingBox(min_lat=8.0, min_lon=76.0, max_lat=13.0, max_lon=80.0),
)


def _state(value: float = 30.0, parent: str | None = None) -> ClimateState:
    var = ClimateVariable(
        name=V.TEMPERATURE_2M,
        unit=U.CELSIUS,
        value=value,
        source="assimilated:era5",
        confidence=0.77,
        quality_flag="verified",
    )
    return ClimateState(
        valid_time=datetime(2024, 1, 1, tzinfo=UTC),
        state_type=StateType.NOWCAST,
        variables={"IN-TN": {V.TEMPERATURE_2M: var}},
        regions={"IN-TN": _REGION},
        parent_version_id=parent,
    )


def _store(tmp_path: Path) -> StateStore:
    return StateStore(
        connector=DuckDBConnector(db_path=tmp_path / "states.duckdb"),
        snapshots_dir=tmp_path / "snaps",
    )


# --------------------------- serialization --------------------------- #
def test_serialization_roundtrip_preserves_everything() -> None:
    state = _state(value=27.5, parent="parent-1")
    restored = state_from_dict(state_to_dict(state))
    assert restored.state_id == state.state_id
    assert restored.parent_version_id == "parent-1"
    assert restored.state_type == StateType.NOWCAST
    assert restored.valid_time == state.valid_time
    var = restored.get_variable("IN-TN", V.TEMPERATURE_2M)
    assert var is not None
    assert var.value == pytest.approx(27.5)
    assert var.unit == U.CELSIUS
    assert var.quality_flag == "verified"
    assert restored.regions["IN-TN"].bounding_box.max_lat == pytest.approx(13.0)


# --------------------------- store --------------------------- #
def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    state = _state(value=31.0)
    payload_path = store.save(state)
    assert payload_path.exists()

    loaded = store.load(state.state_id)
    assert loaded.state_id == state.state_id
    assert loaded.get_variable("IN-TN", V.TEMPERATURE_2M).value == pytest.approx(31.0)


def test_load_unknown_id_raises(tmp_path: Path) -> None:
    with pytest.raises(StateNotFoundError):
        _store(tmp_path).load("does-not-exist")


def test_exists_and_count(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.count() == 0
    state = _state()
    store.save(state)
    assert store.exists(state.state_id)
    assert store.count() == 1


def test_latest_returns_none_when_empty(tmp_path: Path) -> None:
    assert _store(tmp_path).latest() is None


def test_latest_returns_most_recent_valid_time(tmp_path: Path) -> None:
    store = _store(tmp_path)
    older = ClimateState(
        valid_time=datetime(2023, 1, 1, tzinfo=UTC),
        state_type=StateType.NOWCAST,
        variables={"IN-TN": {V.TEMPERATURE_2M: _state().variables["IN-TN"][V.TEMPERATURE_2M]}},
        regions={"IN-TN": _REGION},
    )
    newer = _state(value=33.0)  # valid_time 2024
    store.save(older)
    store.save(newer)
    assert store.latest().state_id == newer.state_id


def test_save_is_idempotent_for_same_id(tmp_path: Path) -> None:
    store = _store(tmp_path)
    state = _state()
    store.save(state)
    store.save(state)  # INSERT OR REPLACE → no duplicate / no error
    assert store.count() == 1
