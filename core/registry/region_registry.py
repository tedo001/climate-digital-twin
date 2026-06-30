"""India administrative region registry.

Provides a static, in-memory registry of India's states and union
territories as :class:`core.models.region.Region` objects, used as the
default spatial selector throughout the application. Bounding boxes are
intentionally approximate (sufficient for map framing and grid-cell
bucketing); precise polygon boundaries belong in a GeoPandas shapefile layer
that can be swapped in later without changing this module's interface.
"""

from __future__ import annotations

from core.models.region import BoundingBox, Region, RegionLevel
from utils.decorators import memoize
from utils.exceptions import ConfigurationError

_INDIA_REGION = Region(
    region_id="IN",
    name="India",
    level=RegionLevel.COUNTRY,
    bounding_box=BoundingBox(min_lat=6.5, min_lon=68.0, max_lat=37.6, max_lon=97.5),
)

_STATE_BOUNDING_BOXES: dict[str, tuple[str, float, float, float, float]] = {
    "IN-AP": ("Andhra Pradesh", 12.6, 76.7, 19.9, 84.8),
    "IN-AR": ("Arunachal Pradesh", 26.6, 91.6, 29.5, 97.4),
    "IN-AS": ("Assam", 24.1, 89.7, 28.2, 96.0),
    "IN-BR": ("Bihar", 24.3, 83.3, 27.5, 88.1),
    "IN-CT": ("Chhattisgarh", 17.8, 80.2, 24.1, 84.4),
    "IN-GA": ("Goa", 14.9, 73.7, 15.8, 74.3),
    "IN-GJ": ("Gujarat", 20.1, 68.2, 24.7, 74.5),
    "IN-HR": ("Haryana", 27.7, 74.5, 30.9, 77.6),
    "IN-HP": ("Himachal Pradesh", 30.4, 75.6, 33.2, 79.0),
    "IN-JH": ("Jharkhand", 21.9, 83.3, 25.4, 87.6),
    "IN-KA": ("Karnataka", 11.6, 74.1, 18.5, 78.6),
    "IN-KL": ("Kerala", 8.2, 74.9, 12.8, 77.4),
    "IN-MP": ("Madhya Pradesh", 21.1, 74.0, 26.9, 82.8),
    "IN-MH": ("Maharashtra", 15.6, 72.6, 22.0, 80.9),
    "IN-MN": ("Manipur", 23.8, 93.0, 25.7, 94.8),
    "IN-ML": ("Meghalaya", 25.0, 89.8, 26.1, 92.8),
    "IN-MZ": ("Mizoram", 21.9, 92.2, 24.5, 93.5),
    "IN-NL": ("Nagaland", 25.2, 93.3, 27.0, 95.8),
    "IN-OR": ("Odisha", 17.8, 81.4, 22.6, 87.5),
    "IN-PB": ("Punjab", 29.5, 73.9, 32.5, 76.9),
    "IN-RJ": ("Rajasthan", 23.0, 69.5, 30.2, 78.3),
    "IN-SK": ("Sikkim", 27.0, 88.0, 28.1, 88.9),
    "IN-TN": ("Tamil Nadu", 8.1, 76.2, 13.6, 80.3),
    "IN-TG": ("Telangana", 15.8, 77.2, 19.9, 81.3),
    "IN-TR": ("Tripura", 22.9, 91.1, 24.5, 92.3),
    "IN-UP": ("Uttar Pradesh", 23.9, 77.0, 30.4, 84.6),
    "IN-UT": ("Uttarakhand", 28.7, 77.6, 31.5, 81.0),
    "IN-WB": ("West Bengal", 21.5, 85.8, 27.2, 89.9),
    "IN-AN": ("Andaman and Nicobar Islands", 6.5, 92.2, 13.7, 93.9),
    "IN-CH": ("Chandigarh", 30.6, 76.7, 30.8, 76.9),
    "IN-DH": ("Dadra and Nagar Haveli and Daman and Diu", 20.0, 72.7, 20.8, 73.2),
    "IN-DL": ("Delhi", 28.4, 76.8, 28.9, 77.4),
    "IN-JK": ("Jammu and Kashmir", 32.3, 73.0, 36.5, 80.3),
    "IN-LA": ("Ladakh", 32.0, 75.8, 36.0, 80.3),
    "IN-LD": ("Lakshadweep", 8.0, 71.7, 12.3, 74.0),
    "IN-PY": ("Puducherry", 10.9, 79.7, 12.0, 79.9),
}


def _build_registry() -> dict[str, Region]:
    registry: dict[str, Region] = {_INDIA_REGION.region_id: _INDIA_REGION}
    for region_id, (name, min_lat, min_lon, max_lat, max_lon) in _STATE_BOUNDING_BOXES.items():
        registry[region_id] = Region(
            region_id=region_id,
            name=name,
            level=RegionLevel.STATE,
            bounding_box=BoundingBox(
                min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon
            ),
            parent_region_id=_INDIA_REGION.region_id,
        )
    return registry


class RegionRegistry:
    """Queryable registry of India's country/state-level regions.

    This class is intentionally simple (no I/O) so it is trivially testable
    and importable from any layer without a database connection.
    """

    def __init__(self) -> None:
        self._regions: dict[str, Region] = _build_registry()

    def get(self, region_id: str) -> Region:
        """Retrieve a region by its identifier.

        Args:
            region_id: Region identifier (e.g. ``"IN-TN"``).

        Returns:
            The matching :class:`Region`.

        Raises:
            ConfigurationError: If no region with that identifier exists.
        """
        try:
            return self._regions[region_id]
        except KeyError as exc:
            raise ConfigurationError(
                "Unknown region_id in registry", details={"region_id": region_id}
            ) from exc

    def list_states(self) -> tuple[Region, ...]:
        """Return all state/UT-level regions.

        Returns:
            A tuple of :class:`Region` objects with ``level == RegionLevel.STATE``.
        """
        return tuple(r for r in self._regions.values() if r.level == RegionLevel.STATE)

    def country(self) -> Region:
        """Return the top-level India region.

        Returns:
            The :class:`Region` representing all of India.
        """
        return _INDIA_REGION

    def all(self) -> tuple[Region, ...]:
        """Return every registered region.

        Returns:
            A tuple of all :class:`Region` objects.
        """
        return tuple(self._regions.values())


@memoize
def get_region_registry() -> RegionRegistry:
    """Return a process-wide memoized :class:`RegionRegistry` instance.

    Returns:
        A :class:`RegionRegistry` singleton.
    """
    return RegionRegistry()
