"""Timeline component: a date-range slider for selecting a historical window.

Rendering only — returns the user's selection for the controller to act on;
performs no querying or aggregation itself.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st


def render_timeline_selector(
    *, max_lookback_days: int = 365, default_window_days: int = 30, key: str
) -> tuple[date, date]:
    """Render a slider for selecting a historical date range.

    Args:
        max_lookback_days: Furthest back in time the slider allows selecting.
        default_window_days: Default width of the selected window, in days.
        key: Unique Streamlit widget key.

    Returns:
        A ``(start_date, end_date)`` tuple representing the user's selection.
    """
    today = date.today()
    earliest = today - timedelta(days=max_lookback_days)
    default_start = today - timedelta(days=default_window_days)

    selection = st.slider(
        "Date range",
        min_value=earliest,
        max_value=today,
        value=(default_start, today),
        key=key,
    )
    start, end = selection
    return start, end
