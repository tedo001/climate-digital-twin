"""Unit tests for core.registry.region_registry."""

from __future__ import annotations

import pytest

from core.registry.region_registry import RegionRegistry
from utils.exceptions import ConfigurationError


def test_registry_contains_country_and_states() -> None:
    registry = RegionRegistry()
    country = registry.country()
    assert country.region_id == "IN"

    states = registry.list_states()
    assert len(states) >= 28  # 28 states + UTs
    assert any(s.name == "Tamil Nadu" for s in states)


def test_get_known_region() -> None:
    registry = RegionRegistry()
    region = registry.get("IN-KA")
    assert region.name == "Karnataka"
    assert region.parent_region_id == "IN"


def test_get_unknown_region_raises() -> None:
    registry = RegionRegistry()
    with pytest.raises(ConfigurationError):
        registry.get("IN-ZZ")


def test_all_states_have_valid_bounding_boxes() -> None:
    registry = RegionRegistry()
    for region in registry.list_states():
        bbox = region.bounding_box
        assert bbox.min_lat <= bbox.max_lat
        assert bbox.min_lon <= bbox.max_lon
