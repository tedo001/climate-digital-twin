"""Chart component: renders pre-built Plotly figures.

Figure construction belongs to the visualization layer
(``visualization.charts``); this component only places a finished
``plotly.graph_objects.Figure`` into the Streamlit layout (SAD Section 19
rule 7: visualization separated from prediction, and rule 5: no domain
logic inside `app`).
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st


def render_chart(figure: go.Figure, *, key: str, use_container_width: bool = True) -> None:
    """Render a pre-built Plotly figure inside the Streamlit layout.

    Args:
        figure: A fully constructed Plotly figure from the visualization layer.
        key: Unique Streamlit widget key to avoid duplicate-element errors.
        use_container_width: Whether the chart should stretch to its container.
    """
    st.plotly_chart(figure, use_container_width=use_container_width, key=key)


def render_empty_chart_placeholder(message: str = "No data available yet.") -> None:
    """Render a placeholder message in place of a chart with no data.

    Args:
        message: The message to display.
    """
    st.info(message)
