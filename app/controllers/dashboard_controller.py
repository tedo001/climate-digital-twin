"""Dashboard page controller.

Per SAD Section 19 rule 6, AI/climate/simulation are never called directly
from Streamlit pages — only through controllers like this one. The climate
intelligence layer (``climate.state_manager``) lands in a later
implementation phase; until then this controller degrades gracefully
rather than crashing the page, consistent with the SAD Section 16 fallback
policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.components.kpi_cards import KPICardData
from core.registry.region_registry import get_region_registry
from utils.exceptions import ClimateTwinError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DashboardViewModel:
    """Display-ready data the Dashboard page needs to render.

    Attributes:
        region_name: Human-readable name of the selected region.
        kpi_cards: Pre-formatted KPI cards summarizing current conditions.
        state_available: Whether a live ``ClimateState`` could be loaded.
        status_message: User-facing message when state is unavailable.
    """

    region_name: str
    kpi_cards: list[KPICardData]
    state_available: bool
    status_message: str | None = None


def get_dashboard_view(region_id: str) -> DashboardViewModel:
    """Build the view model for the Dashboard page.

    Args:
        region_id: Identifier of the currently selected region.

    Returns:
        A :class:`DashboardViewModel` ready for rendering by ``app.pages``.
    """
    registry = get_region_registry()
    try:
        region = registry.get(region_id)
    except ClimateTwinError as exc:
        logger.warning("Dashboard controller failed to resolve region '%s': %s", region_id, exc)
        return DashboardViewModel(
            region_name=region_id,
            kpi_cards=[],
            state_available=False,
            status_message="Selected region could not be resolved.",
        )

    # The Climate Intelligence layer (climate.state_manager.get_current_state)
    # is implemented in a later phase. Until it lands, the dashboard reports
    # its absence explicitly rather than fabricating numbers.
    return DashboardViewModel(
        region_name=region.name,
        kpi_cards=[],
        state_available=False,
        status_message=(
            "No assimilated ClimateState is available yet. "
            "Data ingestion and assimilation are implemented in the next "
            "delivery phase; once a state is persisted, live KPIs will "
            "appear here automatically."
        ),
    )
