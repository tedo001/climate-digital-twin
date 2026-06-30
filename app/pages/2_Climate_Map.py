"""Climate Map page: spatial visualization of climate variables across India.

Per SAD Section 19 rule 5, this module contains rendering calls only.
"""

from __future__ import annotations

import streamlit as st

from app.components.map_widget import render_map_placeholder
from app.components.sidebar import render_sidebar
from app.state.session_manager import get_session_manager
from config.constants import APP_NAME
from core.registry.region_registry import get_region_registry

st.set_page_config(page_title=f"Climate Map | {APP_NAME}", page_icon="🗺️", layout="wide")

session = get_session_manager()
render_sidebar(session)

st.title("🗺️ Climate Map")
st.caption("Spatial view of climate variables across India's states and districts.")

region = get_region_registry().get(session.selected_region_id)
st.subheader(region.name)
st.write(
    f"Bounding box: ({region.bounding_box.min_lat:.2f}, {region.bounding_box.min_lon:.2f}) "
    f"to ({region.bounding_box.max_lat:.2f}, {region.bounding_box.max_lon:.2f})"
)

render_map_placeholder(
    "Map layers depend on assimilated ClimateState raster data, which is "
    "produced by the Data Ingestion and Climate Intelligence layers in a "
    "later delivery phase. Once available, visualization.maps.india_map_builder "
    "will render PyDeck/Folium layers here through this page."
)
