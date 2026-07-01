"""Unit tests for climate.assimilation.bias_correction."""

from __future__ import annotations

import pytest

from climate.assimilation.bias_correction import BiasCalibration, BiasCorrection
from config.constants import ClimateVariableName
from utils.exceptions import BiasCorrectionError


def test_calibration_rejects_zero_scale() -> None:
    with pytest.raises(BiasCorrectionError):
        BiasCalibration(scale=0.0)


def test_calibration_apply_linear() -> None:
    calibration = BiasCalibration(scale=2.0, offset=1.0)
    assert calibration.apply(10.0) == pytest.approx(21.0)


def test_correct_unknown_pair_is_identity() -> None:
    corrector = BiasCorrection()
    assert corrector.correct("era5", ClimateVariableName.TEMPERATURE_2M, 25.0) == 25.0


def test_correct_applies_registered_calibration() -> None:
    corrector = BiasCorrection()
    corrector.register(
        "modis", ClimateVariableName.TEMPERATURE_2M, BiasCalibration(scale=1.0, offset=-2.0)
    )
    assert corrector.correct("modis", ClimateVariableName.TEMPERATURE_2M, 30.0) == pytest.approx(
        28.0
    )
    # a different source remains unaffected
    assert corrector.correct("era5", ClimateVariableName.TEMPERATURE_2M, 30.0) == 30.0


def test_learn_offset_from_paired_samples() -> None:
    # reference is consistently 1.5 higher than the source → offset +1.5
    calibration = BiasCorrection.learn([11.5, 21.5, 31.5], [10.0, 20.0, 30.0])
    assert calibration.offset == pytest.approx(1.5)
    assert calibration.scale == pytest.approx(1.0)


def test_learn_rejects_mismatched_lengths() -> None:
    with pytest.raises(BiasCorrectionError):
        BiasCorrection.learn([1.0, 2.0], [1.0])


def test_learn_rejects_empty() -> None:
    with pytest.raises(BiasCorrectionError):
        BiasCorrection.learn([], [])
