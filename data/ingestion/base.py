"""Abstract base class for every data-ingestion connector.

:class:`BaseDatasetConnector` factors out everything common to all connectors —
registry lookup, automatic ``data/raw/<dataset>/`` and ``data/metadata/<dataset>/``
directory creation, checksum-based validation, metadata persistence, cache
integration, and logging — so a concrete connector only has to implement the
dataset-specific :meth:`download` logic.

The public surface every connector exposes (per the ingestion contract) is:

* :meth:`download`
* :meth:`validate`
* :meth:`metadata`
* :meth:`available_variables`
* :meth:`available_dates`
"""

from __future__ import annotations

import abc
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from config.dataset_registry import DatasetDescriptor, DatasetRegistry
from config.paths import DATA_METADATA_DIR, DATA_RAW_DIR
from config.settings import Settings, get_settings
from core.models.metadata import DatasetMetadata
from data.ingestion.download_manager import DownloadManager, DownloadResult, compute_checksum
from storage.cache import CacheManager, get_cache_manager
from utils.exceptions import DatasetNotFoundError, IntegrityCheckError, UnsupportedVariableError
from utils.logger import get_logger

logger = get_logger(__name__)

_METADATA_SUFFIX = ".metadata.json"


class BaseDatasetConnector(abc.ABC):
    """Common behaviour shared by all dataset connectors.

    Subclasses must set the class attribute :attr:`DATASET_NAME` (matching a
    ``name`` in ``config/dataset_registry.yaml``) and implement :meth:`download`.

    Args:
        descriptor: Pre-resolved registry descriptor; looked up from ``registry``
            by :attr:`DATASET_NAME` when omitted.
        settings: Injected settings singleton.
        cache_manager: Injected cache facade (memory/disk/raster).
        download_manager: Injected HTTP download orchestrator.
        registry: Injected dataset registry (used only to resolve ``descriptor``).
        raw_root: Root directory under which ``<dataset>/`` payloads are written.
        metadata_root: Root directory under which ``<dataset>/`` metadata is written.
    """

    #: Canonical dataset identifier; overridden by every concrete connector.
    DATASET_NAME: str = ""

    def __init__(
        self,
        descriptor: DatasetDescriptor | None = None,
        *,
        settings: Settings | None = None,
        cache_manager: CacheManager | None = None,
        download_manager: DownloadManager | None = None,
        registry: DatasetRegistry | None = None,
        raw_root: Path = DATA_RAW_DIR,
        metadata_root: Path = DATA_METADATA_DIR,
    ) -> None:
        if not self.DATASET_NAME:
            raise DatasetNotFoundError(
                "Connector subclass did not define DATASET_NAME",
                details={"connector": type(self).__name__},
            )
        self._settings = settings or get_settings()
        self._cache = cache_manager or get_cache_manager()
        self._downloader = download_manager or DownloadManager(settings=self._settings)
        self._descriptor = descriptor or (registry or DatasetRegistry()).get(self.DATASET_NAME)

        self._raw_dir = Path(raw_root) / self.DATASET_NAME
        self._metadata_dir = Path(metadata_root) / self.DATASET_NAME
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_dir.mkdir(parents=True, exist_ok=True)

        self._logger = get_logger(f"data.ingestion.{self.DATASET_NAME}")

    # ------------------------------------------------------------------ #
    # Read-only properties
    # ------------------------------------------------------------------ #
    @property
    def name(self) -> str:
        """Canonical dataset identifier (e.g. ``"era5"``)."""
        return self._descriptor.name

    @property
    def display_name(self) -> str:
        """Human-readable dataset name for UI/log display."""
        return self._descriptor.display_name

    @property
    def descriptor(self) -> DatasetDescriptor:
        """The registry descriptor backing this connector."""
        return self._descriptor

    @property
    def raw_dir(self) -> Path:
        """Directory where this dataset's raw files are stored."""
        return self._raw_dir

    @property
    def metadata_dir(self) -> Path:
        """Directory where this dataset's sidecar metadata is stored."""
        return self._metadata_dir

    # ------------------------------------------------------------------ #
    # Public contract — the five methods every connector supports
    # ------------------------------------------------------------------ #
    @abc.abstractmethod
    def download(
        self,
        *,
        variables: list[str] | None = None,
        dates: list[str] | None = None,
        **kwargs: Any,
    ) -> DownloadResult:
        """Fetch data from the source and store it under ``data/raw/<dataset>/``.

        Args:
            variables: Variables to fetch; defaults to :meth:`available_variables`.
            dates: ISO dates to fetch; defaults to :meth:`available_dates`.
            **kwargs: Connector-specific options (area, product, etc.).

        Returns:
            A :class:`DownloadResult` for the stored file.
        """
        raise NotImplementedError

    def available_variables(self) -> tuple[str, ...]:
        """Return the climate variables this dataset can supply.

        Returns:
            The tuple of variable identifiers declared in the registry.
        """
        return self._descriptor.variables

    def available_dates(self) -> tuple[str, ...]:
        """Return recently available ISO dates for this dataset.

        The default implementation derives a rolling window ending yesterday,
        cached on disk so repeated calls avoid recomputation. Connectors with a
        catalogue endpoint should override this to query the source directly.

        Returns:
            A tuple of ``YYYY-MM-DD`` date strings, oldest first.
        """
        cache_key = f"ingestion:{self.name}:available_dates"
        cached = self._cache.disk.get(cache_key)
        if cached is not None:
            return tuple(cached)
        dates = self._default_date_window()
        self._cache.disk.set(cache_key, list(dates))
        return dates

    def metadata(self) -> DatasetMetadata:
        """Return provenance metadata describing the dataset source.

        Returns:
            A :class:`DatasetMetadata` populated from the registry descriptor and
            the current availability window.
        """
        window = self.available_dates()
        start = _parse_iso_date(window[0]) if window else datetime.now(tz=UTC)
        end = _parse_iso_date(window[-1]) if window else datetime.now(tz=UTC)
        return DatasetMetadata(
            source=self.name,
            retrieved_at=datetime.now(tz=UTC),
            valid_time_start=start,
            valid_time_end=end,
            version=str(self._descriptor.default_params.get("product", self.name)),
            license=str(self._descriptor.default_params.get("license", "see-source-terms")),
            extra={
                "display_name": self.display_name,
                "temporal_resolution": self._descriptor.temporal_resolution,
                "live_api_available": str(self._descriptor.live_api_available),
            },
        )

    def validate(self, file_path: Path, expected_checksum: str | None = None) -> bool:
        """Validate a previously downloaded file's presence and integrity.

        Args:
            file_path: Path to the file to validate.
            expected_checksum: Explicit expected SHA-256; when omitted, the value
                is read from the sidecar metadata written at download time.

        Returns:
            ``True`` if the file exists, is non-empty, and (when a checksum is
            available) matches it.

        Raises:
            IntegrityCheckError: If a known checksum does not match the file.
        """
        file_path = Path(file_path)
        if not file_path.exists() or file_path.stat().st_size == 0:
            self._logger.warning("Validation failed: missing/empty file %s", file_path)
            return False

        reference = expected_checksum
        if reference is None:
            sidecar = self._read_metadata_sidecar(file_path)
            reference = sidecar.get("checksum") if sidecar else None

        if reference is None:
            return True

        actual = compute_checksum(file_path)
        if actual != reference:
            raise IntegrityCheckError(
                "Downloaded file failed checksum validation",
                details={"file": str(file_path), "expected": reference, "actual": actual},
            )
        return True

    # ------------------------------------------------------------------ #
    # Helpers for concrete connectors
    # ------------------------------------------------------------------ #
    def _resolve_variables(self, variables: list[str] | None) -> tuple[str, ...]:
        """Validate requested variables against the registry, or default to all.

        Args:
            variables: Requested variables, or ``None`` for all available.

        Returns:
            A tuple of validated variable identifiers.

        Raises:
            UnsupportedVariableError: If any requested variable is not offered.
        """
        if not variables:
            return self.available_variables()
        unsupported = [v for v in variables if v not in self.available_variables()]
        if unsupported:
            raise UnsupportedVariableError(
                "Requested variables not offered by dataset",
                details={"dataset": self.name, "unsupported": unsupported},
            )
        return tuple(variables)

    def _raw_path(self, filename: str) -> Path:
        """Return the absolute path for a raw file within this dataset's dir."""
        return self._raw_dir / filename

    def _metadata_path(self, file_path: Path) -> Path:
        """Return the sidecar metadata path for a given raw file."""
        return self._metadata_dir / f"{Path(file_path).name}{_METADATA_SUFFIX}"

    def _write_metadata_sidecar(
        self,
        file_path: Path,
        result: DownloadResult,
        *,
        variables: tuple[str, ...],
        valid_time_start: datetime,
        valid_time_end: datetime,
        version: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> Path:
        """Persist provenance metadata for a downloaded file, separate from it.

        Args:
            file_path: The downloaded raw file.
            result: The download result carrying the checksum and byte count.
            variables: Variables contained in the file.
            valid_time_start: Earliest timestamp the data covers.
            valid_time_end: Latest timestamp the data covers.
            version: Optional explicit dataset/product version.
            extra: Additional provenance annotations.

        Returns:
            The path to the written metadata JSON file.
        """
        metadata = DatasetMetadata(
            source=self.name,
            retrieved_at=datetime.now(tz=UTC),
            valid_time_start=valid_time_start,
            valid_time_end=valid_time_end,
            version=version or str(self._descriptor.default_params.get("product", self.name)),
            checksum=result.checksum,
            license=str(self._descriptor.default_params.get("license", "see-source-terms")),
            extra={
                "file": str(file_path),
                "num_bytes": str(result.num_bytes),
                "variables": ",".join(variables),
                **(extra or {}),
            },
        )
        payload = _metadata_to_dict(metadata)
        meta_path = self._metadata_path(file_path)
        meta_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self._logger.info("Wrote metadata sidecar %s", meta_path)
        return meta_path

    def _finalize_download(
        self,
        result: DownloadResult,
        *,
        variables: tuple[str, ...],
        dates: list[str] | tuple[str, ...],
        version: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> DownloadResult:
        """Write the metadata sidecar for a completed download and log it.

        Derives the coverage window from ``dates`` and records the checksum,
        keeping provenance metadata stored separately from the payload.

        Args:
            result: The completed :class:`DownloadResult`.
            variables: Variables contained in the downloaded file.
            dates: The ISO dates the download covers.
            version: Optional explicit version override.
            extra: Additional provenance annotations.

        Returns:
            The same ``result``, with ``metadata_path`` recorded in ``extra``.
        """
        ordered = sorted(dates) if dates else list(self.available_dates())
        start = _parse_iso_date(ordered[0]) if ordered else datetime.now(tz=UTC)
        end = _parse_iso_date(ordered[-1]) if ordered else datetime.now(tz=UTC)
        meta_path = self._write_metadata_sidecar(
            result.path,
            result,
            variables=variables,
            valid_time_start=start,
            valid_time_end=end,
            version=version,
            extra=extra,
        )
        result.extra["metadata_path"] = str(meta_path)
        return result

    def _read_metadata_sidecar(self, file_path: Path) -> dict[str, Any] | None:
        """Read a downloaded file's sidecar metadata, if present."""
        meta_path = self._metadata_path(file_path)
        if not meta_path.exists():
            return None
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:  # pragma: no cover - defensive
            self._logger.warning("Unreadable metadata sidecar %s: %s", meta_path, exc)
            return None

    def _default_date_window(self, num_days: int = 7) -> tuple[str, ...]:
        """Return the last ``num_days`` complete days as ISO date strings."""
        today = date.today()
        window = [today - timedelta(days=offset) for offset in range(num_days, 0, -1)]
        return tuple(d.isoformat() for d in window)


# Public alias matching the task's naming ("BaseDataConnector"); both names
# refer to the same abstract base so either import path resolves.
BaseDataConnector = BaseDatasetConnector


def _parse_iso_date(value: str) -> datetime:
    """Parse a ``YYYY-MM-DD`` string into a timezone-aware UTC datetime."""
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _metadata_to_dict(metadata: DatasetMetadata) -> dict[str, Any]:
    """Serialize :class:`DatasetMetadata` to a JSON-safe dictionary."""
    return {
        "source": metadata.source,
        "retrieved_at": metadata.retrieved_at.isoformat(),
        "valid_time_start": metadata.valid_time_start.isoformat(),
        "valid_time_end": metadata.valid_time_end.isoformat(),
        "version": metadata.version,
        "checksum": metadata.checksum,
        "license": metadata.license,
        "extra": metadata.extra,
    }
