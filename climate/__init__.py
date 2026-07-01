"""Climate Intelligence Layer: build/update the authoritative ClimateState.

This layer turns per-source :class:`~core.models.climate_state.ClimateState`
snapshots (from the data layer) into one unified, versioned, persisted state via
data assimilation (SAD Sections 5 and 9). Public entry points:

* :class:`~climate.assimilation.assimilation_engine.AssimilationEngine` — fuse
  multiple datasets into one unified ClimateState,
* :class:`~climate.state_manager.TwinStateManager` — the single writer that
  assimilates, versions, persists, and exposes the current state.
"""

from __future__ import annotations

from climate.assimilation import (
    AssimilationEngine,
    BiasCalibration,
    BiasCorrection,
    ConfidenceEstimator,
    FusedResult,
    FusionContribution,
    ObservationFusion,
)
from climate.state_manager import TwinStateManager
from climate.versioning import StateStore

__all__ = [
    "AssimilationEngine",
    "BiasCalibration",
    "BiasCorrection",
    "ConfidenceEstimator",
    "FusedResult",
    "FusionContribution",
    "ObservationFusion",
    "StateStore",
    "TwinStateManager",
]
