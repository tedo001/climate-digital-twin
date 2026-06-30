"""DuckDB connector.

Per SAD Section 20, this is the only module that knows DuckDB-specific SQL
dialect details, making a future migration to PostgreSQL/PostGIS a
swap-behind-the-same-interface change.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from config.paths import DUCKDB_PATH, SCHEMA_SQL_PATH
from config.settings import get_settings
from utils.exceptions import StorageError
from utils.logger import get_logger

logger = get_logger(__name__)

_INIT_LOCK = threading.Lock()


class DuckDBConnector:
    """Owns the DuckDB file location and schema initialization.

    Per SAD Section 5.5, DuckDB connections are opened per-call via context
    managers rather than held open long-lived, since Streamlit's
    single-process model removes the need for a persistent connection pool.

    Args:
        db_path: Path to the DuckDB database file.
        schema_path: Path to the ``schema.sql`` file applied on first use.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        schema_path: Path = SCHEMA_SQL_PATH,
    ) -> None:
        settings = get_settings()
        override = settings.duckdb_path_override
        self._db_path = db_path or (Path(override) if override else DUCKDB_PATH)
        self._schema_path = schema_path
        self._schema_initialized = False

    def _ensure_schema(self, conn: duckdb.DuckDBPyConnection) -> None:
        if self._schema_initialized:
            return
        with _INIT_LOCK:
            if self._schema_initialized:
                return
            if not self._schema_path.exists():
                raise StorageError(
                    "DuckDB schema file not found", details={"path": str(self._schema_path)}
                )
            try:
                schema_sql = self._schema_path.read_text(encoding="utf-8")
                conn.execute(schema_sql)
            except duckdb.Error as exc:
                raise StorageError(
                    "Failed to apply DuckDB schema", details={"error": str(exc)}
                ) from exc
            self._schema_initialized = True
            logger.info("DuckDB schema initialized at %s", self._db_path)

    @contextmanager
    def connection(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Open a short-lived DuckDB connection with schema guaranteed present.

        Yields:
            An active :class:`duckdb.DuckDBPyConnection`.

        Raises:
            StorageError: If the connection cannot be opened or schema applied.
        """
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = duckdb.connect(str(self._db_path))
        except duckdb.Error as exc:
            raise StorageError(
                "Failed to open DuckDB connection", details={"path": str(self._db_path)}
            ) from exc
        try:
            self._ensure_schema(conn)
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        """Execute a single statement with no result expected (DDL/DML).

        Args:
            query: SQL statement to execute.
            params: Optional positional parameters.

        Raises:
            StorageError: If execution fails.
        """
        with self.connection() as conn:
            try:
                conn.execute(query, params or [])
            except duckdb.Error as exc:
                raise StorageError(
                    "DuckDB execute failed", details={"query": query, "error": str(exc)}
                ) from exc

    def fetch_all(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> list[tuple[object, ...]]:
        """Execute a query and return all rows.

        Args:
            query: SQL query to execute.
            params: Optional positional parameters.

        Returns:
            A list of result row tuples.

        Raises:
            StorageError: If the query fails.
        """
        with self.connection() as conn:
            try:
                return conn.execute(query, params or []).fetchall()
            except duckdb.Error as exc:
                raise StorageError(
                    "DuckDB query failed", details={"query": query, "error": str(exc)}
                ) from exc
