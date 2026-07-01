"""Unit tests for climate.assimilation.confidence_estimator."""

from __future__ import annotations

import pytest

from climate.assimilation.confidence_estimator import ConfidenceEstimator
from climate.assimilation.observation_fusion import FusionContribution, ObservationFusion


def _fuse(*values: float):
    return ObservationFusion().fuse([FusionContribution(v, f"s{i}") for i, v in enumerate(values)])


def test_confidence_in_unit_interval() -> None:
    estimator = ConfidenceEstimator()
    score = estimator.estimate(_fuse(30.0, 31.0), base_confidence=0.8)
    assert 0.0 <= score <= 1.0


def test_agreement_beats_disagreement() -> None:
    estimator = ConfidenceEstimator()
    agree = estimator.estimate(_fuse(30.0, 30.0), base_confidence=0.9)
    disagree = estimator.estimate(_fuse(20.0, 40.0), base_confidence=0.9)
    assert agree > disagree


def test_more_sources_increase_confidence() -> None:
    estimator = ConfidenceEstimator()
    one = estimator.estimate(_fuse(30.0), base_confidence=0.8)
    three = estimator.estimate(_fuse(30.0, 30.0, 30.0), base_confidence=0.8)
    assert three > one


def test_freshness_penalizes_old_data() -> None:
    estimator = ConfidenceEstimator(freshness_halflife_hours=24.0)
    fresh = estimator.estimate(_fuse(30.0, 30.0), base_confidence=0.9, age_hours=0.0)
    stale = estimator.estimate(_fuse(30.0, 30.0), base_confidence=0.9, age_hours=48.0)
    assert stale < fresh
    # two half-lives → roughly a quarter of the fresh score
    assert stale == pytest.approx(fresh * 0.25, rel=1e-6)


def test_base_confidence_caps_result() -> None:
    estimator = ConfidenceEstimator()
    score = estimator.estimate(_fuse(30.0, 30.0), base_confidence=0.5)
    assert score <= 0.5
