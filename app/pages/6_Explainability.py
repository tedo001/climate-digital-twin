"""Explainability page: model interpretability for predictions (SHAP/attention).

Per SAD Section 19 rule 5, this module contains rendering calls only.
"""

from __future__ import annotations

import streamlit as st

from app.components.sidebar import render_sidebar
from app.state.session_manager import get_session_manager
from config.constants import APP_NAME

st.set_page_config(page_title=f"Explainability | {APP_NAME}", page_icon="🧩", layout="wide")

session = get_session_manager()
render_sidebar(session)

st.title("🧩 Explainability")
st.caption("Understand why the AI models produced a given prediction.")

st.info(
    "Explainability (ai.explainability.xai_engine — SHAP and attention-based "
    "explanations) is implemented on-demand once prediction models are "
    "trained and registered, per the AI Layer roadmap. This page will let "
    "you select a prediction and view its feature attributions here."
)
