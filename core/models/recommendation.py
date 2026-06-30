"""Recommendation domain model for the decision layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, unique


@unique
class RecommendationPriority(str, Enum):
    """Urgency level of a recommendation."""

    INFORMATIONAL = "informational"
    ADVISORY = "advisory"
    URGENT = "urgent"


@dataclass(frozen=True, slots=True)
class Recommendation:
    """An actionable recommendation derived from one or more risk assessments.

    Attributes:
        recommendation_id: UUID uniquely identifying this recommendation.
        region_id: Region the recommendation applies to.
        title: Short summary line.
        description: Full recommendation text.
        priority: Urgency level.
        based_on_assessment_ids: IDs of ``RiskAssessment`` objects used as input.
        generated_at: Timestamp the recommendation was produced.
    """

    region_id: str
    title: str
    description: str
    priority: RecommendationPriority
    based_on_assessment_ids: tuple[str, ...]
    recommendation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("title must not be empty")
