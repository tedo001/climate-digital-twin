"""Unit tests for storage.db.duckdb_connector."""

from __future__ import annotations

from pathlib import Path

from storage.db.duckdb_connector import DuckDBConnector


def test_connector_applies_schema_and_allows_insert(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    connector = DuckDBConnector(db_path=db_path)

    connector.execute(
        "INSERT INTO dataset_manifest "
        "(dataset_name, retrieved_at, valid_time_start, valid_time_end, version, raw_path) "
        "VALUES (?, now(), now(), now(), ?, ?)",
        ("era5", "1.0.0", "/tmp/era5.nc"),
    )

    rows = connector.fetch_all("SELECT dataset_name, version FROM dataset_manifest")
    assert rows == [("era5", "1.0.0")]


def test_connector_is_idempotent_across_connections(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    connector = DuckDBConnector(db_path=db_path)

    with connector.connection() as conn:
        conn.execute("SELECT 1")
    with connector.connection() as conn:
        conn.execute("SELECT 1")  # schema already applied; should not raise
