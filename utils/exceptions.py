"""Centralized exception hierarchy for the Climate Digital Twin.

Every layer raises subclasses of :class:`ClimateTwinError` so that
Application-layer controllers can catch a single family of exceptions and
translate them into user-facing messages without leaking stack traces into
the Streamlit UI (see SAD Section 16).
"""

from __future__ import annotations


class ClimateTwinError(Exception):
    """Base exception for every error raised within the Climate Digital Twin.

    Args:
        message: Human-readable description of the failure.
        details: Optional structured context (e.g. dataset name, file path)
            useful for logging but not necessarily shown to end users.
    """

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, object] = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | details={self.details}"
        return self.message


# --------------------------------------------------------------------------- #
# Data Ingestion Layer
# --------------------------------------------------------------------------- #
class DataIngestionError(ClimateTwinError):
    """Raised when a dataset cannot be downloaded, read, or parsed."""


class DatasetNotFoundError(DataIngestionError):
    """Raised when a requested dataset is missing from the registry or disk."""


class SchemaValidationError(DataIngestionError):
    """Raised when ingested data fails structural or semantic validation."""


class IntegrityCheckError(DataIngestionError):
    """Raised when a downloaded file fails a checksum / integrity check."""


class ConnectorNotImplementedError(DataIngestionError):
    """Raised when a data source connector's live API path is not yet available.

    Used by connectors whose architecture is ready (per SAD scope) but whose
    upstream public API access is currently limited or unavailable (e.g.
    INSAT, Oceansat, IMD), so the failure is explicit rather than silent.
    """


class DownloadError(DataIngestionError):
    """Raised when a network download fails after all retries are exhausted."""


class MissingCredentialsError(DataIngestionError):
    """Raised when a connector needs an API key/token that is not configured.

    Credentials are always read from the environment via ``config.settings``;
    this is raised (rather than silently proceeding) when a required key is
    absent, so misconfiguration surfaces immediately and no secret is inlined.
    """


class UnsupportedVariableError(DataIngestionError):
    """Raised when a requested variable is not offered by the target dataset."""


# --------------------------------------------------------------------------- #
# Data Processing Layer
# --------------------------------------------------------------------------- #
class DataProcessingError(ClimateTwinError):
    """Base exception for the climate-processing pipeline (SAD Section 6)."""


class UnsupportedFormatError(DataProcessingError):
    """Raised when a file extension has no registered reader (not GeoTIFF/NetCDF)."""


class RasterReadError(DataProcessingError):
    """Raised when a GeoTIFF/NetCDF payload cannot be read or decoded."""


class RasterProcessingError(DataProcessingError):
    """Raised when a raster transform (reproject/clip/resample) cannot complete."""


class TemporalAlignmentError(DataProcessingError):
    """Raised when time series cannot be aligned onto a common temporal grid."""


class NormalizationError(DataProcessingError):
    """Raised when a normalization/unit-conversion step receives invalid input."""


class FeatureEngineeringError(DataProcessingError):
    """Raised when a derived feature cannot be computed from processed inputs."""


class PipelineError(DataProcessingError):
    """Raised when a processing pipeline step fails, wrapping the root cause."""


class StateConstructionError(DataProcessingError):
    """Raised when a standardized :class:`ClimateState` cannot be assembled."""


# --------------------------------------------------------------------------- #
# Climate Intelligence Layer
# --------------------------------------------------------------------------- #
class AssimilationError(ClimateTwinError):
    """Raised when the assimilation engine cannot fuse observations into state."""


class StateValidationError(AssimilationError):
    """Raised when a constructed ClimateState fails validation checks."""


class FusionError(AssimilationError):
    """Raised when multi-source observation fusion cannot produce a value."""


class BiasCorrectionError(AssimilationError):
    """Raised when a bias-correction calibration is invalid or cannot apply."""


class StateNotFoundError(ClimateTwinError):
    """Raised when no persisted ClimateState version can be located."""


class StatePersistenceError(ClimateTwinError):
    """Raised when a ClimateState snapshot cannot be serialized or stored."""


# --------------------------------------------------------------------------- #
# AI Layer
# --------------------------------------------------------------------------- #
class ModelError(ClimateTwinError):
    """Base exception for AI model lifecycle and inference failures."""


class ModelNotLoadedError(ModelError):
    """Raised when inference is requested before a model checkpoint is loaded."""


class InferenceError(ModelError):
    """Raised when a forward pass or post-processing step fails."""


# --------------------------------------------------------------------------- #
# Simulation Layer
# --------------------------------------------------------------------------- #
class SimulationError(ClimateTwinError):
    """Raised when a what-if scenario cannot be executed."""


class InvalidScenarioParameterError(SimulationError):
    """Raised when scenario parameters fail validation."""


# --------------------------------------------------------------------------- #
# Visualization Layer
# --------------------------------------------------------------------------- #
class VisualizationError(ClimateTwinError):
    """Raised when a figure/map object cannot be constructed from domain data."""


# --------------------------------------------------------------------------- #
# Storage / Configuration Layer
# --------------------------------------------------------------------------- #
class StorageError(ClimateTwinError):
    """Raised for database or file-cache I/O failures."""


class ConfigurationError(ClimateTwinError):
    """Raised when application configuration is missing or invalid."""


class CacheError(StorageError):
    """Raised when a cache read/write operation fails unexpectedly."""
