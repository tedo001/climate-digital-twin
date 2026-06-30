# AI-Powered Digital Twin of India's Climate
## Software Architecture Document (SAD) — Phase 1

**Tech Stack (Locked):** Streamlit · Python · PyTorch · Plotly/PyDeck/Folium · Rasterio/GeoPandas/Xarray/Shapely/GDAL · Pandas/NumPy · DuckDB (→ PostgreSQL/PostGIS ready) · Git · Docker · Linux

**Scope:** Modular monolith. No Kubernetes, no microservices, no auth, no cloud infra. Hackathon-feasible, production-quality code organization.

---

# SECTION 1 — Overall Architecture

## 1.1 Layered Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER (Streamlit)                  │
│   Pages | Widgets | Session State | Navigation | UI Components       │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ calls (function calls, no HTTP)
┌───────────────────────────────▼──────────────────────────────────────┐
│                       APPLICATION LAYER (Orchestration)               │
│   Page Controllers | App Bootstrapper | Request Coordinators          │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        │                        │                          │
┌───────▼────────┐   ┌───────────▼──────────┐   ┌───────────▼──────────┐
│ CLIMATE INTEL   │   │     AI LAYER         │   │  SIMULATION LAYER     │
│ LAYER           │   │ Prediction Engine     │   │ Scenario Engine        │
│ Assimilation    │   │ Inference Engine      │   │ Parameter Engine       │
│ State Mgmt      │   │ Model Manager         │   │ Impact Calculator      │
│ Climate State    │   │ XAI Engine            │   │ Comparison Engine      │
└───────┬─────────┘   └───────────┬───────────┘   └───────────┬───────────┘
        │                         │                            │
        └─────────────┬───────────┴────────────┬───────────────┘
                       │                        │
            ┌──────────▼─────────┐    ┌─────────▼──────────┐
            │  BUSINESS LOGIC     │    │ VISUALIZATION LAYER │
            │ Risk/Decision Logic │    │ Map/Chart/Layer Bldrs│
            │ Recommendation Eng. │    │ Plotly/PyDeck/Folium │
            └──────────┬──────────┘    └─────────┬───────────┘
                       │                          │
┌──────────────────────▼──────────────────────────▼─────────────────────┐
│                          DATA LAYER                                    │
│  Loaders | Readers (Raster/NetCDF/Vector) | Validators | Cleaners      │
└───────────────────────────────┬─────────────────────────────────────-─┘
                                 │
┌───────────────────────────────▼──────────────────────────────────────┐
│                         STORAGE LAYER                                  │
│  DuckDB | File Cache (Parquet/Zarr/GeoTIFF) | Model Registry Files     │
└──────────────────────────────────────────────────────────────────────┘

   Cross-cutting (used by every layer): UTILITY LAYER
   Config | Logging | Caching | Error Handling | Validation Helpers
```

## 1.2 Responsibilities by Layer

| Layer | Responsibility | Talks To |
|---|---|---|
| Presentation | Render UI, capture user input, hold session state | Application Layer only |
| Application | Orchestrate calls across business/AI/sim layers per page | All core layers |
| Climate Intelligence | Maintain authoritative `ClimateState`, run assimilation | Data Layer, Storage |
| AI Layer | Train-free inference, predictions, confidence, explainability | Climate Intelligence, Storage (model registry) |
| Simulation Layer | What-if scenario execution on top of ClimateState | Climate Intelligence, AI Layer |
| Business Logic | Risk scoring, recommendations, thresholds | Climate Intelligence, AI, Simulation |
| Visualization | Convert domain objects into figure/map objects | Business Logic, Climate Intelligence |
| Data Layer | I/O, parsing, schema validation, normalization | Storage Layer only |
| Storage Layer | Persistence — DuckDB tables, file-based caches | Disk |
| Utility Layer | Config, logging, caching, errors — injected everywhere | Everything (no upward calls) |

## 1.3 Key Dependency Rule

Dependencies flow strictly **downward**: Presentation → Application → Domain Layers → Data → Storage. Utility Layer is a horizontal layer importable by anyone but importing no one. **AI is never called directly from Streamlit pages** — always via Application Layer controllers. This is enforced in Section 19.

---

# SECTION 2 — Complete Folder Structure

```
climate-digital-twin/
│
├── app/                                # PRESENTATION LAYER
│   ├── main.py                         # Streamlit entrypoint, page router
│   ├── pages/
│   │   ├── 1_Dashboard.py
│   │   ├── 2_Climate_Map.py
│   │   ├── 3_Prediction.py
│   │   ├── 4_Simulation.py
│   │   ├── 5_Decision_Support.py
│   │   ├── 6_Explainability.py
│   │   └── 7_Data_Explorer.py
│   ├── components/                     # Reusable Streamlit widgets
│   │   ├── sidebar.py
│   │   ├── map_widget.py
│   │   ├── timeline_widget.py
│   │   ├── chart_widget.py
│   │   └── kpi_cards.py
│   ├── state/
│   │   └── session_manager.py          # Centralized st.session_state wrapper
│   └── controllers/                    # APPLICATION LAYER
│       ├── dashboard_controller.py
│       ├── prediction_controller.py
│       ├── simulation_controller.py
│       └── decision_controller.py
│
├── core/                               # BUSINESS / DOMAIN LOGIC
│   ├── models/                         # Data Model Design (Section 7)
│   │   ├── climate_state.py
│   │   ├── satellite_frame.py
│   │   ├── weather_observation.py
│   │   ├── prediction.py
│   │   ├── simulation_scenario.py
│   │   ├── risk_assessment.py
│   │   ├── recommendation.py
│   │   ├── region.py
│   │   ├── climate_variable.py
│   │   └── metadata.py
│   ├── decision/
│   │   ├── risk_engine.py
│   │   ├── recommendation_engine.py
│   │   └── thresholds.py
│   └── registry/
│       └── region_registry.py          # India admin boundary registry
│
├── climate/                            # CLIMATE INTELLIGENCE LAYER
│   ├── state_manager.py                # ClimateState lifecycle owner
│   ├── assimilation/
│   │   ├── fusion_engine.py
│   │   ├── satellite_fusion.py
│   │   ├── bias_correction.py
│   │   ├── confidence_scoring.py
│   │   └── quality_flags.py
│   └── versioning/
│       └── state_version_store.py
│
├── ai/                                 # AI LAYER
│   ├── prediction/
│   │   ├── prediction_engine.py
│   │   ├── inference_engine.py
│   │   └── feature_generator.py
│   ├── models/
│   │   ├── model_manager.py
│   │   ├── architectures/              # PyTorch nn.Module defs
│   │   │   ├── monsoon_lstm.py
│   │   │   ├── drought_cnn.py
│   │   │   └── temp_transformer.py
│   │   └── checkpoints/                # .pt files (gitignored, registry-tracked)
│   ├── confidence/
│   │   └── confidence_estimator.py
│   └── explainability/
│       ├── xai_engine.py
│       ├── shap_explainer.py
│       └── attention_explainer.py
│
├── simulation/                         # SIMULATION LAYER
│   ├── scenario_manager.py
│   ├── parameter_engine.py
│   ├── simulation_runner.py
│   ├── state_modifier.py
│   ├── comparison_engine.py
│   └── impact_calculator.py
│
├── visualization/                      # VISUALIZATION LAYER
│   ├── maps/
│   │   ├── india_map_builder.py
│   │   ├── pydeck_layers.py
│   │   └── folium_layers.py
│   ├── charts/
│   │   ├── timeseries_charts.py
│   │   ├── heatmap_builder.py
│   │   └── comparison_charts.py
│   └── styles/
│       └── color_scales.py
│
├── data/                               # DATA LAYER
│   ├── ingestion/
│   │   ├── satellite_reader.py         # INSAT/Oceansat via Rasterio/GDAL
│   │   ├── imd_reader.py               # ground station data
│   │   ├── reanalysis_reader.py        # Xarray/NetCDF
│   │   └── hydrology_reader.py
│   ├── preprocessing/
│   │   ├── cleaner.py
│   │   ├── normalizer.py
│   │   ├── regridder.py
│   │   └── geocoder.py
│   ├── validation/
│   │   └── schema_validator.py
│   └── catalog/
│       └── dataset_catalog.py          # discovers/lists available datasets
│
├── storage/                            # STORAGE LAYER
│   ├── db/
│   │   ├── duckdb_connector.py
│   │   ├── schema.sql
│   │   └── migrations/
│   ├── cache/
│   │   ├── disk_cache.py
│   │   ├── memory_cache.py
│   │   └── raster_cache.py
│   └── files/
│       ├── raw/                        # immutable source datasets
│       ├── processed/                  # cleaned parquet/zarr
│       └── exports/                    # user-downloaded artifacts
│
├── config/                             # CONFIGURATION ARCHITECTURE
│   ├── settings.py                     # pydantic-style settings loader
│   ├── constants.py
│   ├── paths.py
│   ├── model_registry.yaml
│   ├── dataset_registry.yaml
│   └── logging.yaml
│
├── utils/                              # UTILITY LAYER
│   ├── logger.py
│   ├── exceptions.py
│   ├── timer.py
│   ├── decorators.py
│   ├── validators.py
│   └── geo_utils.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/                            # one-off / batch scripts
│   ├── seed_database.py
│   ├── download_datasets.py
│   └── train_model.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── docs/
│   └── architecture/  (this document and diagrams)
│
├── .env.example
├── pyproject.toml
└── README.md
```

**Naming conventions:** `snake_case` for files/functions, `PascalCase` for classes, modules named after the domain noun they own (`climate_state.py` owns `ClimateState`). Every top-level package is independently importable with no upward imports (enforced by import-linter rule in Section 19). **Ownership:** each package owns exactly one layer's responsibility — no package straddles two layers.

---

# SECTION 3 — Module Architecture

| Module | Responsibilities | Inputs | Outputs | Depends On | Public Interface |
|---|---|---|---|---|---|
| `core.models` | Define all domain entities (dataclasses) | — | Typed objects | `utils` | `ClimateState`, `Region`, etc. |
| `data` | Ingest, clean, validate raw datasets | Raw files (NetCDF/GeoTIFF/CSV) | Normalized DataFrames/xr.Dataset | `storage`, `utils`, `core.models` | `load_satellite_frame()`, `load_observations()` |
| `climate` | Build/update authoritative ClimateState via assimilation | `SatelliteFrame`, `WeatherObservation` | `ClimateState` (versioned) | `data`, `core.models`, `storage` | `get_current_state()`, `update_state()` |
| `ai` | Predict future climate variables, estimate confidence, explain | `ClimateState`, features | `Prediction`, `RiskAssessment` inputs | `climate`, `core.models`, `storage` | `predict(region, horizon)`, `explain(prediction)` |
| `simulation` | Run what-if scenarios on top of ClimateState | `SimulationScenario` | Modified `ClimateState` projections | `climate`, `ai`, `core.models` | `run_scenario()`, `compare()` |
| `core.decision` | Compute risk scores & recommendations | `Prediction`, `ClimateState` | `RiskAssessment`, `Recommendation` | `core.models` | `assess_risk()`, `recommend()` |
| `visualization` | Build chart/map figure objects | Domain objects | Plotly/PyDeck/Folium objects | `core.models` | `build_map()`, `build_chart()` |
| `app.controllers` | Orchestrate one page's full workflow | UI input | Rendered components | All above | one controller fn per page |
| `app.pages` | Streamlit rendering only | Controller outputs | Rendered HTML/widgets | `app.controllers`, `app.components` | Streamlit script |
| `config` | Centralized settings/constants | `.env`, YAML | Settings object | `utils` | `get_settings()` |
| `utils` | Cross-cutting helpers | — | — | nothing internal | logging, caching, exceptions |

**Internal Components note:** Each module's internal classes (e.g., `ai.models.model_manager.ModelManager`) are private to the module; only the functions listed in "Public Interface" are imported by other layers — enforced via `__init__.py` re-exports acting as the module's public API boundary.

---

# SECTION 4 — Application Flow

1. **Startup** — `app/main.py` executed by `streamlit run`. Loads `.env`, calls `config.settings.get_settings()`.
2. **Configuration Loading** — `config.settings` parses `dataset_registry.yaml` and `model_registry.yaml` into typed registries; validates required paths exist.
3. **Logging Init** — `utils.logger` configured from `config/logging.yaml`; one logger per layer namespace (`climate`, `ai`, `simulation`, `data`).
4. **Dataset Discovery** — `data.catalog.dataset_catalog` scans `storage/files/raw` + registry entries, builds an in-memory manifest of available datasets with freshness timestamps.
5. **Cache Warm-up** — `storage.cache.disk_cache` checks for existing processed Parquet/Zarr; lazy — nothing loaded into memory yet, only existence checked.
6. **Model Loading** — `ai.models.model_manager.ModelManager` lazily registers available checkpoints from `model_registry.yaml` without loading weights into memory until first inference call.
7. **Digital Twin Initialization** — `climate.state_manager` loads the **latest persisted** `ClimateState` snapshot from DuckDB (or triggers a cold-start assimilation run if none exists).
8. **Session State Init** — `app.state.session_manager` initializes `st.session_state` keys (selected region, time window, active scenario) with defaults.
9. **Rendering** — `app/main.py` renders sidebar/navigation; routes to the selected page in `app/pages/`.
10. **User Interaction** — Widget events captured by page → delegated to the matching `app.controllers` function (never directly to `ai`/`climate`/`simulation`).
11. **Prediction Cycle** — Controller calls `ai.prediction.prediction_engine.predict()` → internally: `feature_generator` builds features from current `ClimateState` → `inference_engine` runs PyTorch forward pass → `confidence_estimator` attaches confidence → result wrapped as `Prediction` object → cached.
12. **Simulation Cycle** — Controller calls `simulation.simulation_runner.run_scenario()` → `parameter_engine` validates scenario params → `state_modifier` clones+perturbs `ClimateState` → `ai` re-invoked on perturbed state if needed → `impact_calculator` quantifies deltas → `comparison_engine` produces before/after diff.
13. **Shutdown** — Streamlit session end triggers no explicit teardown; DuckDB connections closed via context managers per-call (no long-lived locks), disk caches persist for next run.

---

# SECTION 5 — Climate Digital Twin Architecture

## 5.1 Climate State Representation

`ClimateState` is the single authoritative, versioned snapshot of India's climate system at a point in time, composed of:

- **Spatial Dimension** — gridded representation keyed by `Region` (state/district polygons via GeoPandas) plus raw raster grid (Xarray `Dataset` with lat/lon/time dims) for sub-region resolution.
- **Time Dimension** — each `ClimateState` is timestamped (`valid_time`) and tagged with `state_type`: `historical | nowcast | forecast | simulated`.
- **Climate Variables** — a dict of `ClimateVariable` objects (temperature, precipitation, soil moisture, SST, wind, humidity, NDVI, etc.), each carrying its own units, source, and confidence layer.

## 5.2 Update Cycle

```
New Observation/Satellite Frame arrives
        ↓
Assimilation Engine (climate.assimilation)
        ↓
Bias-corrected, fused variable update
        ↓
New ClimateState version created (immutable, prior version retained)
        ↓
Persisted to DuckDB (state_versions table) + Zarr for raster payloads
        ↓
In-memory "current state" pointer updated
```

## 5.3 Versioning

Each `ClimateState` has a UUID, `parent_version_id` (lineage), and `created_at`. States are **immutable once written** — updates always create a new version, enabling reproducibility and rollback. A lightweight version table in DuckDB tracks lineage; raster payloads live in Zarr stores referenced by version ID, not duplicated.

## 5.4 Storage Split

| Store Type | Mechanism | Content |
|---|---|---|
| Historical | DuckDB table `historical_states` + Zarr | Past assimilated states |
| Forecast | DuckDB table `forecast_states` + Zarr | `Prediction`-derived future states |
| Simulation | DuckDB table `simulation_states` (ephemeral, TTL-cached) | Scenario outputs, not persisted long-term by default |

## 5.5 State Synchronization

`climate.state_manager` is the **single writer** to the "current state" pointer (thread-safety not required since Streamlit's single-process model is assumed per Section 19 simplification); all readers (AI, Simulation, Visualization) receive **immutable references**, preventing accidental mutation — simulation always operates on a deep-copied state.

---

# SECTION 6 — Data Flow Architecture

```
SATELLITE (INSAT/Oceansat) ─┐
GROUND STATIONS (IMD)       ─┤
REANALYSIS PRODUCTS         ─┼──▶ [data.ingestion.*] readers (Rasterio/GDAL/Xarray)
HYDROLOGICAL DATASETS       ─┘
        │
        ▼
PREPROCESSING  [data.preprocessing]
  - cleaning (missing/invalid values)
  - normalization (units, projections via GeoPandas/Shapely)
  - regridding (common spatial resolution)
        │
        ▼
ASSIMILATION  [climate.assimilation]
  - multi-source fusion
  - bias correction
  - confidence + quality flagging
        │
        ▼
CLIMATE STATE  [climate.state_manager]  → persisted (Sec 5)
        │
        ├──────────────▶ PREDICTION [ai.prediction]
        │                     │
        │                     ▼
        │                 Prediction objects (forecast states)
        │                     │
        ├──────────────▶ SIMULATION [simulation] (consumes state + predictions)
        │                     │
        │                     ▼
        │                 SimulationScenario outputs
        │                     │
        ▼                     ▼
   DECISION SUPPORT [core.decision]
   - risk scoring, recommendations
        │
        ▼
   VISUALIZATION [visualization]
   - maps, charts, layers → rendered in Streamlit
```

**Transformation notes:** each arrow is a pure-function boundary returning a typed domain object — no layer mutates another layer's input in place, which keeps every stage independently unit-testable.

---

# SECTION 7 — Data Model Design

| Object | Key Attributes | Relationships | Lifecycle | Owner |
|---|---|---|---|---|
| `ClimateState` | id, valid_time, state_type, variables: Dict[str, ClimateVariable], region_scope, parent_version_id | Has many `ClimateVariable`; references `Region` | Immutable, versioned | `climate` |
| `SatelliteFrame` | satellite_id, sensor, capture_time, raster_path, bounds, resolution | Consumed by Assimilation | Created at ingestion, archived raw | `data` |
| `WeatherObservation` | station_id, timestamp, variable, value, lat/lon, quality_flag | Consumed by Assimilation | Created at ingestion | `data` |
| `Prediction` | id, target_variable, horizon, region, predicted_values, confidence, model_version, generated_at | References source `ClimateState`; produces forecast `ClimateState` | Created per inference call, cached | `ai` |
| `SimulationScenario` | id, name, parameters: Dict, base_state_id, created_at | References base `ClimateState`; produces modified state | Created per user run, ephemeral by default | `simulation` |
| `RiskAssessment` | id, region, hazard_type, risk_score, severity, contributing_factors | References `Prediction`/`ClimateState` | Derived, recomputed on demand | `core.decision` |
| `Recommendation` | id, target_region, action_text, priority, basis (RiskAssessment ref) | References `RiskAssessment` | Derived | `core.decision` |
| `Region` | id, name, admin_level, geometry (Shapely), parent_region_id | Hierarchical (state→district) | Static reference data | `core.registry` |
| `ClimateVariable` | name, unit, value_grid (xr.DataArray ref), confidence_grid, source | Owned by `ClimateState` | Embedded, immutable | `climate` |
| `Metadata` | source, license, ingestion_time, version, quality_notes | Attached to every dataset-derived object | Append-only | `data` |

All objects are implemented as **typed Python dataclasses** (or `attrs`) with explicit `to_dict()`/`from_dict()` for DuckDB/Parquet serialization — no ORM, keeping the layer dependency-light.

---

# SECTION 8 — AI Architecture

```
ClimateState ──▶ Feature Generator ──▶ Feature Vector/Tensor
                                              │
                                              ▼
                                      Model Manager
                                  (resolves model_version
                                   from model_registry.yaml,
                                   lazy-loads PyTorch checkpoint)
                                              │
                                              ▼
                                      Inference Engine
                                  (forward pass, batching,
                                   device selection CPU/GPU)
                                              │
                          ┌───────────────────┼────────────────────┐
                          ▼                   ▼                    ▼
                Confidence Estimator   Prediction Engine    Explainable AI
                (ensemble/dropout      (wraps raw tensor      (SHAP / attention
                 variance → score)      into Prediction obj)   maps → reasons)
                          │                   │                    │
                          └─────────┬─────────┴──────────┬─────────┘
                                    ▼                     ▼
                              Prediction object      Explanation object
                                    │
                                    ▼
                          Scenario Engine (simulation layer reuses
                          this same Prediction Engine for re-inference
                          on perturbed states)
```

**Interaction rules:** `Prediction Engine` is the only public entrypoint other layers call; it internally composes `Feature Generator → Model Manager → Inference Engine → Confidence Estimator`. `Explainable AI` is invoked separately, on-demand (expensive), only when the user opens the Explainability page, never on every prediction call (performance, Section 17).

---

# SECTION 9 — Data Assimilation Architecture

| Component | Function |
|---|---|
| `Observation Fusion` | Combines `WeatherObservation` (point) + gridded sources into one spatial field via interpolation (kriging/IDW) |
| `Satellite Fusion` | Merges multiple satellite passes (INSAT/Oceansat) for a given window, resolving overlaps by recency + sensor confidence |
| `Bias Correction` | Applies station-vs-satellite systematic offset correction using historical calibration tables |
| `Confidence Scoring` | Produces per-grid-cell confidence layer from source agreement, data age, sensor quality |
| `Quality Flags` | Tags cells as `verified | interpolated | low_confidence | missing` for downstream transparency |
| `Update Logic` | Decides whether new data triggers a new `ClimateState` version (threshold-based: significant delta or time-elapsed) vs. is buffered |

All five feed into `climate.assimilation.fusion_engine` which is the single orchestrator producing the variable set consumed by `state_manager`.

---

# SECTION 10 — Simulation Engine

| Component | Function |
|---|---|
| `Scenario Manager` | CRUD for `SimulationScenario` objects, validates against allowed parameter ranges |
| `Parameter Engine` | Translates user-facing sliders (e.g., "+2°C", "-30% rainfall") into structured perturbation parameters |
| `Simulation Runner` | Orchestrates: clone base state → apply modifier → optionally re-run AI inference on modified state |
| `State Modifier` | Pure function applying parameter deltas to a deep-copied `ClimateState` (never mutates original) |
| `Comparison Engine` | Diffs baseline vs. simulated state per variable/region |
| `Impact Calculator` | Translates variable diffs into human-relevant impact metrics (e.g., crop stress index, flood risk delta) |

Simulation never writes back to the canonical historical/forecast stores — outputs live in the ephemeral `simulation_states` cache (Section 5.4), keeping the digital twin's ground truth uncontaminated by hypothetical runs.

---

# SECTION 11 — Visualization Architecture

| Component | Library | Purpose |
|---|---|---|
| Interactive India Map | PyDeck (primary, GPU-accelerated layers) + Folium (lightweight fallback) | Base choropleth/region selection |
| Climate Layers | PyDeck `HeatmapLayer`/`GeoJsonLayer` | Per-variable overlays (temp, rainfall, drought index) |
| Timeline | Plotly slider + `app.components.timeline_widget` | Scrub through historical/forecast states |
| Heatmaps | Plotly `Heatmap`/`Densitymap` | Gridded variable visualization |
| Charts | Plotly time series, bar, radar | Trends, comparisons |
| Prediction Views | Plotly with confidence bands | Forecast + uncertainty |
| Simulation Views | Plotly diff charts + side-by-side maps | Before/after scenario comparison |

**Architecture principle:** `visualization` modules accept only domain objects (`ClimateState`, `Prediction`, `SimulationScenario`) and return **figure objects** (not rendered widgets) — actual `st.plotly_chart()`/`st.pydeck_chart()` calls happen only in `app/pages`, keeping visualization logic UI-framework-agnostic and unit-testable without Streamlit running.

---

# SECTION 12 — Streamlit Page Architecture

| Page | Purpose | Widgets | State Used | Data Source | Navigation |
|---|---|---|---|---|---|
| Dashboard | National overview KPIs | KPI cards, mini-map, alert banner | `selected_date` | `climate.state_manager` | Entry page |
| Climate Map | Explore spatial climate layers | Layer toggle, region selector, time slider | `selected_region`, `selected_layer`, `time_window` | `climate`, `visualization.maps` | From sidebar |
| Prediction | View AI forecasts per region/variable | Variable dropdown, horizon selector, region picker | `prediction_cache_key` | `ai.prediction_engine` | From sidebar |
| Simulation | Run what-if scenarios | Parameter sliders, scenario name, run button | `active_scenario_id` | `simulation.simulation_runner` | From sidebar |
| Decision Support | Risk + recommendations | Risk filter, region selector | `selected_region` | `core.decision` | From sidebar |
| Explainability | Inspect why a prediction was made | Prediction selector, SHAP view toggle | `selected_prediction_id` | `ai.explainability` | From Prediction page link |
| Data Explorer | Browse raw/processed datasets, catalog | Dataset filter, download button | `selected_dataset` | `data.catalog` | From sidebar |

State management is centralized through `app.state.session_manager`, which exposes typed getters/setters (`get_selected_region()`, `set_active_scenario()`) instead of raw `st.session_state[...]` access scattered across pages — this is a strict rule in Section 19.

---

# SECTION 13 — Configuration Architecture

| Element | Mechanism |
|---|---|
| Configuration Files | `config/settings.py` (typed), `dataset_registry.yaml`, `model_registry.yaml`, `logging.yaml` |
| Environment Variables | `.env` (paths, DB file location, debug flag) loaded once at startup via `python-dotenv`, never read ad-hoc elsewhere |
| Constants | `config/constants.py` — fixed enums (variable names, region codes, units) |
| Paths | `config/paths.py` — single source of truth for all filesystem paths, no hardcoded strings elsewhere (Section 19 rule) |
| Model Registry | YAML mapping `model_name → {checkpoint_path, version, input_schema, variable}` |
| Dataset Registry | YAML mapping `dataset_name → {source, format, refresh_cadence, path_pattern}` |
| Application Settings | Aggregated into one `Settings` object injected (not globally imported) into modules that need it |

---

# SECTION 14 — Logging Architecture

| Log Stream | Logger Namespace | Sink |
|---|---|---|
| Application Logs | `app.*` | `logs/app.log` |
| Model Logs | `ai.*` | `logs/model.log` |
| Dataset Logs | `data.*` | `logs/dataset.log` |
| Error Logs | root error handler | `logs/error.log` (ERROR+ only, all namespaces) |
| Performance Logs | `utils.timer` decorator output | `logs/performance.log` |
| Simulation Logs | `simulation.*` | `logs/simulation.log` |

Configured centrally in `config/logging.yaml` using Python's standard `logging` dictConfig — rotating file handlers, structured (JSON-able) formatter for future log aggregation readiness, console handler at INFO in dev / WARNING in "production" mode.

---

# SECTION 15 — Caching Strategy

| Cache Type | Mechanism | Use Case |
|---|---|---|
| Memory Cache | `functools.lru_cache` / Streamlit `@st.cache_data` wrappers in `utils.decorators` | Hot, small, frequently reused objects (region lookups, current state pointer) |
| Disk Cache | `storage.cache.disk_cache` (joblib/pickle-backed) | Expensive preprocessing results across sessions |
| Dataset Cache | Parquet/Zarr in `storage/files/processed` | Cleaned datasets, avoids re-parsing raw NetCDF/GeoTIFF every run |
| Model Cache | In-memory dict in `ModelManager`, keyed by model_version | Avoid reloading PyTorch weights per inference call |
| Prediction Cache | Disk + memory, keyed by (region, variable, horizon, state_version) | Avoid recomputation for repeated identical queries |
| Map Cache | `st.cache_data` on figure-builder functions, keyed by layer+region+time | Avoid rebuilding PyDeck/Plotly objects on every rerun |

All caches are invalidated by `ClimateState` version change — cache keys always incorporate the state version ID to guarantee freshness correctness.

---

# SECTION 16 — Error Handling Strategy

```
ClimateTwinError (base, in utils.exceptions)
├── DataIngestionError
│   ├── DatasetNotFoundError
│   └── SchemaValidationError
├── AssimilationError
├── ModelError
│   ├── ModelNotLoadedError
│   └── InferenceError
├── SimulationError
│   └── InvalidScenarioParameterError
└── VisualizationError
```

- **Recovery:** transient I/O failures retried with exponential backoff (`utils.decorators.retry`); assimilation failures fall back to last-known-good `ClimateState`.
- **Fallbacks:** if a model checkpoint fails to load, AI layer degrades to a documented "unavailable" prediction state rather than crashing the page.
- **Validation:** `data.validation.schema_validator` rejects malformed datasets at ingestion boundary — errors never propagate silently downstream.
- **User-friendly errors:** Application Layer controllers catch all `ClimateTwinError` subclasses and translate to plain-language `st.error()` messages; raw stack traces only appear in logs, never in UI.

---

# SECTION 17 — Performance Strategy

| Technique | Application |
|---|---|
| Lazy Loading | Models, large rasters, and Zarr stores loaded only on first access, not at startup |
| Incremental Updates | `ClimateState` updates apply deltas to changed grid cells/regions rather than full recomputation |
| Background Processing | Long assimilation/training jobs run via `scripts/` as separate processes, not blocking the Streamlit thread |
| Parallel Processing | `multiprocessing`/`joblib` for embarrassingly parallel preprocessing across raster tiles |
| Memory Optimization | Xarray chunked/Dask-backed reads for large NetCDF; avoid loading full-India rasters into memory when a regional subset suffices |
| Large Raster Handling | Cloud-Optimized GeoTIFF (COG) + windowed Rasterio reads; Zarr chunking aligned to typical query access patterns (per-region, per-time-slice) |

---

# SECTION 18 — Coding Standards

- **Naming:** `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, modules named for the single concept they own.
- **Typing:** full type hints on all public functions (`mypy`-checkable); domain objects are typed dataclasses.
- **Documentation:** Google-style docstrings on every public function/class — purpose, args, returns, raises.
- **Functions:** single responsibility, <50 lines as a guideline, no hidden side effects on inputs.
- **Classes:** used only for stateful components (`ModelManager`, `StateManager`) or domain objects; pure transformations stay as functions.
- **Comments:** explain *why*, not *what*; no commented-out dead code committed.
- **Error Handling:** never bare `except:`; always catch specific exception types from `utils.exceptions`.
- **Logging:** structured logging via module-level `logger = get_logger(__name__)`, no `print()` in library code.
- **Imports:** absolute imports only, grouped stdlib/third-party/local, no wildcard imports.
- **Formatting:** `black` + `isort` enforced via pre-commit; `ruff` for linting.

---

# SECTION 19 — Development Rules

1. No duplicated logic — shared logic extracted to `utils` or the owning domain module.
2. No hardcoded paths — all paths sourced from `config/paths.py`.
3. No circular imports — enforced via `import-linter` contract matching the layer diagram in Section 1.
4. Every module independently testable — no module requires Streamlit runtime to be imported/tested.
5. Business logic strictly separated from UI — `app/pages` contain rendering calls only, zero domain logic.
6. **AI is never called directly from Streamlit pages** — always via `app/controllers`.
7. Visualization separated from prediction — `visualization` never imports `ai` directly; controllers pass already-computed `Prediction` objects to figure builders.
8. Configuration centralized — no module reads `.env` or hardcodes a constant outside `config/`.
9. All cross-layer calls pass typed domain objects, never raw dicts/DataFrames across layer boundaries.
10. Each layer owns its own exceptions, subclassed from `ClimateTwinError`.

---

# SECTION 20 — Future Scalability

| Future Need | How Current Architecture Supports It |
|---|---|
| More datasets | New reader added to `data.ingestion`, registered in `dataset_registry.yaml` — no change to downstream layers |
| More AI models | New entry in `model_registry.yaml` + new architecture file in `ai/models/architectures` — `ModelManager` resolves by config |
| Real-time updates | `climate.assimilation.update_logic` already threshold-driven; swapping a polling scheduler for a streaming trigger doesn't change downstream contract |
| Additional simulations | New `SimulationScenario` subtype + handler in `simulation_runner`, reusing existing `state_modifier`/`impact_calculator` |
| New climate variables | New `ClimateVariable` entries — `ClimateState` is a dict-based variable container, not a fixed schema |
| Additional satellite missions | New ingestion reader implementing the existing `SatelliteFrame` interface |
| API support | `app/controllers` functions are already framework-agnostic — a thin FastAPI layer could call the same controllers without touching core/climate/ai/simulation |
| DuckDB → PostgreSQL/PostGIS | `storage.db.duckdb_connector` is the only module that knows SQL dialect specifics — swappable behind the same connector interface |

No layer above Data/Storage needs to change for any of the above — this is the direct payoff of the strict downward-dependency rule in Section 1.3.

---

# FINAL SECTION — Architecture Review

**Strengths**
- Clean unidirectional layering keeps AI, simulation, and visualization independently testable and replaceable.
- Immutable, versioned `ClimateState` gives reproducibility — critical for a scientific/climate system where "what data produced this prediction" must be answerable.
- Config/registry-driven extensibility (Section 20) avoids the need for major refactors as the hackathon prototype grows.

**Potential Weaknesses**
- DuckDB is single-writer/single-process; fine for a hackathon/single-instance deployment, but will need genuine concurrency handling if multiple analysts use it simultaneously — flagged for the PostgreSQL migration path already designed in.
- Ephemeral simulation storage means scenario results aren't shared across sessions without explicit export — acceptable tradeoff for now, but a "saved scenarios" feature would need lightweight persistence.
- XAI module (SHAP/attention) can be computationally expensive — current design defers it to on-demand calls only, which is correct, but real-time XAI at scale would need precomputation.

**Overengineering Avoided**
- No microservices, no message queues, no auth/user management, no Kubernetes — deliberately a modular monolith, matching the "hackathon-feasible" constraint while still respecting layer boundaries that make it production-extensible later.

**Simplifications Made (and why they're acceptable)**
- Single-process concurrency model — acceptable because Streamlit itself is single-session-oriented; true multi-user concurrency is a Phase 2+ concern.
- File-based model/dataset registries (YAML) instead of a database-backed registry — simpler to version-control and review in Git, appropriate at this scale.

**Risks**
- Data quality/availability from national sources (IMD, INSAT) is the biggest external risk — assimilation's bias correction and quality-flagging components are designed specifically to make this risk visible rather than hidden.
- PyTorch model accuracy for monsoon/extreme-event prediction is inherently uncertain — the confidence estimator and explicit `confidence_score` on every `Prediction` object is the architectural mitigation, ensuring uncertainty is never silently dropped.

**Future Improvements**
- Add a streaming/event-driven assimilation trigger once real-time satellite feeds are available.
- Introduce a thin API layer (Section 20) once external consumers (other agencies/apps) need programmatic access.
- Move from ephemeral to persisted, shareable simulation scenarios once multi-user collaboration is in scope.

**Why this is hackathon-appropriate yet production-quality:** every layer boundary, naming convention, and data model defined here costs nothing extra to implement quickly, but prevents the most common hackathon failure mode — tangled UI/business/AI code that can't be extended after the demo. The architecture is intentionally "boring" at the infrastructure level (single DuckDB file, local Docker container, no distributed systems) while being rigorous at the domain-modeling and layering level, which is exactly where rigor pays off for a scientific climate system.
