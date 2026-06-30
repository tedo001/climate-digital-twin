"""Domain models: typed, immutable dataclasses shared across every layer.

Per SAD Section 3, this `__init__.py` re-export list is the public API
boundary for the ``core.models`` package.
"""

from core.models.climate_state import ClimateState
from core.models.climate_variable import ClimateVariable
from core.models.metadata import DatasetMetadata
from core.models.prediction import Prediction
from core.models.recommendation import Recommendation, RecommendationPriority
from core.models.region import BoundingBox, Region, RegionLevel
from core.models.risk_assessment import RiskAssessment, RiskCategory, RiskLevel
from core.models.satellite_frame import SatelliteFrame
from core.models.simulation_scenario import (
    PerturbationType,
    ScenarioParameter,
    SimulationScenario,
)
from core.models.weather_observation import WeatherObservation

__all__ = [
    "BoundingBox",
    "ClimateState",
    "ClimateVariable",
    "DatasetMetadata",
    "PerturbationType",
    "Prediction",
    "Recommendation",
    "RecommendationPriority",
    "Region",
    "RegionLevel",
    "RiskAssessment",
    "RiskCategory",
    "RiskLevel",
    "SatelliteFrame",
    "ScenarioParameter",
    "SimulationScenario",
    "WeatherObservation",
]
