"""Data assimilation: fuse multi-source observations into ClimateState values.

Exposes the assimilation pipeline components of SAD Section 9:

* :class:`~climate.assimilation.observation_fusion.ObservationFusion` — weighted
  multi-source fusion of a single variable,
* :class:`~climate.assimilation.bias_correction.BiasCorrection` — per-source
  systematic bias removal,
* :class:`~climate.assimilation.confidence_estimator.ConfidenceEstimator` —
  agreement/corroboration/freshness confidence scoring,
* :class:`~climate.assimilation.assimilation_engine.AssimilationEngine` — the
  orchestrator producing one unified ClimateState.
"""

from __future__ import annotations

from climate.assimilation.assimilation_engine import AssimilationEngine
from climate.assimilation.bias_correction import BiasCalibration, BiasCorrection
from climate.assimilation.confidence_estimator import ConfidenceEstimator
from climate.assimilation.observation_fusion import (
    FusedResult,
    FusionContribution,
    ObservationFusion,
)

__all__ = [
    "AssimilationEngine",
    "BiasCalibration",
    "BiasCorrection",
    "ConfidenceEstimator",
    "FusedResult",
    "FusionContribution",
    "ObservationFusion",
]
