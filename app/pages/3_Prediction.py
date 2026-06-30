"""Prediction page: AI-driven forecasts for the selected region and horizon.

Per SAD Section 19 rules 5 and 6, this module contains rendering calls only
and never calls the AI layer directly.
"""

from __future__ import annotations

import streamlit as st

from app.components.chart_widget import render_empty_chart_placeholder
from app.components.sidebar import render_sidebar
from app.controllers.prediction_controller import get_prediction_view
from app.state.session_manager import get_session_manager
from config.constants import APP_NAME

st.set_page_config(page_title=f"Prediction | {APP_NAME}", page_icon="🔮", layout="wide")

session = get_session_manager()
render_sidebar(session)

st.title("🔮 Prediction")
st.caption("AI-driven forecasts of climate variables for the selected region and horizon.")

view = get_prediction_view(session.selected_region_id, session.forecast_horizon_days)

st.subheader(f"{view.region_name} — {view.horizon_days}-day horizon")

if view.predictions_available:
    render_empty_chart_placeholder()
else:
    st.info(view.status_message)
