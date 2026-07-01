"""Unit tests for data.ingestion.download_manager."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

from config.settings import Settings
from data.ingestion.download_manager import DownloadManager, compute_checksum
from utils.exceptions import DownloadError, IntegrityCheckError


class _FakeResponse:
    """Minimal stand-in for a streaming ``requests`` response."""

    def __init__(self, chunks: list[bytes], headers: dict[str, str] | None = None, ok: bool = True):
        self._chunks = chunks
        self.headers = headers or {}
        self._ok = ok

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def raise_for_status(self) -> None:
        if not self._ok:
            raise requests.HTTPError("simulated server error")

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        yield from self._chunks


class _FakeSession:
    """A ``requests.Session`` stub returning queued responses in order."""

    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        self.calls.append((method, url, kwargs))
        return self._responses.pop(0)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize retry backoff sleeps so tests stay fast."""
    monkeypatch.setattr("utils.decorators.time.sleep", lambda _s: None)


def _manager(session: _FakeSession) -> DownloadManager:
    return DownloadManager(settings=Settings(), session=session)  # type: ignore[arg-type]


def test_download_writes_file_and_computes_checksum(tmp_path: Path) -> None:
    chunks = [b"hello ", b"world"]
    session = _FakeSession([_FakeResponse(chunks, headers={"Content-Length": "11"})])
    dest = tmp_path / "out.bin"

    result = _manager(session).download("https://example.test/f", dest)

    assert dest.exists()
    assert dest.read_bytes() == b"hello world"
    assert result.num_bytes == 11
    assert result.checksum == hashlib.sha256(b"hello world").hexdigest()
    assert not dest.with_suffix(".bin.part").exists()


def test_download_reports_progress(tmp_path: Path) -> None:
    session = _FakeSession([_FakeResponse([b"ab", b"cd"], headers={"Content-Length": "4"})])
    seen: list[tuple[int, int | None]] = []
    _manager(session).download(
        "https://example.test/f",
        tmp_path / "p.bin",
        progress_callback=lambda done, total: seen.append((done, total)),
    )
    assert seen[-1] == (4, 4)


def test_download_integrity_mismatch_raises_and_cleans_up(tmp_path: Path) -> None:
    session = _FakeSession([_FakeResponse([b"data"])])
    dest = tmp_path / "x.bin"
    with pytest.raises(IntegrityCheckError):
        _manager(session).download("https://example.test/f", dest, expected_checksum="deadbeef")
    assert not dest.exists()
    assert not dest.with_suffix(".bin.part").exists()


def test_download_retries_then_succeeds(tmp_path: Path) -> None:
    session = _FakeSession(
        [
            _FakeResponse([], ok=False),
            _FakeResponse([b"recovered"], headers={"Content-Length": "9"}),
        ]
    )
    result = _manager(session).download("https://example.test/f", tmp_path / "r.bin")
    assert result.num_bytes == 9
    assert len(session.calls) == 2


def test_download_exhausts_retries_raises_download_error(tmp_path: Path) -> None:
    failures = [_FakeResponse([], ok=False) for _ in range(Settings().max_download_retries)]
    session = _FakeSession(failures)
    with pytest.raises(DownloadError):
        _manager(session).download("https://example.test/f", tmp_path / "e.bin")


def test_compute_checksum_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "c.bin"
    path.write_bytes(b"some payload")
    assert compute_checksum(path) == hashlib.sha256(b"some payload").hexdigest()
