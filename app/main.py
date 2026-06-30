"""Streamlit application entrypoint.

Implements the startup sequence defined in SAD Section 4:
1. Load configuration.
2. Initialize logging.
3. Discover datasets.
4. Warm cache (existence checks only).
5. Register AI models (lazy — no weights loaded yet).
6. Initialize the Digital Twin's current-state pointer (best-effort).
7. Initialize session state.
8. Render navigation and route to the selected page.
"""

from __future__ import annotations

import streamlit as st

from config.dataset_registry import DatasetRegistry
from config.model_registry import ModelRegistry
from config.paths import ensure_runtime_directories
from config.settings import get_settings
from storage.cache import get_cache_manager
from utils.exceptions import ConfigurationError
from utils.logger import configure_logging, get_logger

st.set_page_config(
    page_title="AI-Powered Digital Twin of India's Climate",
    page_icon="🌍",
    layout="wide",
)


def _bootstrap() -> None:
    """Run the one-time application bootstrap sequence.

    Idempotent across Streamlit reruns via ``st.session_state`` guard.
    """
    if st.session_state.get("_bootstrapped", False):
        return

    configure_logging()
    logger = get_logger("app")

    ensure_runtime_directories()
    get_settings()  # validates env/settings parse cleanly; raises on failure

    try:
        dataset_count = len(DatasetRegistry().list_all())
        model_count = len(ModelRegistry().list_all())
        logger.info("Startup: %d datasets and %d models registered", dataset_count, model_count)
    except ConfigurationError as exc:
        logger.error("Startup registry load failed: %s", exc)
        st.error(f"Configuration error during startup: {exc.message}")
        st.stop()

    get_cache_manager()  # warms cache manager singleton, no data loaded yet

    st.session_state["_bootstrapped"] = True


_bootstrap()

st.title("🌍 AI-Powered Digital Twin of India's Climate")
st.markdown("""
Welcome to the **Climate Digital Twin** — a unified view of India's climate
system combining national and global Earth-observation data, AI-driven
forecasting, and decision-support tooling.

Use the navigation in the sidebar to explore:

- **Dashboard** — current conditions at a glance
- **Climate Map** — spatial view of climate variables
- **Prediction** — AI-driven forecasts
- **Simulation** — what-if scenario exploration
- **Decision Support** — risk assessments and recommendations
- **Explainability** — understand model predictions
- **Data Explorer** — browse registered data sources
""")

st.info(
    "This is the Phase 2 (Project Bootstrap) build. Data ingestion, "
    "climate processing, and assimilation land in subsequent delivery "
    "phases — the navigation, state management, and layer boundaries "
    "established here are already wired to receive them."
)
