"""SimulationScenario domain model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, unique

from config.constants import ClimateVariableName


@unique
class PerturbationType(str, Enum):
    """How a scenario parameter modifies the baseline state."""

    ABSOLUTE_DELTA = "absolute_delta"
    PERCENTAGE_CHANGE = "percentage_change"
    ABSOLUTE_SET = "absolute_set"


@dataclass(frozen=True, slots=True)
class ScenarioParameter:
    """A single variable perturbation within a scenario.

    Attributes:
        variable_name: Canonical climate variable to perturb.
        perturbation_type: How ``magnitude`` should be applied.
        magnitude: The perturbation magnitude (unit depends on ``perturbation_type``).
        region_ids: Regions this perturbation applies to; empty tuple means
            "all regions in the base state".
    """

    variable_name: ClimateVariableName
    perturbation_type: PerturbationType
    magnitude: float
    region_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SimulationScenario:
    """A what-if scenario to run against a baseline ``ClimateState``.

    Attributes:
        scenario_id: UUID uniquely identifying this scenario.
        name: Human-readable scenario name (e.g. ``"+2C heatwave"``).
        base_state_id: ``ClimateState.state_id`` to perturb.
        parameters: The set of variable perturbations to apply.
        created_at: Timestamp the scenario was defined.
        description: Optional free-text description of intent.
    """

    name: str
    base_state_id: str
    parameters: tuple[ScenarioParameter, ...]
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.parameters:
            raise ValueError("parameters must contain at least one ScenarioParameter")
