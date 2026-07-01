"""Per-variable confidence scoring for assimilated values.

Implements the *Confidence Scoring* box of SAD Section 9. A fused value's
confidence is derived from four transparent factors:

* **base** — the (weighted) confidence the contributing sources reported,
* **agreement** — how tightly the sources agree (small inter-source spread),
* **corroboration** — how many independent sources contributed,
* **freshness** — how recent the underlying data is (optional).

Each factor is bounded in ``[0, 1]`` and combined multiplicatively so any one
weak factor appropriately drags the score down, and the result is clamped to
``[0, 1]`` for use as :attr:`core.models.climate_variable.ClimateVariable.confidence`.
"""

from __future__ import annotations

import math

from climate.assimilation.observation_fusion import FusedResult
from utils.logger import get_logger

logger = get_logger(__name__)

_EPS = 1e-9


def _clamp01(value: float) -> float:
    """Clamp a value into the closed interval ``[0, 1]``."""
    return max(0.0, min(1.0, value))


class ConfidenceEstimator:
    """Turn fusion agreement, corroboration, and freshness into a confidence.

    Args:
        source_scale: Controls how quickly extra sources saturate corroboration;
            larger means each additional source adds less.
        freshness_halflife_hours: Data age at which the freshness factor halves.
        min_corroboration: Floor applied to the corroboration reward so a single
            trusted source is not penalized to zero.
    """

    def __init__(
        self,
        *,
        source_scale: float = 2.0,
        freshness_halflife_hours: float = 48.0,
        min_corroboration: float = 0.7,
    ) -> None:
        self._source_scale = source_scale
        self._freshness_halflife = freshness_halflife_hours
        self._min_corroboration = min_corroboration

    def estimate(
        self,
        fused: FusedResult,
        *,
        base_confidence: float,
        age_hours: float | None = None,
    ) -> float:
        """Estimate confidence for a fused value.

        Args:
            fused: The fusion result (provides spread, value, source count).
            base_confidence: Weighted base confidence of the contributing sources.
            age_hours: Age of the underlying data in hours; ``None`` disables the
                freshness penalty.

        Returns:
            A confidence score in ``[0, 1]``.
        """
        agreement = self._agreement(fused.spread, fused.value)
        corroboration = self._corroboration(fused.num_sources)
        freshness = self._freshness(age_hours)

        score = _clamp01(base_confidence) * agreement * freshness * corroboration
        result = _clamp01(score)
        logger.debug(
            "Confidence: base=%.3f agree=%.3f corrob=%.3f fresh=%.3f → %.3f",
            base_confidence,
            agreement,
            corroboration,
            freshness,
            result,
        )
        return result

    def _agreement(self, spread: float, value: float) -> float:
        """Map inter-source spread to an agreement factor in ``(0, 1]``."""
        relative_spread = spread / (abs(value) + _EPS)
        return 1.0 / (1.0 + relative_spread)

    def _corroboration(self, num_sources: int) -> float:
        """Reward independent corroboration, floored at ``min_corroboration``."""
        if num_sources <= 0:
            return self._min_corroboration
        saturation = 1.0 - math.exp(-num_sources / self._source_scale)
        return self._min_corroboration + (1.0 - self._min_corroboration) * saturation

    def _freshness(self, age_hours: float | None) -> float:
        """Exponentially decay confidence with data age (half-life based)."""
        if age_hours is None:
            return 1.0
        if age_hours <= 0:
            return 1.0
        return 0.5 ** (age_hours / self._freshness_halflife)
