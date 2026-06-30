"""Decision Support page controller.

Per SAD Section 19 rule 6, this controller is the only entry point through
which the Decision Support page may trigger ``core.decision`` risk/
recommendation logic. That logic lands in a later implementation phase.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.registry.region_registry import get_region_registry
from utils.exceptions import ClimateTwinError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DecisionSupportViewModel:
    """Display-ready data the Decision Support page needs to render.

    Attributes:
        region_name: Human-readable name of the selected region.
        risk_assessments_available: Whether risk assessments could be computed.
        status_message: User-facing message when assessments are unavailable.
    """

    region_name: str
    risk_assessments_available: bool
    status_message: str | None = None


def get_decision_support_view(region_id: str) -> DecisionSupportViewModel:
    """Build the view model for the Decision Support page.

    Args:
        region_id: Identifier of the currently selected region.

    Returns:
        A :class:`DecisionSupportViewModel` ready for rendering by ``app.pages``.
    """
    registry = get_region_registry()
    try:
        region = registry.get(region_id)
    except ClimateTwinError as exc:
        logger.warning("Decision controller failed to resolve region '%s': %s", region_id, exc)
        return DecisionSupportViewModel(
            region_name=region_id,
            risk_assessments_available=False,
            status_message="Selected region could not be resolved.",
        )

    return DecisionSupportViewModel(
        region_name=region.name,
        risk_assessments_available=False,
        status_message=(
            "The risk and recommendation engines (core.decision) are "
            "implemented in a later delivery phase, depending on AI "
            "predictions which themselves depend on assimilated "
            "ClimateState data. This controller is the fixed integration "
            "point those engines will be wired into."
        ),
    )
