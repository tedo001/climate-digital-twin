"""Project-wide constants.

Centralizes magic strings/numbers referenced by multiple layers so they have
exactly one definition (SAD Section 19 rule 1: no duplicated logic).
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class ClimateVariableName(str, Enum):
    """Canonical climate variable identifiers used throughout the system."""

    TEMPERATURE_2M = "temperature_2m"
    PRECIPITATION = "precipitation"
    SOIL_MOISTURE = "soil_moisture"
    SEA_SURFACE_TEMPERATURE = "sea_surface_temperature"
    WIND_SPEED_10M = "wind_speed_10m"
    RELATIVE_HUMIDITY = "relative_humidity"
    NDVI = "ndvi"
    SURFACE_PRESSURE = "surface_pressure"
    CLOUD_COVER = "cloud_cover"


@unique
class ClimateVariableUnit(str, Enum):
    """Canonical units paired with :class:`ClimateVariableName`."""

    CELSIUS = "celsius"
    MILLIMETER = "mm"
    VOLUMETRIC_FRACTION = "m3/m3"
    METERS_PER_SECOND = "m/s"
    PERCENT = "percent"
    DIMENSIONLESS = "dimensionless"
    HECTOPASCAL = "hPa"


DEFAULT_VARIABLE_UNITS: dict[ClimateVariableName, ClimateVariableUnit] = {
    ClimateVariableName.TEMPERATURE_2M: ClimateVariableUnit.CELSIUS,
    ClimateVariableName.PRECIPITATION: ClimateVariableUnit.MILLIMETER,
    ClimateVariableName.SOIL_MOISTURE: ClimateVariableUnit.VOLUMETRIC_FRACTION,
    ClimateVariableName.SEA_SURFACE_TEMPERATURE: ClimateVariableUnit.CELSIUS,
    ClimateVariableName.WIND_SPEED_10M: ClimateVariableUnit.METERS_PER_SECOND,
    ClimateVariableName.RELATIVE_HUMIDITY: ClimateVariableUnit.PERCENT,
    ClimateVariableName.NDVI: ClimateVariableUnit.DIMENSIONLESS,
    ClimateVariableName.SURFACE_PRESSURE: ClimateVariableUnit.HECTOPASCAL,
    ClimateVariableName.CLOUD_COVER: ClimateVariableUnit.PERCENT,
}


@unique
class StateType(str, Enum):
    """Lifecycle classification of a ``ClimateState`` snapshot."""

    HISTORICAL = "historical"
    NOWCAST = "nowcast"
    FORECAST = "forecast"
    SIMULATED = "simulated"


@unique
class DataSourceName(str, Enum):
    """Identifiers for every national/global dataset connector in the registry."""

    ERA5 = "era5"
    NASA_POWER = "nasa_power"
    SENTINEL = "sentinel"
    MODIS = "modis"
    GPM = "gpm"
    SMAP = "smap"
    INSAT = "insat"
    OCEANSAT = "oceansat"
    IMD = "imd"


DEFAULT_SPATIAL_RESOLUTION_DEG: float = 0.25
DEFAULT_CACHE_TTL_SECONDS: int = 6 * 60 * 60  # 6 hours
DEFAULT_FORECAST_HORIZON_DAYS: int = 7
MAX_FORECAST_HORIZON_DAYS: int = 30

APP_NAME: str = "AI-Powered Digital Twin of India's Climate"
APP_VERSION: str = "0.2.0"
