"""Map component: renders pre-built PyDeck or Folium map objects.

Layer construction belongs to ``visualization.maps``; this component only
places a finished map object into the Streamlit layout.
"""

from __future__ import annotations

from typing import Any

import pydeck as pdk
import streamlit as st
from streamlit_folium import st_folium


def render_pydeck_map(deck: pdk.Deck, *, key: str, height: int = 520) -> None:
    """Render a pre-built PyDeck map.

    Args:
        deck: A fully constructed ``pydeck.Deck`` from the visualization layer.
        key: Unique Streamlit widget key.
        height: Map height in pixels.
    """
    st.pydeck_chart(deck, use_container_width=True, key=key, height=height)


def render_folium_map(folium_map: Any, *, key: str, height: int = 520) -> dict[str, Any]:
    """Render a pre-built Folium map and return interaction state.

    Args:
        folium_map: A fully constructed ``folium.Map`` from the visualization layer.
        key: Unique Streamlit widget key.
        height: Map height in pixels.

    Returns:
        The interaction dictionary returned by ``streamlit_folium.st_folium``
        (e.g. last clicked coordinates), for controllers that need it.
    """
    return st_folium(folium_map, use_container_width=True, height=height, key=key)


def render_map_placeholder(message: str = "Map data is not available yet.") -> None:
    """Render a placeholder message in place of a map with no data.

    Args:
        message: The message to display.
    """
    st.info(message)
