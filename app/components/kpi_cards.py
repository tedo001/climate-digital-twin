"""KPI card component: renders a row of summary metric cards.

Rendering only — receives plain, already-computed display values from a
controller; never computes risk scores or aggregates domain objects itself
(SAD Section 19 rule 5).
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True, slots=True)
class KPICardData:
    """Display-ready data for a single KPI card.

    Attributes:
        label: Short metric name (e.g. ``"Avg. Temperature"``).
        value: Pre-formatted display value (e.g. ``"28.4 °C"``).
        delta: Optional pre-formatted change indicator (e.g. ``"+0.6 °C"``).
        help_text: Optional tooltip text shown on hover.
    """

    label: str
    value: str
    delta: str | None = None
    help_text: str | None = None


def render_kpi_cards(cards: list[KPICardData]) -> None:
    """Render a horizontal row of KPI cards.

    Args:
        cards: Display-ready KPI card data, one entry per card.
    """
    if not cards:
        st.info("No metrics available yet.")
        return

    columns = st.columns(len(cards))
    for column, card in zip(columns, cards, strict=True):
        with column:
            st.metric(label=card.label, value=card.value, delta=card.delta, help=card.help_text)
