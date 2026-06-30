"""Sidebar component: region selector and global controls.

Per SAD Section 19 rule 5, this module performs rendering only — it reads
from :class:`app.state.session_manager.SessionManager` and writes user
selections back to it, with zero domain logic of its own.
"""

from __future__ import annotations

import streamlit as st

from app.state.session_manager import SessionManager
from config.constants import APP_NAME, APP_VERSION
from core.registry.region_registry import get_region_registry


def render_sidebar(session: SessionManager) -> None:
    """Render the global sidebar with region selection and app metadata.

    Args:
        session: The active :class:`SessionManager` for reading/writing
            the user's region and time-window selections.
    """
    registry = get_region_registry()
    states = registry.list_states()
    country = registry.country()

    options = [country.region_id] + [s.region_id for s in states]
    labels = {country.region_id: f"{country.name} (All)"}
    labels.update({s.region_id: s.name for s in states})

    with st.sidebar:
        st.markdown(f"### {APP_NAME}")
        st.caption(f"v{APP_VERSION}")
        st.divider()

        current_index = (
            options.index(session.selected_region_id)
            if (session.selected_region_id in options)
            else 0
        )

        selected = st.selectbox(
            "Region",
            options=options,
            index=current_index,
            format_func=lambda region_id: labels.get(region_id, region_id),
            key="sidebar_region_select",
        )
        if selected != session.selected_region_id:
            session.selected_region_id = selected

        window_days = st.slider(
            "Historical window (days)",
            min_value=1,
            max_value=365,
            value=session.selected_time_window_days,
            key="sidebar_window_slider",
        )
        if window_days != session.selected_time_window_days:
            session.selected_time_window_days = window_days

        horizon_days = st.slider(
            "Forecast horizon (days)",
            min_value=1,
            max_value=30,
            value=session.forecast_horizon_days,
            key="sidebar_horizon_slider",
        )
        if horizon_days != session.forecast_horizon_days:
            session.forecast_horizon_days = horizon_days

        st.divider()
        st.caption("Digital Twin of India's Climate — hackathon-feasible, production-quality.")
