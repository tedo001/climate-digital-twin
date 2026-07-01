"""Unit tests for every data-ingestion connector.

Covers the shared base contract (``available_variables``, ``available_dates``,
``metadata``, ``validate``) plus per-connector ``download`` behaviour: the live
connectors download via an injected fake manager and persist metadata, the
credential-gated ones surface :class:`MissingCredentialsError` when keys are
absent, and the architecture-ready stubs raise
:class:`ConnectorNotImplementedError`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from config.settings import Settings
from core.models.metadata import DatasetMetadata
from data.ingestion.connectors.era5_connector import ERA5Connector
from data.ingestion.connectors.gpm_connector import GPMConnector
from data.ingestion.connectors.imd_connector import IMDConnector
from data.ingestion.connectors.insat_connector import INSATConnector
from data.ingestion.connectors.modis_connector import MODISConnector
from data.ingestion.connectors.nasa_power_connector import NASAPowerConnector
from data.ingestion.connectors.oceansat_connector import OceansatConnector
from data.ingestion.connectors.sentinel_connector import SentinelConnector
from data.ingestion.connectors.smap_connector import SMAPConnector
from data.ingestion.download_manager import DownloadResult
from storage.cache import CacheManager
from storage.cache.disk_cache import DiskCache
from utils.exceptions import (
    ConnectorNotImplementedError,
    IntegrityCheckError,
    MissingCredentialsError,
    UnsupportedVariableError,
)

LIVE_CONNECTORS = [
    ERA5Connector,
    NASAPowerConnector,
    SentinelConnector,
    MODISConnector,
    GPMConnector,
    SMAPConnector,
]
STUB_CONNECTORS = [INSATConnector, OceansatConnector, IMDConnector]
ALL_CONNECTORS = LIVE_CONNECTORS + STUB_CONNECTORS

# Connectors that require credentials, and the settings kwargs that satisfy them.
CREDENTIALED = {
    ERA5Connector: {"cds_api_key": "uid:secret"},
    SentinelConnector: {"sentinel_client_id": "cid", "sentinel_client_secret": "csecret"},
    MODISConnector: {"earthdata_token": "tok"},
    GPMConnector: {"earthdata_token": "tok"},
    SMAPConnector: {"earthdata_token": "tok"},
}


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeSession:
    """Session stub used only for Sentinel's OAuth token exchange."""

    def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse({"access_token": "fake-token"})


class _FakeDownloader:
    """Stands in for :class:`DownloadManager`, writing a small file per call."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.session = _FakeSession()

    def download(self, url: str, dest_path: Path, **kwargs: Any) -> DownloadResult:
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        content = f"payload::{url}".encode()
        dest_path.write_bytes(content)
        self.calls.append({"url": url, "dest": dest_path, "kwargs": kwargs})
        return DownloadResult(
            path=dest_path,
            checksum=hashlib.sha256(content).hexdigest(),
            num_bytes=len(content),
            url=url,
        )


def _make(
    connector_cls: type,
    tmp_path: Path,
    *,
    settings: Settings | None = None,
    downloader: _FakeDownloader | None = None,
) -> Any:
    """Instantiate a connector wired to isolated temp dirs and a temp cache."""
    cache = CacheManager(disk_cache=DiskCache(cache_dir=tmp_path / "cache"))
    return connector_cls(
        settings=settings or Settings(),
        cache_manager=cache,
        download_manager=downloader or _FakeDownloader(),
        raw_root=tmp_path / "raw",
        metadata_root=tmp_path / "metadata",
    )


# --------------------------------------------------------------------------- #
# Shared contract — every connector
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("connector_cls", ALL_CONNECTORS)
def test_available_variables_match_registry(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    assert connector.available_variables() == connector.descriptor.variables
    assert len(connector.available_variables()) > 0


@pytest.mark.parametrize("connector_cls", ALL_CONNECTORS)
def test_available_dates_non_empty_iso(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    dates = connector.available_dates()
    assert dates
    # Each entry must parse as an ISO date.
    for value in dates:
        assert len(value) == 10 and value[4] == "-"


@pytest.mark.parametrize("connector_cls", ALL_CONNECTORS)
def test_metadata_returns_dataset_metadata(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    meta = connector.metadata()
    assert isinstance(meta, DatasetMetadata)
    assert meta.source == connector.name
    assert meta.valid_time_start <= meta.valid_time_end


@pytest.mark.parametrize("connector_cls", ALL_CONNECTORS)
def test_creates_dataset_directories(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    assert connector.raw_dir.is_dir()
    assert connector.metadata_dir.is_dir()
    assert connector.raw_dir.name == connector.name


@pytest.mark.parametrize("connector_cls", ALL_CONNECTORS)
def test_validate_missing_file_returns_false(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    assert connector.validate(tmp_path / "does_not_exist.bin") is False


@pytest.mark.parametrize("connector_cls", ALL_CONNECTORS)
def test_validate_checksum_mismatch_raises(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    f = connector.raw_dir / "sample.bin"
    f.write_bytes(b"real-content")
    with pytest.raises(IntegrityCheckError):
        connector.validate(f, expected_checksum="0" * 64)


# --------------------------------------------------------------------------- #
# Live connectors — successful download + metadata persistence
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("connector_cls", LIVE_CONNECTORS)
def test_live_download_writes_file_and_metadata(connector_cls: type, tmp_path: Path) -> None:
    settings = Settings(**CREDENTIALED.get(connector_cls, {}))
    downloader = _FakeDownloader()
    connector = _make(connector_cls, tmp_path, settings=settings, downloader=downloader)

    result = connector.download()

    # File landed under data/raw/<dataset>/ (here the temp raw_root).
    assert result.path.exists()
    assert result.path.parent == connector.raw_dir
    assert len(downloader.calls) >= 1

    # Metadata was stored separately, under the metadata dir, and is valid JSON.
    meta_path = Path(result.extra["metadata_path"])
    assert meta_path.parent == connector.metadata_dir
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert payload["source"] == connector.name
    assert payload["checksum"] == result.checksum

    # The recorded checksum validates the on-disk file.
    assert connector.validate(result.path) is True


@pytest.mark.parametrize("connector_cls", LIVE_CONNECTORS)
def test_live_download_rejects_unsupported_variable(connector_cls: type, tmp_path: Path) -> None:
    settings = Settings(**CREDENTIALED.get(connector_cls, {}))
    connector = _make(connector_cls, tmp_path, settings=settings)
    with pytest.raises(UnsupportedVariableError):
        connector.download(variables=["not_a_variable"])


@pytest.mark.parametrize("connector_cls", list(CREDENTIALED))
def test_credentialed_connectors_require_keys(connector_cls: type, tmp_path: Path) -> None:
    # Default Settings() has all credentials as None.
    connector = _make(connector_cls, tmp_path, settings=Settings())
    with pytest.raises(MissingCredentialsError):
        connector.download()


def test_nasa_power_needs_no_credentials(tmp_path: Path) -> None:
    connector = _make(NASAPowerConnector, tmp_path)
    result = connector.download(latitude=13.0, longitude=80.0)
    assert result.path.exists()


# --------------------------------------------------------------------------- #
# Stub connectors — architecture-ready, not live
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("connector_cls", STUB_CONNECTORS)
def test_stub_download_raises_not_implemented(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    with pytest.raises(ConnectorNotImplementedError):
        connector.download()


@pytest.mark.parametrize("connector_cls", STUB_CONNECTORS)
def test_stub_still_exposes_metadata_contract(connector_cls: type, tmp_path: Path) -> None:
    connector = _make(connector_cls, tmp_path)
    assert connector.available_variables()
    assert isinstance(connector.metadata(), DatasetMetadata)
    assert connector.descriptor.live_api_available is False
