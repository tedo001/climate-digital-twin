"""Centralized filesystem path definitions.

Per SAD Section 19 rule 2 ("No hardcoded paths"), every module that needs a
filesystem location imports it from here rather than constructing its own
``Path`` literals.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# --- Config ---
CONFIG_DIR: Path = PROJECT_ROOT / "config"
DATASET_REGISTRY_PATH: Path = CONFIG_DIR / "dataset_registry.yaml"
MODEL_REGISTRY_PATH: Path = CONFIG_DIR / "model_registry.yaml"
LOGGING_CONFIG_PATH: Path = CONFIG_DIR / "logging.yaml"

# --- Storage: files ---
STORAGE_DIR: Path = PROJECT_ROOT / "storage"
FILES_DIR: Path = STORAGE_DIR / "files"
RAW_DATA_DIR: Path = FILES_DIR / "raw"
PROCESSED_DATA_DIR: Path = FILES_DIR / "processed"
EXPORTS_DIR: Path = FILES_DIR / "exports"

# --- Ingestion: downloaded datasets & their provenance metadata ---
# Per the data-ingestion contract, raw downloads land under
# ``data/raw/<dataset>/`` and their sidecar metadata under
# ``data/metadata/<dataset>/`` so provenance is stored separately from payloads.
DATA_DIR: Path = PROJECT_ROOT / "data"
DATA_RAW_DIR: Path = DATA_DIR / "raw"
DATA_METADATA_DIR: Path = DATA_DIR / "metadata"

# --- Storage: db & cache ---
DB_DIR: Path = STORAGE_DIR / "db"
DUCKDB_PATH: Path = DB_DIR / "climate_twin.duckdb"
SCHEMA_SQL_PATH: Path = DB_DIR / "schema.sql"
MIGRATIONS_DIR: Path = DB_DIR / "migrations"

CACHE_DIR: Path = STORAGE_DIR / "cache"
DISK_CACHE_DIR: Path = CACHE_DIR / ".disk_cache"
RASTER_CACHE_DIR: Path = CACHE_DIR / ".raster_cache"

# --- AI ---
AI_DIR: Path = PROJECT_ROOT / "ai"
MODEL_CHECKPOINTS_DIR: Path = AI_DIR / "models" / "checkpoints"

# --- Logs ---
LOGS_DIR: Path = PROJECT_ROOT / "logs"

# --- Env ---
ENV_FILE_PATH: Path = PROJECT_ROOT / ".env"

ALL_RUNTIME_DIRS: tuple[Path, ...] = (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    EXPORTS_DIR,
    DATA_RAW_DIR,
    DATA_METADATA_DIR,
    DB_DIR,
    MIGRATIONS_DIR,
    DISK_CACHE_DIR,
    RASTER_CACHE_DIR,
    MODEL_CHECKPOINTS_DIR,
    LOGS_DIR,
)


def ensure_runtime_directories() -> None:
    """Create every runtime directory the application writes to, if missing.

    Idempotent; safe to call on every application startup.
    """
    for directory in ALL_RUNTIME_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
