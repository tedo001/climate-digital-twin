"""Dataset provenance metadata domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    """Provenance metadata attached to any ingested or derived dataset.

    Attributes:
        source: Originating dataset/connector name (e.g. ``"era5"``).
        retrieved_at: Timestamp when the data was fetched.
        valid_time_start: Earliest timestamp covered by the data.
        valid_time_end: Latest timestamp covered by the data.
        version: Source-reported or internally-assigned dataset version.
        checksum: Integrity checksum (e.g. SHA-256) of the raw payload.
        license: Usage license/terms identifier, if known.
        extra: Free-form additional provenance fields.
    """

    source: str
    retrieved_at: datetime
    valid_time_start: datetime
    valid_time_end: datetime
    version: str
    checksum: str | None = None
    license: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.valid_time_start > self.valid_time_end:
            raise ValueError("valid_time_start must not be after valid_time_end")
