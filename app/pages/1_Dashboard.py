"""Dashboard page: high-level KPI overview for the selected region.

Per SAD Section 19 rule 5, this module contains rendering calls only.
"""

from __future__ import annotations

import streamlit as st

from app.components.kpi_cards import render_kpi_cards
from app.components.sidebar import render_sidebar
from app.controllers.dashboard_controller import get_dashboard_view
from app.state.session_manager import get_session_manager
from config.constants import APP_NAME

st.set_page_config(page_title=f"Dashboard | {APP_NAME}", page_icon="🌦️", layout="wide")

session = get_session_manager()
render_sidebar(session)

st.title("🌦️ Climate Dashboard")
st.caption("High-level overview of India's current climate conditions.")

view = get_dashboard_view(session.selected_region_id)

st.subheader(view.region_name)
render_kpi_cards(view.kpi_cards)

if not view.state_available and view.status_message:
    st.info(view.status_message)
