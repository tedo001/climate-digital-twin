-- DuckDB schema for the Climate Digital Twin storage layer.
-- Applied idempotently at startup by storage.db.duckdb_connector.

CREATE TABLE IF NOT EXISTS historical_states (
    state_id          VARCHAR PRIMARY KEY,
    parent_version_id VARCHAR,
    valid_time        TIMESTAMP NOT NULL,
    created_at        TIMESTAMP NOT NULL,
    state_type        VARCHAR NOT NULL,
    payload_path      VARCHAR NOT NULL,  -- pointer to serialized ClimateState (zarr/parquet)
    region_ids        VARCHAR NOT NULL   -- JSON-encoded list of region_ids included
);

CREATE TABLE IF NOT EXISTS forecast_states (
    state_id          VARCHAR PRIMARY KEY,
    parent_version_id VARCHAR,
    valid_time        TIMESTAMP NOT NULL,
    created_at        TIMESTAMP NOT NULL,
    horizon_days      INTEGER NOT NULL,
    payload_path      VARCHAR NOT NULL,
    region_ids        VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_states (
    state_id          VARCHAR PRIMARY KEY,
    scenario_id       VARCHAR NOT NULL,
    base_state_id     VARCHAR NOT NULL,
    created_at        TIMESTAMP NOT NULL,
    expires_at        TIMESTAMP,         -- TTL for ephemeral cleanup
    payload_path      VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_manifest (
    dataset_name      VARCHAR NOT NULL,
    retrieved_at      TIMESTAMP NOT NULL,
    valid_time_start  TIMESTAMP NOT NULL,
    valid_time_end    TIMESTAMP NOT NULL,
    version           VARCHAR NOT NULL,
    checksum          VARCHAR,
    raw_path          VARCHAR NOT NULL,
    PRIMARY KEY (dataset_name, version, valid_time_start)
);

CREATE INDEX IF NOT EXISTS idx_historical_states_valid_time
    ON historical_states (valid_time);

CREATE INDEX IF NOT EXISTS idx_forecast_states_valid_time
    ON forecast_states (valid_time);

CREATE INDEX IF NOT EXISTS idx_dataset_manifest_name
    ON dataset_manifest (dataset_name);
