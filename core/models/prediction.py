"""Prediction domain model.

Every model output is wrapped as a :class:`Prediction` carrying an explicit
``confidence_score`` so uncertainty is never silently dropped (SAD "Risks"
section / Final Architecture Review).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from config.constants import ClimateVariableName
from utils.validators import require_in_range


@dataclass(frozen=True, slots=True)
class Prediction:
    """A single model prediction for one variable, region, and horizon.

    Attributes:
        prediction_id: UUID uniquely identifying this prediction.
        region_id: Region the prediction applies to.
        variable_name: Canonical climate variable being predicted.
        horizon_days: Number of days ahead from ``based_on_state_id``'s valid_time.
        predicted_value: The model's point estimate.
        unit: Unit of measurement for ``predicted_value``.
        confidence_score: Confidence in ``[0, 1]`` from the confidence estimator.
        model_name: Name of the model (from the model registry) that produced this.
        model_version: Version string of the model checkpoint used.
        based_on_state_id: ``ClimateState.state_id`` used as input features.
        generated_at: Timestamp the prediction was produced.
        lower_bound: Optional lower bound of a confidence interval.
        upper_bound: Optional upper bound of a confidence interval.
    """

    region_id: str
    variable_name: ClimateVariableName
    horizon_days: int
    predicted_value: float
    unit: str
    confidence_score: float
    model_name: str
    model_version: str
    based_on_state_id: str
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    lower_bound: float | None = None
    upper_bound: float | None = None

    def __post_init__(self) -> None:
        require_in_range(
            self.confidence_score, minimum=0.0, maximum=1.0, field_name="confidence_score"
        )
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound > self.upper_bound
        ):
            raise ValueError("lower_bound must not exceed upper_bound")

    @property
    def is_available(self) -> bool:
        """Whether this represents an actual prediction vs. a degraded fallback.

        A model that failed to load reports ``confidence_score == 0.0`` and
        ``model_version == "unavailable"`` per SAD Section 16 fallback policy.
        """
        return self.model_version != "unavailable"
