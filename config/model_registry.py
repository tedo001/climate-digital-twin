"""Model registry: loads and exposes ``config/model_registry.yaml``.

Per SAD Section 20 ("More AI models"), adding a model is a registry entry
plus an architecture file — ``ModelManager`` resolves everything else from
this registry, with weights lazily loaded on first inference (Section 4 step 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from config.paths import MODEL_REGISTRY_PATH
from utils.exceptions import ConfigurationError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    """Typed description of a single registered PyTorch model.

    Attributes:
        name: Canonical model identifier (e.g. ``"monsoon_lstm"``).
        display_name: Human-readable name for UI display.
        architecture_class: Dotted import path to the ``nn.Module`` subclass.
        checkpoint_filename: Filename within ``ai/models/checkpoints/``.
        target_variable: The climate variable this model predicts.
        supported_horizons_days: Forecast horizons (days) this model supports.
        input_features: Ordered list of feature names expected by the model.
        version: Semantic version string for the trained checkpoint.
        hyperparameters: Architecture hyperparameters needed to instantiate the module.
    """

    name: str
    display_name: str
    architecture_class: str
    checkpoint_filename: str
    target_variable: str
    supported_horizons_days: tuple[int, ...]
    input_features: tuple[str, ...]
    version: str
    hyperparameters: dict[str, object] = field(default_factory=dict)


class ModelRegistry:
    """In-memory, queryable registry of all PyTorch model descriptors.

    Args:
        registry_path: Path to the YAML registry file.
    """

    def __init__(self, registry_path: Path = MODEL_REGISTRY_PATH) -> None:
        self._registry_path = registry_path
        self._descriptors: dict[str, ModelDescriptor] = {}
        self._load()

    def _load(self) -> None:
        if not self._registry_path.exists():
            raise ConfigurationError(
                "Model registry file not found", details={"path": str(self._registry_path)}
            )
        try:
            with self._registry_path.open("r", encoding="utf-8") as handle:
                raw = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            raise ConfigurationError(
                "Failed to parse model registry YAML", details={"error": str(exc)}
            ) from exc

        for entry in raw.get("models", []):
            try:
                descriptor = ModelDescriptor(
                    name=entry["name"],
                    display_name=entry["display_name"],
                    architecture_class=entry["architecture_class"],
                    checkpoint_filename=entry["checkpoint_filename"],
                    target_variable=entry["target_variable"],
                    supported_horizons_days=tuple(entry.get("supported_horizons_days", [7])),
                    input_features=tuple(entry.get("input_features", [])),
                    version=entry.get("version", "0.1.0"),
                    hyperparameters=entry.get("hyperparameters", {}) or {},
                )
            except KeyError as exc:
                raise ConfigurationError(
                    "Model registry entry missing required field",
                    details={"entry": entry, "missing_key": str(exc)},
                ) from exc
            self._descriptors[descriptor.name] = descriptor

        logger.info("Loaded %d model descriptors from registry", len(self._descriptors))

    def get(self, name: str) -> ModelDescriptor:
        """Retrieve a model descriptor by name.

        Args:
            name: Model identifier (e.g. ``"monsoon_lstm"``).

        Returns:
            The matching :class:`ModelDescriptor`.

        Raises:
            ConfigurationError: If no model with that name is registered.
        """
        try:
            return self._descriptors[name]
        except KeyError as exc:
            raise ConfigurationError("Unknown model in registry", details={"name": name}) from exc

    def list_all(self) -> tuple[ModelDescriptor, ...]:
        """Return every registered model descriptor.

        Returns:
            A tuple of all :class:`ModelDescriptor` entries.
        """
        return tuple(self._descriptors.values())

    def find_for_variable(self, target_variable: str) -> tuple[ModelDescriptor, ...]:
        """Find all models capable of predicting a given climate variable.

        Args:
            target_variable: Climate variable name (e.g. ``"precipitation"``).

        Returns:
            A tuple of matching :class:`ModelDescriptor` entries.
        """
        return tuple(d for d in self._descriptors.values() if d.target_variable == target_variable)
