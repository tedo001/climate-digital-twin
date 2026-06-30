"""ClimateState domain model.

The single authoritative, versioned snapshot of India's climate system at a
point in time (SAD Section 5.1). Immutable once constructed — updates always
create a new version via :mod:`climate.state_manager`, never in-place
mutation, satisfying SAD Section 5.3.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from config.constants import ClimateVariableName, StateType
from core.models.climate_variable import ClimateVariable
from core.models.region import Region


@dataclass(frozen=True)
class ClimateState:
    """Immutable, versioned snapshot of climate variables across regions.

    Attributes:
        state_id: UUID uniquely identifying this version.
        parent_version_id: UUID of the state this was derived from, if any.
        valid_time: The timestamp this state represents/is valid for.
        created_at: Timestamp this version object was constructed.
        state_type: Lifecycle classification (historical/nowcast/forecast/simulated).
        variables: Mapping of ``region_id -> {variable_name -> ClimateVariable}``.
        regions: Mapping of ``region_id -> Region`` included in this state.

    The raw raster grid (Xarray Dataset) referenced in SAD Section 5.1 is
    intentionally not embedded here — it is persisted separately in Zarr and
    referenced by ``state_id`` (see ``storage.cache.raster_cache``), keeping
    this object lightweight and easily passed across layer boundaries.
    """

    valid_time: datetime
    state_type: StateType
    variables: dict[str, dict[ClimateVariableName, ClimateVariable]]
    regions: dict[str, Region]
    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_version_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        missing_regions = set(self.variables.keys()) - set(self.regions.keys())
        if missing_regions:
            raise ValueError(
                f"variables reference regions not present in 'regions': {missing_regions}"
            )

    def get_variable(
        self, region_id: str, variable_name: ClimateVariableName
    ) -> ClimateVariable | None:
        """Retrieve a single variable for a region, if present.

        Args:
            region_id: Identifier of the region to query.
            variable_name: Canonical climate variable identifier.

        Returns:
            The matching :class:`ClimateVariable`, or ``None`` if absent.
        """
        return self.variables.get(region_id, {}).get(variable_name)

    def region_ids(self) -> tuple[str, ...]:
        """Return the identifiers of every region present in this state.

        Returns:
            A tuple of region identifiers.
        """
        return tuple(self.regions.keys())

    def with_updated_variables(
        self,
        new_variables: dict[str, dict[ClimateVariableName, ClimateVariable]],
        *,
        new_valid_time: datetime | None = None,
        new_state_type: StateType | None = None,
    ) -> ClimateState:
        """Create a new, immutable ``ClimateState`` derived from this one.

        Per SAD Section 5.3, states are never mutated in place; this method
        merges ``new_variables`` over a copy of the current variables and
        returns a brand-new versioned object with ``parent_version_id`` set
        to this state's ``state_id``.

        Args:
            new_variables: Mapping of region -> variable updates to merge in.
            new_valid_time: Optional new valid_time; defaults to this state's.
            new_state_type: Optional new state_type; defaults to this state's.

        Returns:
            A new :class:`ClimateState` instance with merged variables.
        """
        merged: dict[str, dict[ClimateVariableName, ClimateVariable]] = {
            region_id: dict(vars_for_region)
            for region_id, vars_for_region in self.variables.items()
        }
        for region_id, updates in new_variables.items():
            merged.setdefault(region_id, {})
            merged[region_id].update(updates)

        merged_regions = dict(self.regions)

        return ClimateState(
            valid_time=new_valid_time or self.valid_time,
            state_type=new_state_type or self.state_type,
            variables=merged,
            regions=merged_regions,
            parent_version_id=self.state_id,
        )
