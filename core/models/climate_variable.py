"""ClimateVariable domain model.

Each variable inside a ``ClimateState`` is wrapped as a :class:`ClimateVariable`
so that units, source provenance, and confidence travel with the value
rather than being tracked separately (SAD Section 5.1).
"""

from __future__ import annotations

from dataclasses import dataclass

from config.constants import ClimateVariableName, ClimateVariableUnit
from utils.validators import require_in_range


@dataclass(frozen=True, slots=True)
class ClimateVariable:
    """A single climate variable's value with provenance and confidence.

    Attributes:
        name: Canonical variable identifier.
        unit: Unit of measurement for ``value``.
        value: The scalar value (for a single region) or area-mean value
            (for gridded data summarized to a region).
        source: Dataset/connector that produced this value (e.g. ``"era5"``).
        confidence: Confidence score in ``[0, 1]`` from assimilation.
        quality_flag: Optional categorical quality indicator (e.g. ``"good"``,
            ``"interpolated"``, ``"flagged"``).
    """

    name: ClimateVariableName
    unit: ClimateVariableUnit
    value: float
    source: str
    confidence: float
    quality_flag: str = "good"

    def __post_init__(self) -> None:
        require_in_range(self.confidence, minimum=0.0, maximum=1.0, field_name="confidence")
        if not self.source:
            raise ValueError("source must not be empty")
