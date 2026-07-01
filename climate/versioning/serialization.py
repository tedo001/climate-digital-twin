"""JSON (de)serialization for :class:`ClimateState` snapshot payloads.

``ClimateState`` intentionally holds only lightweight per-region scalar
variables (raster payloads live elsewhere, SAD Section 5.1), so a snapshot
serializes cleanly to a JSON document. These helpers are the single definition
of that on-disk format, used by :class:`~climate.versioning.state_store.StateStore`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from config.constants import ClimateVariableName, ClimateVariableUnit, StateType
from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.region import BoundingBox, Region, RegionLevel


def state_to_dict(state: ClimateState) -> dict[str, Any]:
    """Serialize a :class:`ClimateState` to a JSON-safe dictionary.

    Args:
        state: The state to serialize.

    Returns:
        A nested ``dict`` fully describing the state.
    """
    return {
        "state_id": state.state_id,
        "parent_version_id": state.parent_version_id,
        "valid_time": state.valid_time.isoformat(),
        "created_at": state.created_at.isoformat(),
        "state_type": state.state_type.value,
        "regions": {rid: _region_to_dict(region) for rid, region in state.regions.items()},
        "variables": {
            rid: {name.value: _variable_to_dict(var) for name, var in region_vars.items()}
            for rid, region_vars in state.variables.items()
        },
    }


def state_from_dict(payload: dict[str, Any]) -> ClimateState:
    """Reconstruct a :class:`ClimateState` from :func:`state_to_dict` output.

    Args:
        payload: The serialized state dictionary.

    Returns:
        The reconstructed :class:`ClimateState` (preserving ids and lineage).
    """
    regions = {rid: _region_from_dict(data) for rid, data in payload["regions"].items()}
    variables: dict[str, dict[ClimateVariableName, ClimateVariable]] = {}
    for rid, region_vars in payload["variables"].items():
        variables[rid] = {
            ClimateVariableName(name): _variable_from_dict(var) for name, var in region_vars.items()
        }
    return ClimateState(
        valid_time=datetime.fromisoformat(payload["valid_time"]),
        state_type=StateType(payload["state_type"]),
        variables=variables,
        regions=regions,
        state_id=payload["state_id"],
        parent_version_id=payload.get("parent_version_id"),
        created_at=datetime.fromisoformat(payload["created_at"]),
    )


def _region_to_dict(region: Region) -> dict[str, Any]:
    box = region.bounding_box
    return {
        "region_id": region.region_id,
        "name": region.name,
        "level": region.level.value,
        "bounding_box": {
            "min_lat": box.min_lat,
            "min_lon": box.min_lon,
            "max_lat": box.max_lat,
            "max_lon": box.max_lon,
        },
        "parent_region_id": region.parent_region_id,
    }


def _region_from_dict(data: dict[str, Any]) -> Region:
    box = data["bounding_box"]
    return Region(
        region_id=data["region_id"],
        name=data["name"],
        level=RegionLevel(data["level"]),
        bounding_box=BoundingBox(
            min_lat=box["min_lat"],
            min_lon=box["min_lon"],
            max_lat=box["max_lat"],
            max_lon=box["max_lon"],
        ),
        parent_region_id=data.get("parent_region_id"),
    )


def _variable_to_dict(variable: ClimateVariable) -> dict[str, Any]:
    return {
        "name": variable.name.value,
        "unit": variable.unit.value,
        "value": variable.value,
        "source": variable.source,
        "confidence": variable.confidence,
        "quality_flag": variable.quality_flag,
    }


def _variable_from_dict(data: dict[str, Any]) -> ClimateVariable:
    return ClimateVariable(
        name=ClimateVariableName(data["name"]),
        unit=ClimateVariableUnit(data["unit"]),
        value=data["value"],
        source=data["source"],
        confidence=data["confidence"],
        quality_flag=data.get("quality_flag", "good"),
    )
