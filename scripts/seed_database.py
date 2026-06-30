"""One-off script: initialize the DuckDB schema and verify core registries load.

Usage:
    python scripts/seed_database.py
"""

from __future__ import annotations

import sys

from config.dataset_registry import DatasetRegistry
from config.model_registry import ModelRegistry
from config.paths import ensure_runtime_directories
from core.registry.region_registry import get_region_registry
from storage.db.duckdb_connector import DuckDBConnector
from utils.exceptions import ClimateTwinError
from utils.logger import get_logger

logger = get_logger("scripts.seed_database")


def main() -> int:
    """Apply the DuckDB schema and sanity-check every config-driven registry.

    Returns:
        Process exit code: ``0`` on success, ``1`` on failure.
    """
    ensure_runtime_directories()

    try:
        connector = DuckDBConnector()
        with connector.connection():
            pass  # opening the connection alone triggers schema application
        logger.info("DuckDB schema applied successfully.")

        dataset_count = len(DatasetRegistry().list_all())
        model_count = len(ModelRegistry().list_all())
        region_count = len(get_region_registry().all())
        logger.info(
            "Registries OK: %d datasets, %d models, %d regions.",
            dataset_count,
            model_count,
            region_count,
        )
    except ClimateTwinError as exc:
        logger.error("Database seed failed: %s", exc)
        return 1

    logger.info("Database seed completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
