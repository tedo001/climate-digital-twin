"""HTTP download orchestration for the data-ingestion layer.

The :class:`DownloadManager` centralizes every cross-cutting concern shared by
all connectors so individual connectors only have to describe *what* to fetch,
never *how* to fetch it robustly:

* automatic creation of the destination directory,
* streaming download to a temporary ``.part`` file (atomic rename on success),
* exponential-backoff retries via :func:`utils.decorators.retry`,
* SHA-256 checksum computation and optional integrity verification,
* progress reporting through a :class:`ProgressReporter`,
* structured logging.

Per SAD Section 19 rule 8 it never reads configuration directly; the timeout,
retry count, and chunk size all come from :func:`config.settings.get_settings`.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from config.settings import Settings, get_settings
from utils.decorators import retry
from utils.exceptions import DownloadError, IntegrityCheckError
from utils.logger import get_logger

logger = get_logger(__name__)

# Exceptions that warrant a retry: transient network / server-side failures.
_TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    requests.ConnectionError,
    requests.Timeout,
    requests.HTTPError,
)

ProgressCallback = Callable[[int, int | None], None]
"""Callable invoked as ``(bytes_so_far, total_bytes_or_none)`` during a download."""


@dataclass(slots=True)
class DownloadResult:
    """Outcome of a single completed download.

    Attributes:
        path: Filesystem path of the downloaded file.
        checksum: SHA-256 hex digest of the file's contents.
        num_bytes: Total number of bytes written.
        url: The source URL the file was retrieved from.
        extra: Free-form connector-specific annotations.
    """

    path: Path
    checksum: str
    num_bytes: int
    url: str
    extra: dict[str, Any] = field(default_factory=dict)


class ProgressReporter:
    """Log download progress at fixed percentage intervals.

    Args:
        label: Human-readable label (typically the destination file name).
        total_bytes: Expected total size, or ``None`` if unknown (chunked).
        log_every_percent: Emit a log line each time this many percent elapse.
    """

    def __init__(
        self,
        label: str,
        total_bytes: int | None,
        log_every_percent: int = 20,
    ) -> None:
        self._label = label
        self._total = total_bytes
        self._step = max(1, log_every_percent)
        self._next_threshold = self._step
        self._seen = 0

    def update(self, chunk_bytes: int) -> None:
        """Record newly received bytes and log if a threshold is crossed.

        Args:
            chunk_bytes: Number of bytes received in the latest chunk.
        """
        self._seen += chunk_bytes
        if not self._total:
            return
        percent = int(self._seen * 100 / self._total)
        if percent >= self._next_threshold:
            logger.info(
                "Downloading %s: %d%% (%d/%d bytes)",
                self._label,
                percent,
                self._seen,
                self._total,
            )
            while self._next_threshold <= percent:
                self._next_threshold += self._step

    def finish(self) -> None:
        """Log a final completion line for the transfer."""
        logger.info("Downloaded %s: %d bytes complete", self._label, self._seen)


class DownloadManager:
    """Robust, reusable HTTP file downloader shared by every connector.

    Args:
        settings: Injected settings (defaults to the process singleton).
        session: Optional pre-configured :class:`requests.Session` (mainly for
            tests / connection pooling).
    """

    def __init__(
        self,
        settings: Settings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._session = session or requests.Session()

    @property
    def session(self) -> requests.Session:
        """The underlying :class:`requests.Session` (for auxiliary auth calls)."""
        return self._session

    def download(
        self,
        url: str,
        dest_path: Path,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        expected_checksum: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> DownloadResult:
        """Download ``url`` to ``dest_path`` with retries, checksum, and progress.

        The destination directory is created automatically. The body is
        streamed to a sibling ``.part`` file and atomically renamed on success,
        so a partial transfer never masquerades as a complete file.

        Args:
            url: Source URL.
            dest_path: Destination file path.
            method: HTTP method (``"GET"`` or ``"POST"``).
            params: Query-string parameters.
            headers: Additional request headers.
            auth: Optional ``(username, password)`` basic-auth tuple.
            json_body: Optional JSON request body (for ``POST`` submissions).
            expected_checksum: If provided, the SHA-256 of the downloaded file
                must match this value or :class:`IntegrityCheckError` is raised.
            progress_callback: Optional callback invoked per chunk.

        Returns:
            A :class:`DownloadResult` describing the stored file.

        Raises:
            DownloadError: If the transfer fails after all retries.
            IntegrityCheckError: If ``expected_checksum`` does not match.
        """
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = dest_path.with_suffix(dest_path.suffix + ".part")

        try:
            checksum, num_bytes = self._stream_to_file(
                url,
                part_path,
                method=method,
                params=params,
                headers=headers,
                auth=auth,
                json_body=json_body,
                progress_callback=progress_callback,
            )
        except _TRANSIENT_EXCEPTIONS as exc:
            part_path.unlink(missing_ok=True)
            raise DownloadError(
                "Download failed after retries",
                details={"url": url, "error": str(exc)},
            ) from exc

        if expected_checksum is not None and checksum != expected_checksum:
            part_path.unlink(missing_ok=True)
            raise IntegrityCheckError(
                "Checksum mismatch on downloaded file",
                details={
                    "url": url,
                    "expected": expected_checksum,
                    "actual": checksum,
                },
            )

        shutil.move(str(part_path), str(dest_path))
        logger.info("Stored %s (%d bytes, sha256=%s)", dest_path, num_bytes, checksum[:12])
        return DownloadResult(path=dest_path, checksum=checksum, num_bytes=num_bytes, url=url)

    def _stream_to_file(
        self,
        url: str,
        part_path: Path,
        *,
        method: str,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
        auth: tuple[str, str] | None,
        json_body: dict[str, Any] | None,
        progress_callback: ProgressCallback | None,
    ) -> tuple[str, int]:
        """Stream a single HTTP response body to disk, computing its checksum.

        Wrapped with :func:`utils.decorators.retry` so transient network errors
        are retried with exponential backoff before propagating.

        Returns:
            A ``(sha256_hexdigest, num_bytes)`` tuple.
        """

        @retry(
            max_attempts=self._settings.max_download_retries,
            base_delay_seconds=2.0,
            max_delay_seconds=16.0,
            exceptions=_TRANSIENT_EXCEPTIONS,
        )
        def _attempt() -> tuple[str, int]:
            hasher = hashlib.sha256()
            total_written = 0
            with self._session.request(
                method,
                url,
                params=params,
                headers=headers,
                auth=auth,
                json=json_body,
                stream=True,
                timeout=self._settings.request_timeout_seconds,
            ) as response:
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                total = int(content_length) if content_length else None
                reporter = ProgressReporter(part_path.stem, total)
                with part_path.open("wb") as handle:
                    for chunk in response.iter_content(
                        chunk_size=self._settings.download_chunk_size_bytes
                    ):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        hasher.update(chunk)
                        total_written += len(chunk)
                        reporter.update(len(chunk))
                        if progress_callback is not None:
                            progress_callback(total_written, total)
                reporter.finish()
            return hasher.hexdigest(), total_written

        return _attempt()


def compute_checksum(path: Path, chunk_size: int = 1_048_576) -> str:
    """Compute the SHA-256 hex digest of a file on disk.

    Args:
        path: File to hash.
        chunk_size: Read block size in bytes.

    Returns:
        The lowercase hexadecimal SHA-256 digest.
    """
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(block)
    return hasher.hexdigest()
