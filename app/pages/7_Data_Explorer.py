"""Data Explorer page: browse registered datasets and their ingestion status.

Per SAD Section 19 rule 5, this module contains rendering calls only; it
reads the read-only dataset registry rather than performing any ingestion.
"""

from __future__ import annotations

import streamlit as st

from app.components.sidebar import render_sidebar
from app.state.session_manager import get_session_manager
from config.constants import APP_NAME
from config.dataset_registry import DatasetRegistry

st.set_page_config(page_title=f"Data Explorer | {APP_NAME}", page_icon="📂", layout="wide")

session = get_session_manager()
render_sidebar(session)

st.title("📂 Data Explorer")
st.caption("Registered national and global climate data sources.")

registry = DatasetRegistry()
descriptors = registry.list_all()

rows = [
    {
        "Dataset": d.display_name,
        "Variables": ", ".join(d.variables),
        "Temporal Resolution": d.temporal_resolution,
        "Spatial Resolution (°)": d.spatial_resolution_deg,
        "Live API Available": "✅" if d.live_api_available else "🛠️ Architecture ready",
    }
    for d in descriptors
]

st.dataframe(rows, use_container_width=True, hide_index=True)

st.caption(
    "Sources marked 'Architecture ready' (INSAT, Oceansat, IMD) have a "
    "fully implemented connector interface but limited current public API "
    "access, per the project's data ingestion scope."
)
