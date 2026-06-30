"""Generic, dependency-free validation helpers shared across layers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime


def require_not_none(value: object | None, field_name: str) -> object:
    """Raise ``ValueError`` if ``value`` is ``None``.

    Args:
        value: The value to check.
        field_name: Name of the field, used in the error message.

    Returns:
        The original value, for fluent use.

    Raises:
        ValueError: If ``value`` is ``None``.
    """
    if value is None:
        raise ValueError(f"'{field_name}' must not be None")
    return value


def require_in_range(value: float, *, minimum: float, maximum: float, field_name: str) -> float:
    """Validate that a numeric value falls within an inclusive range.

    Args:
        value: The numeric value to validate.
        minimum: Inclusive lower bound.
        maximum: Inclusive upper bound.
        field_name: Name of the field, used in the error message.

    Returns:
        The original value.

    Raises:
        ValueError: If ``value`` is outside ``[minimum, maximum]``.
    """
    if not minimum <= value <= maximum:
        raise ValueError(f"'{field_name}' must be within [{minimum}, {maximum}], got {value}")
    return value


def require_non_empty(values: Iterable[object], field_name: str) -> list[object]:
    """Validate that an iterable contains at least one element.

    Args:
        values: The iterable to validate.
        field_name: Name of the field, used in the error message.

    Returns:
        The materialized list of values.

    Raises:
        ValueError: If the iterable is empty.
    """
    materialized = list(values)
    if not materialized:
        raise ValueError(f"'{field_name}' must not be empty")
    return materialized


def require_valid_latitude(latitude: float) -> float:
    """Validate a latitude value lies within [-90, 90].

    Args:
        latitude: Latitude in decimal degrees.

    Returns:
        The validated latitude.

    Raises:
        ValueError: If outside the valid range.
    """
    return require_in_range(latitude, minimum=-90.0, maximum=90.0, field_name="latitude")


def require_valid_longitude(longitude: float) -> float:
    """Validate a longitude value lies within [-180, 180].

    Args:
        longitude: Longitude in decimal degrees.

    Returns:
        The validated longitude.

    Raises:
        ValueError: If outside the valid range.
    """
    return require_in_range(longitude, minimum=-180.0, maximum=180.0, field_name="longitude")


def require_chronological(start: datetime, end: datetime) -> None:
    """Validate that ``start`` precedes or equals ``end``.

    Args:
        start: Start timestamp.
        end: End timestamp.

    Raises:
        ValueError: If ``start`` is after ``end``.
    """
    if start > end:
        raise ValueError(f"start ({start.isoformat()}) must not be after end ({end.isoformat()})")
