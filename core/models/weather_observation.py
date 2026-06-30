"""WeatherObservation domain model.

Represents a single point-in-time, point-in-space measurement (IMD ground
station, NASA POWER grid cell, ERA5 reanalysis cell) in a form the
assimilation engine can fuse regardless of origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.models.metadata import DatasetMetadata
from utils.validators import require_in_range, require_valid_latitude, require_valid_longitude


@dataclass(frozen=True, slots=True)
class WeatherObservation:
    """A single-variable point observation from a station or reanalysis grid cell.

    Attributes:
        variable_name: Canonical climate variable identifier.
        latitude: Observation latitude, decimal degrees.
        longitude: Observation longitude, decimal degrees.
        value: Measured/estimated value.
        unit: Unit string for ``value``.
        observed_at: Timestamp of the observation.
        source: Originating dataset/connector name.
        metadata: Provenance metadata.
        station_id: Ground station identifier, if applicable (IMD).
        uncertainty: Optional reported measurement uncertainty (same unit as value).
    """

    variable_name: str
    latitude: float
    longitude: float
    value: float
    unit: str
    observed_at: datetime
    source: str
    metadata: DatasetMetadata
    station_id: str | None = None
    uncertainty: float | None = None

    def __post_init__(self) -> None:
        require_valid_latitude(self.latitude)
        require_valid_longitude(self.longitude)
        if self.uncertainty is not None:
            require_in_range(
                self.uncertainty, minimum=0.0, maximum=float("inf"), field_name="uncertainty"
            )
