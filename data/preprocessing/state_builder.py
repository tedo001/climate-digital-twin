"""Assemble a standardized :class:`ClimateState` from processed rasters.

This is the output edge of the processing layer (SAD Section 6 → Climate
State). Given cleaned, region-scoped raster layers per variable, the builder
reduces each layer to a per-region area-mean, wraps it as a typed
:class:`ClimateVariable` (with canonical units and a quality flag derived from
missing-data coverage), and emits an immutable :class:`ClimateState` ready for
the assimilation/AI layers to consume.

Note: emitting the domain ``ClimateState`` is the layer's defined contract; the
data layer's dependency on ``core.models`` is the sanctioned exception in the
import contract (SAD Section 3 dependency table).
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from config.constants import (
    DEFAULT_VARIABLE_UNITS,
    ClimateVariableName,
    ClimateVariableUnit,
    StateType,
)
from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.region import Region
from data.preprocessing.clipping import clip_to_bbox
from data.preprocessing.raster import RasterLayer
from utils.exceptions import RasterProcessingError, StateConstructionError
from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_CONFIDENCE = 0.8


class ClimateStateBuilder:
    """Incrementally collect processed layers and build a :class:`ClimateState`.

    Args:
        valid_time: The timestamp the resulting state represents.
        state_type: Lifecycle classification of the state.
        default_confidence: Confidence assigned to variables when a per-layer
            value is not supplied.
    """

    def __init__(
        self,
        valid_time: datetime | None = None,
        *,
        state_type: StateType = StateType.HISTORICAL,
        default_confidence: float = _DEFAULT_CONFIDENCE,
    ) -> None:
        self._valid_time = valid_time or datetime.now(UTC)
        self._state_type = state_type
        self._default_confidence = default_confidence
        self._regions: dict[str, Region] = {}
        self._layers: dict[ClimateVariableName, tuple[RasterLayer, str, float]] = {}

    def add_region(self, region: Region) -> ClimateStateBuilder:
        """Register a region to summarize variables over.

        Args:
            region: The region to include in the state.

        Returns:
            This builder, for fluent chaining.
        """
        self._regions[region.region_id] = region
        return self

    def add_layer(
        self,
        variable: ClimateVariableName,
        layer: RasterLayer,
        *,
        source: str,
        confidence: float | None = None,
    ) -> ClimateStateBuilder:
        """Register a processed raster for one climate variable.

        Args:
            variable: The canonical variable the layer represents.
            layer: The cleaned raster (already in canonical units).
            source: Originating dataset/connector name.
            confidence: Confidence for values derived from this layer.

        Returns:
            This builder, for fluent chaining.
        """
        self._layers[variable] = (layer, source, confidence or self._default_confidence)
        return self

    def build(self) -> ClimateState:
        """Reduce every layer over every region and assemble the state.

        Returns:
            An immutable :class:`ClimateState`.

        Raises:
            StateConstructionError: If no regions were added, or no finite
                variable value could be produced for any region.
        """
        if not self._regions:
            raise StateConstructionError("Cannot build a ClimateState with no regions")

        variables: dict[str, dict[ClimateVariableName, ClimateVariable]] = {}
        for region_id, region in self._regions.items():
            region_vars = self._variables_for_region(region)
            if region_vars:
                variables[region_id] = region_vars

        if not variables:
            raise StateConstructionError(
                "No finite variable values produced for any region",
                details={"regions": list(self._regions)},
            )

        logger.info(
            "Built ClimateState over %d region(s), %d variable layer(s)",
            len(self._regions),
            len(self._layers),
        )
        return ClimateState(
            valid_time=self._valid_time,
            state_type=self._state_type,
            variables=variables,
            regions=dict(self._regions),
        )

    def _variables_for_region(self, region: Region) -> dict[ClimateVariableName, ClimateVariable]:
        """Compute the per-variable values for a single region."""
        region_vars: dict[ClimateVariableName, ClimateVariable] = {}
        for variable, (layer, source, confidence) in self._layers.items():
            try:
                clipped = clip_to_bbox(layer, region.bounding_box)
            except RasterProcessingError:
                logger.debug("Layer %s does not cover region %s", variable, region.region_id)
                continue
            value = clipped.mean()
            if not np.isfinite(value):
                continue
            quality_flag = "interpolated" if clipped.missing_mask().any() else "good"
            region_vars[variable] = ClimateVariable(
                name=variable,
                unit=_unit_for(variable),
                value=float(value),
                source=source,
                confidence=confidence,
                quality_flag=quality_flag,
            )
        return region_vars


def build_climate_state(
    regions: list[Region],
    layers: dict[ClimateVariableName, RasterLayer],
    *,
    source: str,
    valid_time: datetime | None = None,
    state_type: StateType = StateType.HISTORICAL,
    confidence: float = _DEFAULT_CONFIDENCE,
) -> ClimateState:
    """One-shot convenience wrapper around :class:`ClimateStateBuilder`.

    Args:
        regions: Regions to summarize over.
        layers: Mapping of variable → processed raster.
        source: Originating dataset/connector name for every variable.
        valid_time: Timestamp the state represents.
        state_type: Lifecycle classification.
        confidence: Confidence assigned to every derived variable.

    Returns:
        The assembled :class:`ClimateState`.
    """
    builder = ClimateStateBuilder(valid_time, state_type=state_type, default_confidence=confidence)
    for region in regions:
        builder.add_region(region)
    for variable, layer in layers.items():
        builder.add_layer(variable, layer, source=source, confidence=confidence)
    return builder.build()


def _unit_for(variable: ClimateVariableName) -> ClimateVariableUnit:
    """Resolve the canonical unit for a variable, defaulting to dimensionless."""
    return DEFAULT_VARIABLE_UNITS.get(variable, ClimateVariableUnit.DIMENSIONLESS)
