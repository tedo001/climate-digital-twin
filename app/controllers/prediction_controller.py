"""Prediction page controller.

Per SAD Section 4 step 11 and Section 19 rule 6, this controller is the only
entry point through which the Prediction page may trigger AI inference. The
AI layer (``ai.prediction.prediction_engine``) lands in a later
implementation phase; this controller currently reports that state
transparently rather than fabricating predictions.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.registry.region_registry import get_region_registry
from utils.exceptions import ClimateTwinError
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PredictionViewModel:
    """Display-ready data the Prediction page needs to render.

    Attributes:
        region_name: Human-readable name of the selected region.
        horizon_days: The requested forecast horizon, in days.
        predictions_available: Whether any predictions could be generated.
        status_message: User-facing message when predictions are unavailable.
    """

    region_name: str
    horizon_days: int
    predictions_available: bool
    status_message: str | None = None


def get_prediction_view(region_id: str, horizon_days: int) -> PredictionViewModel:
    """Build the view model for the Prediction page.

    Args:
        region_id: Identifier of the currently selected region.
        horizon_days: Requested forecast horizon, in days.

    Returns:
        A :class:`PredictionViewModel` ready for rendering by ``app.pages``.
    """
    registry = get_region_registry()
    try:
        region = registry.get(region_id)
    except ClimateTwinError as exc:
        logger.warning("Prediction controller failed to resolve region '%s': %s", region_id, exc)
        return PredictionViewModel(
            region_name=region_id,
            horizon_days=horizon_days,
            predictions_available=False,
            status_message="Selected region could not be resolved.",
        )

    return PredictionViewModel(
        region_name=region.name,
        horizon_days=horizon_days,
        predictions_available=False,
        status_message=(
            "The AI prediction engine and model checkpoints are implemented "
            "in a later delivery phase. Once trained checkpoints are "
            "registered in config/model_registry.yaml, this page will call "
            "ai.prediction.prediction_engine.predict() through this "
            "controller and render real forecasts."
        ),
    )
