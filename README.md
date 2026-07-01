# AI-Powered Digital Twin of India's Climate

A modular-monolith Streamlit application combining national/global Earth
observation datasets, AI-driven forecasting, and decision-support tooling
for India's climate system. See `docs/architecture/` for the full Software
Architecture Document.

**Status:** Phase 2 (Project Bootstrap) complete. Phases 3–5 (Data
Ingestion, Climate Processing, Data Assimilation) are delivered in
subsequent iterations on top of this foundation.

## Tech Stack

Streamlit · Python 3.11 · PyTorch · Plotly / PyDeck / Folium · Rasterio /
GeoPandas / Xarray / Shapely / GDAL · Pandas / NumPy · DuckDB · Docker

## Project Layout

```
app/          Presentation + Application layers (Streamlit pages, controllers)
core/         Domain models, decision logic, region registry
climate/      Climate Intelligence layer (ClimateState, assimilation)
ai/           AI layer (prediction, models, confidence, explainability)
simulation/   What-if scenario engine
visualization/Plotly/PyDeck/Folium figure builders
data/         Ingestion connectors, preprocessing, validation, catalog
storage/      DuckDB connector, file caches, raw/processed/export files
config/       Settings, constants, paths, dataset/model registries
utils/        Logging, exceptions, decorators, validators, geo helpers
tests/        Unit and integration tests
scripts/      One-off batch scripts (seed DB, download datasets, train models)
docker/       Dockerfile and docker-compose.yml
```

Full folder structure and layer responsibilities are documented in
`docs/architecture/Climate_Digital_Twin_SAD.md`.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # optional, defaults work out of the box
```

## Running the App

```bash
python -m streamlit run app/main.py
```

The app is available at `http://localhost:8501`.

## Running Tests

```bash
pytest
```

Coverage reports are generated automatically (see `[tool.pytest.ini_options]`
in `pyproject.toml`).

## Code Quality

```bash
black .
isort .
ruff check . --fix
mypy .
lint-imports          # enforces the layered dependency rules in .importlinter
```

Install the pre-commit hooks once per clone:

```bash
pre-commit install
```

## Docker

```bash
cd docker
docker compose up --build
```

The container exposes port `8501` and persists `storage/`, `ai/models/checkpoints/`,
and `logs/` via bind mounts so data and trained models survive rebuilds.

## Useful Scripts

```bash
python scripts/seed_database.py          # apply DuckDB schema, sanity-check registries
python scripts/download_datasets.py --all
python scripts/train_model.py --model monsoon_lstm
```

## Architecture Principles (enforced)

- Strict downward dependency flow: Presentation → Application → Domain →
  Data → Storage, with `utils`/`config` as horizontal layers.
- AI/Climate/Simulation are never called directly from Streamlit pages —
  always via `app/controllers`.
- Every `ClimateState` version is immutable; updates create new versions.
- All cross-layer calls pass typed domain objects (`core.models`), never raw
  dicts/DataFrames.
- No hardcoded paths or scattered `.env` reads — everything routes through
  `config/`.

See `docs/architecture/Climate_Digital_Twin_SAD.md` Section 19 for the full
list of enforced development rules.
