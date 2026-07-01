"""Unit tests for climate.assimilation.observation_fusion."""

from __future__ import annotations

import pytest

from climate.assimilation.observation_fusion import (
    FusionContribution,
    ObservationFusion,
)
from utils.exceptions import FusionError


def test_contribution_rejects_non_positive_weight() -> None:
    with pytest.raises(FusionError):
        FusionContribution(value=1.0, source="era5", weight=0.0)


def test_effective_weight_scales_by_confidence() -> None:
    c = FusionContribution(value=1.0, source="era5", weight=2.0, confidence=0.5)
    assert c.effective_weight == pytest.approx(1.0)


def test_fuse_single_source_returns_its_value_zero_spread() -> None:
    result = ObservationFusion().fuse([FusionContribution(value=42.0, source="era5")])
    assert result.value == pytest.approx(42.0)
    assert result.spread == 0.0
    assert result.num_sources == 1


def test_fuse_weighted_mean() -> None:
    # effective weights: era5 = 2*1 = 2, power = 1*1 = 1
    contributions = [
        FusionContribution(value=30.0, source="era5", weight=2.0),
        FusionContribution(value=33.0, source="power", weight=1.0),
    ]
    result = ObservationFusion().fuse(contributions)
    assert result.value == pytest.approx((2 * 30.0 + 1 * 33.0) / 3.0)
    assert result.total_weight == pytest.approx(3.0)
    assert result.sources == ("era5", "power")


def test_fuse_spread_reflects_disagreement() -> None:
    agree = ObservationFusion().fuse([FusionContribution(30.0, "a"), FusionContribution(30.0, "b")])
    disagree = ObservationFusion().fuse(
        [FusionContribution(20.0, "a"), FusionContribution(40.0, "b")]
    )
    assert agree.spread == pytest.approx(0.0)
    assert disagree.spread > agree.spread


def test_fuse_empty_raises() -> None:
    with pytest.raises(FusionError):
        ObservationFusion().fuse([])
