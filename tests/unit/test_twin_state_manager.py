"""Unit tests for climate.state_manager.TwinStateManager."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from climate.assimilation.assimilation_engine import AssimilationEngine
from climate.state_manager import TwinStateManager
from climate.versioning.state_store import StateStore
from config.constants import ClimateVariableName as V
from config.constants import ClimateVariableUnit as U
from config.constants import StateType
from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.region import BoundingBox, Region, RegionLevel
from storage.db.duckdb_connector import DuckDBConnector

_REGION = Region(
    region_id="IN-TN",
    name="Tamil Nadu",
    level=RegionLevel.STATE,
    bounding_box=BoundingBox(min_lat=8.0, min_lon=76.0, max_lat=13.0, max_lon=80.0),
)
_T0 = datetime(2024, 1, 1, tzinfo=UTC)


def _source_state(source: str, value: float, valid_time: datetime = _T0) -> ClimateState:
    var = ClimateVariable(
        name=V.TEMPERATURE_2M, unit=U.CELSIUS, value=value, source=source, confidence=0.85
    )
    return ClimateState(
        valid_time=valid_time,
        state_type=StateType.HISTORICAL,
        variables={"IN-TN": {V.TEMPERATURE_2M: var}},
        regions={"IN-TN": _REGION},
    )


def _manager(tmp_path: Path, **kwargs) -> TwinStateManager:
    store = StateStore(
        connector=DuckDBConnector(db_path=tmp_path / "s.duckdb"),
        snapshots_dir=tmp_path / "snaps",
    )
    return TwinStateManager(engine=AssimilationEngine(), store=store, **kwargs)


def test_first_update_always_commits(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    assert manager.get_current_state() is None
    committed = manager.update_state([_source_state("era5", 30.0)])
    assert manager.get_current_state().state_id == committed.state_id


def test_minor_change_is_buffered(tmp_path: Path) -> None:
    manager = _manager(tmp_path, significant_delta_fraction=0.1)
    first = manager.update_state([_source_state("era5", 30.0)])
    # ~0.3% change, same valid_time → below threshold → buffered
    second = manager.update_state([_source_state("era5", 30.1)])
    assert second.state_id == first.state_id


def test_significant_change_creates_new_version_with_lineage(tmp_path: Path) -> None:
    manager = _manager(tmp_path, significant_delta_fraction=0.1)
    first = manager.update_state([_source_state("era5", 30.0)])
    second = manager.update_state([_source_state("era5", 45.0)])  # +50% change
    assert second.state_id != first.state_id
    assert second.parent_version_id == first.state_id


def test_time_elapsed_forces_new_version(tmp_path: Path) -> None:
    manager = _manager(tmp_path, significant_delta_fraction=0.9, min_seconds_between_versions=60.0)
    first = manager.update_state([_source_state("era5", 30.0, valid_time=_T0)])
    later = _T0 + timedelta(hours=2)
    # tiny value change but 2h elapsed → significant by time
    second = manager.update_state([_source_state("era5", 30.05, valid_time=later)])
    assert second.state_id != first.state_id


def test_force_commits_even_minor_change(tmp_path: Path) -> None:
    manager = _manager(tmp_path, significant_delta_fraction=0.9)
    first = manager.update_state([_source_state("era5", 30.0)])
    second = manager.update_state([_source_state("era5", 30.01)], force=True)
    assert second.state_id != first.state_id


def test_load_current_from_store(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    committed = manager.update_state([_source_state("era5", 30.0)])
    # a fresh manager over the same store adopts the persisted state
    fresh = _manager(tmp_path)
    assert fresh.get_current_state() is None
    loaded = fresh.load_current_from_store()
    assert loaded is not None
    assert loaded.state_id == committed.state_id


def test_committed_state_is_persisted(tmp_path: Path) -> None:
    store = StateStore(
        connector=DuckDBConnector(db_path=tmp_path / "s.duckdb"),
        snapshots_dir=tmp_path / "snaps",
    )
    manager = TwinStateManager(engine=AssimilationEngine(), store=store)
    committed = manager.update_state([_source_state("era5", 30.0)])
    assert store.exists(committed.state_id)
