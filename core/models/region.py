"""Region domain model.

Represents an India administrative unit (state/district) or a custom
bounding box, used throughout the system as the canonical spatial selector.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from utils.validators import require_valid_latitude, require_valid_longitude


@unique
class RegionLevel(str, Enum):
    """Granularity of a :class:`Region`."""

    COUNTRY = "country"
    STATE = "state"
    DISTRICT = "district"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned lat/lon bounding box.

    Attributes:
        min_lat: Minimum latitude (south edge), decimal degrees.
        min_lon: Minimum longitude (west edge), decimal degrees.
        max_lat: Maximum latitude (north edge), decimal degrees.
        max_lon: Maximum longitude (east edge), decimal degrees.
    """

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def __post_init__(self) -> None:
        require_valid_latitude(self.min_lat)
        require_valid_latitude(self.max_lat)
        require_valid_longitude(self.min_lon)
        require_valid_longitude(self.max_lon)
        if self.min_lat > self.max_lat:
            raise ValueError("min_lat must not exceed max_lat")
        if self.min_lon > self.max_lon:
            raise ValueError("min_lon must not exceed max_lon")

    @property
    def center(self) -> tuple[float, float]:
        """Centroid of the bounding box as ``(lat, lon)``."""
        return ((self.min_lat + self.max_lat) / 2.0, (self.min_lon + self.max_lon) / 2.0)


@dataclass(frozen=True, slots=True)
class Region:
    """An India administrative region or custom area of interest.

    Attributes:
        region_id: Stable unique identifier (e.g. ISO/LGD code or slug).
        name: Human-readable region name (e.g. ``"Tamil Nadu"``).
        level: Administrative granularity.
        bounding_box: Approximate bounding box for the region.
        parent_region_id: Identifier of the containing region, if any
            (e.g. a district's parent state).
    """

    region_id: str
    name: str
    level: RegionLevel
    bounding_box: BoundingBox
    parent_region_id: str | None = None

    def __post_init__(self) -> None:
        if not self.region_id:
            raise ValueError("region_id must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")
