"""Dataset registry: loads and exposes ``config/dataset_registry.yaml``.

The registry is the single source of truth for which data sources exist,
their connector class paths, and their default parameters, per SAD Section
20 ("More datasets" extensibility row).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from config.paths import DATASET_REGISTRY_PATH
from utils.exceptions import ConfigurationError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DatasetDescriptor:
    """Typed description of a single registered dataset source.

    Attributes:
        name: Canonical short identifier (matches ``DataSourceName``).
        display_name: Human-readable name for UI display.
        connector_class: Dotted import path to the connector implementing
            :class:`data.ingestion.base.BaseDatasetConnector`.
        variables: Climate variables this source can supply.
        temporal_resolution: e.g. ``"hourly"``, ``"daily"``, ``"16-day"``.
        spatial_resolution_deg: Native spatial resolution in degrees, if gridded.
        live_api_available: Whether a public API is currently reachable; sources
            such as INSAT/Oceansat/IMD may have ``False`` while still being
            architecturally registered.
        default_params: Extra connector-specific default parameters.
    """

    name: str
    display_name: str
    connector_class: str
    variables: tuple[str, ...]
    temporal_resolution: str
    spatial_resolution_deg: float | None
    live_api_available: bool
    default_params: dict[str, object] = field(default_factory=dict)


class DatasetRegistry:
    """In-memory, queryable registry of all dataset sources.

    Args:
        registry_path: Path to the YAML registry file.
    """

    def __init__(self, registry_path: Path = DATASET_REGISTRY_PATH) -> None:
        self._registry_path = registry_path
        self._descriptors: dict[str, DatasetDescriptor] = {}
        self._load()

    def _load(self) -> None:
        if not self._registry_path.exists():
            raise ConfigurationError(
                "Dataset registry file not found",
                details={"path": str(self._registry_path)},
            )
        try:
            with self._registry_path.open("r", encoding="utf-8") as handle:
                raw = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            raise ConfigurationError(
                "Failed to parse dataset registry YAML", details={"error": str(exc)}
            ) from exc

        datasets = raw.get("datasets", [])
        for entry in datasets:
            try:
                descriptor = DatasetDescriptor(
                    name=entry["name"],
                    display_name=entry["display_name"],
                    connector_class=entry["connector_class"],
                    variables=tuple(entry.get("variables", [])),
                    temporal_resolution=entry.get("temporal_resolution", "unknown"),
                    spatial_resolution_deg=entry.get("spatial_resolution_deg"),
                    live_api_available=bool(entry.get("live_api_available", False)),
                    default_params=entry.get("default_params", {}) or {},
                )
            except KeyError as exc:
                raise ConfigurationError(
                    "Dataset registry entry missing required field",
                    details={"entry": entry, "missing_key": str(exc)},
                ) from exc
            self._descriptors[descriptor.name] = descriptor

        logger.info("Loaded %d dataset descriptors from registry", len(self._descriptors))

    def get(self, name: str) -> DatasetDescriptor:
        """Retrieve a dataset descriptor by name.

        Args:
            name: Dataset identifier (e.g. ``"era5"``).

        Returns:
            The matching :class:`DatasetDescriptor`.

        Raises:
            ConfigurationError: If no dataset with that name is registered.
        """
        try:
            return self._descriptors[name]
        except KeyError as exc:
            raise ConfigurationError("Unknown dataset in registry", details={"name": name}) from exc

    def list_all(self) -> tuple[DatasetDescriptor, ...]:
        """Return every registered dataset descriptor.

        Returns:
            A tuple of all :class:`DatasetDescriptor` entries.
        """
        return tuple(self._descriptors.values())

    def list_available(self) -> tuple[DatasetDescriptor, ...]:
        """Return only descriptors whose live API is currently available.

        Returns:
            A tuple of :class:`DatasetDescriptor` entries with
            ``live_api_available=True``.
        """
        return tuple(d for d in self._descriptors.values() if d.live_api_available)
