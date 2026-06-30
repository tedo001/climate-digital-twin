"""Simulation page: what-if scenario exploration for the selected region.

Per SAD Section 19 rules 5 and 6, this module contains rendering calls only
and never calls the Simulation layer directly.
"""

from __future__ import annotations

import streamlit as st

from app.components.sidebar import render_sidebar
from app.controllers.simulation_controller import get_simulation_view
from app.state.session_manager import get_session_manager
from config.constants import APP_NAME

st.set_page_config(page_title=f"Simulation | {APP_NAME}", page_icon="🧪", layout="wide")

session = get_session_manager()
render_sidebar(session)

st.title("🧪 Simulation")
st.caption("Explore what-if climate scenarios for the selected region.")

view = get_simulation_view(session.selected_region_id)

st.subheader(view.region_name)

with st.form("scenario_form"):
    st.text_input("Scenario name", placeholder="e.g. '+2°C heatwave'", disabled=True)
    st.number_input("Temperature delta (°C)", value=0.0, step=0.5, disabled=True)
    st.number_input("Precipitation change (%)", value=0.0, step=5.0, disabled=True)
    st.form_submit_button("Run scenario", disabled=True)

if not view.scenario_available:
    st.info(view.status_message)
