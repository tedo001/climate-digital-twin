"""RiskAssessment and Recommendation domain models for the decision layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, unique

from utils.validators import require_in_range


@unique
class RiskLevel(str, Enum):
    """Categorical risk severity bands."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"


@unique
class RiskCategory(str, Enum):
    """Type of climate-related risk being assessed."""

    DROUGHT = "drought"
    FLOOD = "flood"
    HEATWAVE = "heatwave"
    CYCLONE = "cyclone"
    CROP_STRESS = "crop_stress"


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """A computed risk score for a region/category derived from predictions.

    Attributes:
        assessment_id: UUID uniquely identifying this assessment.
        region_id: Region the assessment applies to.
        category: The type of risk being assessed.
        risk_score: Numeric risk score in ``[0, 1]``.
        risk_level: Categorical band derived from ``risk_score``.
        contributing_prediction_ids: IDs of ``Prediction`` objects used as input.
        generated_at: Timestamp the assessment was produced.
        rationale: Short human-readable explanation of the score.
    """

    region_id: str
    category: RiskCategory
    risk_score: float
    risk_level: RiskLevel
    contributing_prediction_ids: tuple[str, ...]
    rationale: str
    assessment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        require_in_range(self.risk_score, minimum=0.0, maximum=1.0, field_name="risk_score")
