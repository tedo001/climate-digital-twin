"""TwinStateManager: the single writer to the digital twin's current state.

Per SAD Section 5.5 this is the *only* component that advances the "current
state" pointer. It wires the assimilation engine to durable persistence and
implements the *Update Logic* of SAD Section 9: freshly assimilated data only
creates a new immutable :class:`ClimateState` version when the change is
significant (a large enough variable delta) or enough time has elapsed;
otherwise it is buffered and the current version is retained.

Readers (AI, simulation, visualization) obtain immutable references via
:meth:`get_current_state` and never mutate them.
"""

from __future__ import annotations

from collections.abc import Sequence

from climate.assimilation.assimilation_engine import AssimilationEngine
from climate.versioning.state_store import StateStore
from config.constants import StateType
from core.models.climate_state import ClimateState
from utils.logger import get_logger

logger = get_logger(__name__)

_EPS = 1e-9


class TwinStateManager:
    """Own the current ClimateState, assimilating and persisting new versions.

    Args:
        engine: The assimilation engine (a default is created if omitted).
        store: The durable state store (a default is created if omitted).
        significant_delta_fraction: Minimum relative change in any shared
            variable that, on its own, justifies a new version.
        min_seconds_between_versions: Elapsed ``valid_time`` gap that justifies a
            new version regardless of magnitude.
    """

    def __init__(
        self,
        engine: AssimilationEngine | None = None,
        store: StateStore | None = None,
        *,
        significant_delta_fraction: float = 0.05,
        min_seconds_between_versions: float = 3600.0,
    ) -> None:
        self._engine = engine or AssimilationEngine()
        self._store = store or StateStore()
        self._significant_delta = significant_delta_fraction
        self._min_seconds = min_seconds_between_versions
        self._current: ClimateState | None = None

    def get_current_state(self) -> ClimateState | None:
        """Return the current in-memory state, or ``None`` if none is set."""
        return self._current

    def load_current_from_store(self) -> ClimateState | None:
        """Adopt the most recent persisted state as the current pointer.

        Returns:
            The loaded :class:`ClimateState`, or ``None`` if the store is empty.
        """
        self._current = self._store.latest()
        if self._current is not None:
            logger.info("Loaded current state %s from store", self._current.state_id)
        return self._current

    def update_state(
        self,
        source_states: Sequence[ClimateState],
        *,
        state_type: StateType = StateType.NOWCAST,
        force: bool = False,
    ) -> ClimateState:
        """Assimilate source states and, if warranted, commit a new version.

        Args:
            source_states: Per-source states to fuse.
            state_type: Lifecycle classification for the assimilated state.
            force: If ``True``, always commit even when the change is minor.

        Returns:
            The new committed state, or the retained current state if the change
            was below the significance threshold.
        """
        parent_id = self._current.state_id if self._current is not None else None
        candidate = self._engine.assimilate(
            source_states, state_type=state_type, parent_version_id=parent_id
        )

        if not force and self._current is not None and not self._is_significant(candidate):
            logger.info(
                "Assimilated update below significance threshold; buffering (keeping %s)",
                self._current.state_id,
            )
            return self._current

        return self.commit(candidate)

    def commit(self, state: ClimateState) -> ClimateState:
        """Persist a state and advance the current pointer to it.

        This is the single write path for the current-state pointer.

        Args:
            state: The state to persist and adopt as current.

        Returns:
            The committed state.
        """
        self._store.save(state)
        self._current = state
        logger.info("Committed new current state %s", state.state_id)
        return state

    def _is_significant(self, candidate: ClimateState) -> bool:
        """Decide whether ``candidate`` differs enough to warrant a new version."""
        current = self._current
        if current is None:
            return True

        try:
            elapsed = (candidate.valid_time - current.valid_time).total_seconds()
        except TypeError:
            # Mixed tz-aware/naive timestamps: treat as significant to be safe.
            return True
        if elapsed >= self._min_seconds:
            return True

        return self._max_relative_delta(current, candidate) >= self._significant_delta

    @staticmethod
    def _max_relative_delta(current: ClimateState, candidate: ClimateState) -> float:
        """Return the largest relative variable change between two states.

        A variable or region present in ``candidate`` but not ``current`` counts
        as an unbounded change (returns ``inf``), forcing a new version.
        """
        max_relative = 0.0
        for region_id in candidate.regions:
            for name, cand_var in candidate.variables.get(region_id, {}).items():
                current_var = current.get_variable(region_id, name)
                if current_var is None:
                    return float("inf")
                denominator = abs(current_var.value) + _EPS
                relative = abs(cand_var.value - current_var.value) / denominator
                max_relative = max(max_relative, relative)
        return max_relative
