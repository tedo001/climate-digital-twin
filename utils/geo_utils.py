"""Lightweight geospatial helper functions with no heavy GIS dependency.

Heavier raster/vector operations (Rasterio, GeoPandas) belong in
``data.preprocessing``; this module holds pure-math helpers usable anywhere
without pulling in GDAL.
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088

# Approximate bounding box of India (mainland + islands), used for sanity
# checks and default map extents.
INDIA_BOUNDS = {
    "min_lat": 6.5,
    "max_lat": 37.6,
    "min_lon": 68.0,
    "max_lon": 97.5,
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the great-circle distance between two points in kilometers.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Distance between the two points in kilometers.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def is_within_india_bounds(lat: float, lon: float) -> bool:
    """Check whether a coordinate falls within India's approximate bounding box.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        ``True`` if the point lies inside :data:`INDIA_BOUNDS`.
    """
    return (
        INDIA_BOUNDS["min_lat"] <= lat <= INDIA_BOUNDS["max_lat"]
        and INDIA_BOUNDS["min_lon"] <= lon <= INDIA_BOUNDS["max_lon"]
    )


def grid_cell_id(lat: float, lon: float, resolution_deg: float = 0.25) -> str:
    """Compute a stable grid-cell identifier for a coordinate at a given resolution.

    Used to key cached raster lookups and to bucket point observations into
    a regular grid for assimilation.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        resolution_deg: Grid cell size in degrees (default matches common
            reanalysis resolutions such as ERA5 0.25°).

    Returns:
        A string identifier of the form ``"lat_<n>_lon_<n>"`` for the cell
        containing the coordinate.
    """
    lat_idx = math.floor(lat / resolution_deg)
    lon_idx = math.floor(lon / resolution_deg)
    return f"lat_{lat_idx}_lon_{lon_idx}"


def bounding_box_center(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> tuple[float, float]:
    """Compute the centroid of a lat/lon bounding box.

    Args:
        min_lat: Minimum latitude.
        min_lon: Minimum longitude.
        max_lat: Maximum latitude.
        max_lon: Maximum longitude.

    Returns:
        A ``(center_lat, center_lon)`` tuple.
    """
    return ((min_lat + max_lat) / 2.0, (min_lon + max_lon) / 2.0)
