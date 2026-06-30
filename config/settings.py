"""Centralized application settings, loaded once and cached.

Per SAD Section 19 rule 8, no module outside ``config`` reads ``.env`` or
hardcodes a configuration constant directly.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.paths import ENV_FILE_PATH


class Settings(BaseSettings):
    """Application-wide settings sourced from environment variables / ``.env``.

    Attributes:
        environment: Deployment environment name (``development``, ``production``...).
        log_level: Root logging level.
        duckdb_path_override: Optional override for the DuckDB file location.
        nasa_power_base_url: Base URL for the NASA POWER REST API.
        era5_cds_url: Base URL for the Copernicus Climate Data Store API.
        sentinel_hub_base_url: Base URL for the Sentinel Hub API.
        request_timeout_seconds: Default HTTP timeout for connector downloads.
        max_download_retries: Default retry count for connector downloads.
        enable_disk_cache: Whether disk-backed caching is active.
        cache_ttl_seconds: Default time-to-live for cached datasets.
        default_forecast_horizon_days: Default prediction horizon.
        random_seed: Global seed for reproducible model inference.
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CDT_",
    )

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    duckdb_path_override: str | None = Field(default=None)

    nasa_power_base_url: str = Field(default="https://power.larc.nasa.gov/api")
    era5_cds_url: str = Field(default="https://cds.climate.copernicus.eu/api/v2")
    sentinel_hub_base_url: str = Field(default="https://services.sentinel-hub.com")
    modis_base_url: str = Field(default="https://modis.gsfc.nasa.gov")
    gpm_base_url: str = Field(default="https://gpm.nasa.gov")
    smap_base_url: str = Field(default="https://smap.jpl.nasa.gov")
    insat_base_url: str = Field(default="https://mosdac.gov.in")
    oceansat_base_url: str = Field(default="https://mosdac.gov.in")
    imd_base_url: str = Field(default="https://mausam.imd.gov.in")

    request_timeout_seconds: float = Field(default=30.0, gt=0)
    max_download_retries: int = Field(default=3, ge=1, le=10)

    enable_disk_cache: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=21_600, ge=0)

    default_forecast_horizon_days: int = Field(default=7, ge=1, le=30)
    random_seed: int = Field(default=42)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton.

    Returns:
        A cached :class:`Settings` instance, constructed once per process.
    """
    return Settings()
