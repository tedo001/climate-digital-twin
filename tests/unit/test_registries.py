"""Unit tests for config.dataset_registry and config.model_registry."""

from __future__ import annotations

import pytest

from config.dataset_registry import DatasetRegistry
from config.model_registry import ModelRegistry
from utils.exceptions import ConfigurationError


def test_dataset_registry_loads_all_nine_sources() -> None:
    registry = DatasetRegistry()
    all_datasets = registry.list_all()
    names = {d.name for d in all_datasets}
    expected = {
        "era5",
        "nasa_power",
        "sentinel",
        "modis",
        "gpm",
        "smap",
        "insat",
        "oceansat",
        "imd",
    }
    assert expected.issubset(names)


def test_dataset_registry_distinguishes_live_availability() -> None:
    registry = DatasetRegistry()
    available = {d.name for d in registry.list_available()}
    assert "era5" in available
    assert "insat" not in available  # architecture-ready, not live


def test_dataset_registry_unknown_name_raises() -> None:
    registry = DatasetRegistry()
    with pytest.raises(ConfigurationError):
        registry.get("not_a_real_dataset")


def test_model_registry_loads_three_architectures() -> None:
    registry = ModelRegistry()
    names = {m.name for m in registry.list_all()}
    assert names == {"monsoon_lstm", "drought_cnn", "temp_transformer"}


def test_model_registry_find_for_variable() -> None:
    registry = ModelRegistry()
    matches = registry.find_for_variable("precipitation")
    assert len(matches) == 1
    assert matches[0].name == "monsoon_lstm"


def test_model_registry_unknown_name_raises() -> None:
    registry = ModelRegistry()
    with pytest.raises(ConfigurationError):
        registry.get("not_a_real_model")
