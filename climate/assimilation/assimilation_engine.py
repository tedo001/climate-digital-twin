"""The assimilation orchestrator: many source states → one unified ClimateState.

``AssimilationEngine`` is the single orchestrator of SAD Section 9. Given several
per-source :class:`~core.models.climate_state.ClimateState` snapshots (each
produced by the processing layer for one dataset), it:

1. bias-corrects every source estimate (:mod:`~climate.assimilation.bias_correction`),
2. fuses the estimates per ``(region, variable)`` with source-reliability weights
   (:mod:`~climate.assimilation.observation_fusion`),
3. scores each fused value's confidence
   (:mod:`~climate.assimilation.confidence_estimator`), and
4. assembles one immutable, unified ``ClimateState`` carrying per-variable
   confidence and quality flags.

It performs no persistence; committing/versioning is the responsibility of
:class:`~climate.state_manager.TwinStateManager`.
"""

from __future__ import annotations

from collections.abc import Sequence

from climate.assimilation.bias_correction import BiasCorrection
from climate.assimilation.confidence_estimator import ConfidenceEstimator
from climate.assimilation.observation_fusion import (
    FusedResult,
    FusionContribution,
    ObservationFusion,
)
from config.constants import (
    DEFAULT_VARIABLE_UNITS,
    ClimateVariableName,
    ClimateVariableUnit,
    StateType,
)
from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.region import Region
from utils.exceptions import AssimilationError
from utils.logger import get_logger

logger = get_logger(__name__)

_FUSED_SOURCE = "assimilated"
_LOW_CONFIDENCE_THRESHOLD = 0.4


class AssimilationEngine:
    """Fuse multiple single-source states into one authoritative ClimateState.

    Args:
        source_weights: Per-source reliability weights (default weight is 1.0 for
            any source not listed).
        bias_correction: Bias-correction stage; a pass-through instance is
            created if omitted.
        fusion: The fusion strategy; a default :class:`ObservationFusion` is used
            if omitted.
        confidence_estimator: Confidence scorer; a default is used if omitted.
    """

    def __init__(
        self,
        source_weights: dict[str, float] | None = None,
        *,
        bias_correction: BiasCorrection | None = None,
        fusion: ObservationFusion | None = None,
        confidence_estimator: ConfidenceEstimator | None = None,
    ) -> None:
        self._source_weights = dict(source_weights or {})
        self._bias = bias_correction or BiasCorrection()
        self._fusion = fusion or ObservationFusion()
        self._confidence = confidence_estimator or ConfidenceEstimator()

    def assimilate(
        self,
        states: Sequence[ClimateState],
        *,
        state_type: StateType = StateType.NOWCAST,
        parent_version_id: str | None = None,
    ) -> ClimateState:
        """Combine per-source states into one unified, versioned ClimateState.

        Args:
            states: The per-source states to fuse (at least one).
            state_type: Lifecycle classification for the produced state.
            parent_version_id: Lineage pointer to the state this supersedes.

        Returns:
            A new immutable :class:`ClimateState` with fused values and confidence.

        Raises:
            AssimilationError: If ``states`` is empty or yields no fused values.
        """
        if not states:
            raise AssimilationError("Cannot assimilate an empty set of states")

        regions = self._merge_regions(states)
        valid_time = max(state.valid_time for state in states)

        fused_variables: dict[str, dict[ClimateVariableName, ClimateVariable]] = {}
        for region_id in regions:
            region_vars = self._fuse_region(region_id, states)
            if region_vars:
                fused_variables[region_id] = region_vars

        if not fused_variables:
            raise AssimilationError(
                "Assimilation produced no fused variables",
                details={"num_states": len(states)},
            )

        logger.info(
            "Assimilated %d source state(s) into unified state over %d region(s)",
            len(states),
            len(fused_variables),
        )
        return ClimateState(
            valid_time=valid_time,
            state_type=state_type,
            variables=fused_variables,
            regions={rid: regions[rid] for rid in fused_variables},
            parent_version_id=parent_version_id,
        )

    def _merge_regions(self, states: Sequence[ClimateState]) -> dict[str, Region]:
        """Return the union of regions across all input states."""
        merged: dict[str, Region] = {}
        for state in states:
            merged.update(state.regions)
        return merged

    def _fuse_region(
        self, region_id: str, states: Sequence[ClimateState]
    ) -> dict[ClimateVariableName, ClimateVariable]:
        """Fuse every variable available for one region across all states."""
        contributions_by_variable: dict[ClimateVariableName, list[FusionContribution]] = {}
        for state in states:
            for variable_name, variable in state.variables.get(region_id, {}).items():
                corrected = self._bias.correct(variable.source, variable_name, variable.value)
                contribution = FusionContribution(
                    value=corrected,
                    source=variable.source,
                    weight=self._source_weights.get(variable.source, 1.0),
                    confidence=variable.confidence,
                    quality_flag=variable.quality_flag,
                )
                contributions_by_variable.setdefault(variable_name, []).append(contribution)

        region_vars: dict[ClimateVariableName, ClimateVariable] = {}
        for variable_name, contributions in contributions_by_variable.items():
            region_vars[variable_name] = self._fuse_variable(variable_name, contributions)
        return region_vars

    def _fuse_variable(
        self, variable_name: ClimateVariableName, contributions: list[FusionContribution]
    ) -> ClimateVariable:
        """Fuse one variable's contributions into a confidence-scored value."""
        fused = self._fusion.fuse(contributions)
        base_confidence = self._weighted_base_confidence(contributions)
        confidence = self._confidence.estimate(fused, base_confidence=base_confidence)
        return ClimateVariable(
            name=variable_name,
            unit=_unit_for(variable_name),
            value=fused.value,
            source=self._fused_source_label(fused),
            confidence=confidence,
            quality_flag=self._quality_flag(fused, confidence),
        )

    @staticmethod
    def _weighted_base_confidence(contributions: list[FusionContribution]) -> float:
        """Return the weight-weighted mean of the contributions' confidences."""
        total_weight = sum(c.weight for c in contributions)
        if total_weight <= 0:  # pragma: no cover - guarded by validation
            return 0.0
        return sum(c.weight * c.confidence for c in contributions) / total_weight

    @staticmethod
    def _fused_source_label(fused: FusedResult) -> str:
        """Build a provenance label naming the fused sources."""
        unique = sorted(set(fused.sources))
        return f"{_FUSED_SOURCE}:{'+'.join(unique)}"

    @staticmethod
    def _quality_flag(fused: FusedResult, confidence: float) -> str:
        """Derive a SAD-style quality flag for the fused value."""
        if confidence < _LOW_CONFIDENCE_THRESHOLD:
            return "low_confidence"
        if fused.num_sources >= 2:
            return "verified"
        return fused.contributions[0].quality_flag


def _unit_for(variable: ClimateVariableName) -> ClimateVariableUnit:
    """Resolve the canonical unit for a variable, defaulting to dimensionless."""
    return DEFAULT_VARIABLE_UNITS.get(variable, ClimateVariableUnit.DIMENSIONLESS)
