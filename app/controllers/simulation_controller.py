"""Simulation page controller.

Per SAD Section 4 step 12, this controller is the only entry point through
which the Simulation page may trigger ``simulation.simulation_runner``. The
simulation layer lands in a later implementation phase.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.registry.region_registry import get_region_registry
from utils.exceptions import ClimateTwinError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SimulationViewModel:
    """Display-ready data the Simulation page needs to render.

    Attributes:
        region_name: Human-readable name of the selected region.
        scenario_available: Whether an active scenario has results to show.
        status_message: User-facing message when no scenario is active.
    """

    region_name: str
    scenario_available: bool
    status_message: str | None = None


def get_simulation_view(region_id: str) -> SimulationViewModel:
    """Build the view model for the Simulation page.

    Args:
        region_id: Identifier of the currently selected region.

    Returns:
        A :class:`SimulationViewModel` ready for rendering by ``app.pages``.
    """
    registry = get_region_registry()
    try:
        region = registry.get(region_id)
    except ClimateTwinError as exc:
        logger.warning("Simulation controller failed to resolve region '%s': %s", region_id, exc)
        return SimulationViewModel(
            region_name=region_id,
            scenario_available=False,
            status_message="Selected region could not be resolved.",
        )

    return SimulationViewModel(
        region_name=region.name,
        scenario_available=False,
        status_message=(
            "The Simulation layer (scenario_manager, parameter_engine, "
            "state_modifier, impact_calculator) is implemented in a later "
            "delivery phase. This controller is the fixed integration point "
            "the Simulation page will call once that layer lands."
        ),
    )
