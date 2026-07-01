"""Weighted multi-source fusion of a single climate variable.

``ObservationFusion`` implements the *Observation Fusion* box of SAD Section 9:
given several estimates of the same variable over the same region (e.g. ERA5,
NASA POWER, and a MODIS-derived value), it combines them into one value via a
weighted mean, where each contribution's weight reflects both its source
reliability and its own confidence. It also reports the weighted spread across
sources, which :class:`~climate.assimilation.confidence_estimator.ConfidenceEstimator`
turns into an agreement-based confidence score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from utils.exceptions import FusionError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class FusionContribution:
    """One source's estimate of a variable, feeding into a fusion.

    Attributes:
        value: The estimated value (already bias-corrected, canonical units).
        source: Originating dataset/connector name (e.g. ``"era5"``).
        weight: Source-reliability weight (``> 0``); higher trusts this source more.
        confidence: The source estimate's own confidence in ``[0, 1]``.
        quality_flag: Categorical quality indicator carried from processing.
    """

    value: float
    source: str
    weight: float = 1.0
    confidence: float = 1.0
    quality_flag: str = "good"

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise FusionError(
                "Fusion weight must be positive",
                details={"source": self.source, "weight": self.weight},
            )

    @property
    def effective_weight(self) -> float:
        """Weight actually used in fusion: ``weight * max(confidence, eps)``."""
        return self.weight * max(self.confidence, 1e-6)


@dataclass(frozen=True, slots=True)
class FusedResult:
    """Outcome of fusing several :class:`FusionContribution` values.

    Attributes:
        value: The weighted-mean fused value.
        sources: Names of the sources that contributed, in input order.
        spread: Weighted standard deviation across contributions (0 if single
            source) — a measure of inter-source disagreement.
        total_weight: Sum of effective weights that produced ``value``.
        contributions: The inputs that produced this result.
    """

    value: float
    sources: tuple[str, ...]
    spread: float
    total_weight: float
    contributions: tuple[FusionContribution, ...] = field(default_factory=tuple)

    @property
    def num_sources(self) -> int:
        """Number of distinct contributions fused."""
        return len(self.contributions)


class ObservationFusion:
    """Combine multiple single-variable estimates into one weighted value."""

    def fuse(self, contributions: list[FusionContribution]) -> FusedResult:
        """Fuse contributions into a single weighted-mean value.

        Args:
            contributions: Non-empty list of per-source estimates of one variable.

        Returns:
            A :class:`FusedResult` with the fused value and inter-source spread.

        Raises:
            FusionError: If ``contributions`` is empty.
        """
        if not contributions:
            raise FusionError("Cannot fuse an empty set of contributions")

        weights = [c.effective_weight for c in contributions]
        total_weight = math.fsum(weights)
        if total_weight <= 0:  # pragma: no cover - guarded by contribution validation
            raise FusionError("Total fusion weight must be positive")

        fused_value = (
            math.fsum(w * c.value for w, c in zip(weights, contributions, strict=True))
            / total_weight
        )
        spread = self._weighted_spread(contributions, weights, total_weight, fused_value)

        logger.debug(
            "Fused %d source(s) → %.4f (spread=%.4f)",
            len(contributions),
            fused_value,
            spread,
        )
        return FusedResult(
            value=fused_value,
            sources=tuple(c.source for c in contributions),
            spread=spread,
            total_weight=total_weight,
            contributions=tuple(contributions),
        )

    @staticmethod
    def _weighted_spread(
        contributions: list[FusionContribution],
        weights: list[float],
        total_weight: float,
        mean: float,
    ) -> float:
        """Compute the weighted standard deviation of contribution values."""
        if len(contributions) < 2:
            return 0.0
        variance = (
            math.fsum(
                w * (c.value - mean) ** 2 for w, c in zip(weights, contributions, strict=True)
            )
            / total_weight
        )
        return math.sqrt(max(variance, 0.0))
