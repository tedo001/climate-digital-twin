"""Systematic bias correction of source estimates before fusion.

Implements the *Bias Correction* box of SAD Section 9: each source/variable pair
can carry a linear calibration ``corrected = scale * raw + offset`` derived from
historical station-vs-satellite comparisons. Corrections are looked up per
``(source, variable)``; unknown pairs pass through unchanged (identity), so the
engine degrades gracefully when no calibration exists.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from config.constants import ClimateVariableName
from utils.exceptions import BiasCorrectionError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class BiasCalibration:
    """A linear ``scale * raw + offset`` calibration for one source/variable.

    Attributes:
        scale: Multiplicative factor (must be finite and non-zero).
        offset: Additive offset in the variable's canonical unit.
    """

    scale: float = 1.0
    offset: float = 0.0

    def __post_init__(self) -> None:
        if self.scale == 0:
            raise BiasCorrectionError("Bias calibration scale must be non-zero")

    def apply(self, value: float) -> float:
        """Return the bias-corrected value ``scale * value + offset``."""
        return self.scale * value + self.offset


class BiasCorrection:
    """Applies per-(source, variable) linear calibrations to raw estimates.

    Args:
        calibrations: Mapping of ``(source, variable)`` → :class:`BiasCalibration`.
    """

    def __init__(
        self,
        calibrations: dict[tuple[str, ClimateVariableName], BiasCalibration] | None = None,
    ) -> None:
        self._calibrations = dict(calibrations or {})

    def register(
        self, source: str, variable: ClimateVariableName, calibration: BiasCalibration
    ) -> None:
        """Register or replace a calibration for a source/variable pair.

        Args:
            source: Dataset/connector name the calibration applies to.
            variable: The climate variable the calibration applies to.
            calibration: The linear calibration to store.
        """
        self._calibrations[(source, variable)] = calibration

    def correct(self, source: str, variable: ClimateVariableName, value: float) -> float:
        """Apply the calibration for ``(source, variable)`` to ``value``.

        Args:
            source: Originating source name.
            variable: The climate variable being corrected.
            value: The raw value.

        Returns:
            The bias-corrected value, or ``value`` unchanged if no calibration
            is registered for the pair.
        """
        calibration = self._calibrations.get((source, variable))
        if calibration is None:
            return value
        corrected = calibration.apply(value)
        logger.debug("Bias-corrected %s/%s: %.4f → %.4f", source, variable.value, value, corrected)
        return corrected

    @staticmethod
    def learn(reference_values: Iterable[float], source_values: Iterable[float]) -> BiasCalibration:
        """Estimate an additive calibration from paired reference/source samples.

        Uses the mean difference (``reference - source``) as the offset, which
        removes a source's systematic bias relative to a trusted reference
        (e.g. ground stations) without over-fitting a scale term.

        Args:
            reference_values: Trusted reference measurements.
            source_values: The source's measurements at the same points/times.

        Returns:
            A :class:`BiasCalibration` with unit scale and the fitted offset.

        Raises:
            BiasCorrectionError: If the inputs are empty or of unequal length.
        """
        reference = list(reference_values)
        source = list(source_values)
        if not reference or len(reference) != len(source):
            raise BiasCorrectionError(
                "learn() needs non-empty, equal-length reference/source samples",
                details={"n_reference": len(reference), "n_source": len(source)},
            )
        offset = sum(r - s for r, s in zip(reference, source, strict=True)) / len(reference)
        return BiasCalibration(scale=1.0, offset=offset)
