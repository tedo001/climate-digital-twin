"""Decision Support page: risk assessments and actionable recommendations.

Per SAD Section 19 rules 5 and 6, this module contains rendering calls only
and never calls ``core.decision`` directly.
"""

from __future__ import annotations

import streamlit as st

from app.components.sidebar import render_sidebar
from app.controllers.decision_controller import get_decision_support_view
from app.state.session_manager import get_session_manager
from config.constants import APP_NAME

st.set_page_config(page_title=f"Decision Support | {APP_NAME}", page_icon="🧭", layout="wide")

session = get_session_manager()
render_sidebar(session)

st.title("🧭 Decision Support")
st.caption("Risk assessments and recommendations derived from predictions.")

view = get_decision_support_view(session.selected_region_id)

st.subheader(view.region_name)

if not view.risk_assessments_available:
    st.info(view.status_message)
