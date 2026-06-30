"""Centralized Streamlit session state wrapper.

Per SAD Section 4 step 8, this module owns initialization and typed access
to ``st.session_state`` so no other module reads/writes session state keys
directly by string literal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from config.constants import DEFAULT_FORECAST_HORIZON_DAYS
from core.registry.region_registry import get_region_registry

_SESSION_KEYS = (
    "selected_region_id",
    "selected_time_window_days",
    "active_scenario_id",
    "forecast_horizon_days",
    "current_state_id",
)


@dataclass(slots=True)
class SessionDefaults:
    """Default values applied to session state on first run.

    Attributes:
        selected_region_id: Region selected in the sidebar (defaults to all-India).
        selected_time_window_days: Lookback window for historical views.
        active_scenario_id: Currently active simulation scenario, if any.
        forecast_horizon_days: Default AI prediction horizon.
        current_state_id: ``ClimateState.state_id`` currently in view.
    """

    selected_region_id: str = "IN"
    selected_time_window_days: int = 30
    active_scenario_id: str | None = None
    forecast_horizon_days: int = DEFAULT_FORECAST_HORIZON_DAYS
    current_state_id: str | None = None


class SessionManager:
    """Typed accessor over ``st.session_state`` for application-level state.

    All reads/writes to navigation, selection, and scenario state should go
    through this class rather than touching ``st.session_state`` directly,
    keeping ``app.pages`` free of state-management logic.
    """

    def __init__(self, defaults: SessionDefaults | None = None) -> None:
        self._defaults = defaults or SessionDefaults()

    def initialize(self) -> None:
        """Populate ``st.session_state`` with defaults if not already set.

        Idempotent: safe to call on every page render.
        """
        if "selected_region_id" not in st.session_state:
            st.session_state["selected_region_id"] = self._defaults.selected_region_id
        if "selected_time_window_days" not in st.session_state:
            st.session_state["selected_time_window_days"] = self._defaults.selected_time_window_days
        if "active_scenario_id" not in st.session_state:
            st.session_state["active_scenario_id"] = self._defaults.active_scenario_id
        if "forecast_horizon_days" not in st.session_state:
            st.session_state["forecast_horizon_days"] = self._defaults.forecast_horizon_days
        if "current_state_id" not in st.session_state:
            st.session_state["current_state_id"] = self._defaults.current_state_id

    @property
    def selected_region_id(self) -> str:
        """The currently selected region identifier."""
        return str(st.session_state.get("selected_region_id", self._defaults.selected_region_id))

    @selected_region_id.setter
    def selected_region_id(self, value: str) -> None:
        registry = get_region_registry()
        registry.get(value)  # raises ConfigurationError if invalid
        st.session_state["selected_region_id"] = value

    @property
    def selected_time_window_days(self) -> int:
        """The currently selected historical lookback window, in days."""
        return int(
            st.session_state.get(
                "selected_time_window_days", self._defaults.selected_time_window_days
            )
        )

    @selected_time_window_days.setter
    def selected_time_window_days(self, value: int) -> None:
        if value <= 0:
            raise ValueError("selected_time_window_days must be positive")
        st.session_state["selected_time_window_days"] = value

    @property
    def active_scenario_id(self) -> str | None:
        """The currently active simulation scenario identifier, if any."""
        return st.session_state.get("active_scenario_id")

    @active_scenario_id.setter
    def active_scenario_id(self, value: str | None) -> None:
        st.session_state["active_scenario_id"] = value

    @property
    def forecast_horizon_days(self) -> int:
        """The currently selected AI prediction horizon, in days."""
        return int(
            st.session_state.get("forecast_horizon_days", self._defaults.forecast_horizon_days)
        )

    @forecast_horizon_days.setter
    def forecast_horizon_days(self, value: int) -> None:
        if value <= 0:
            raise ValueError("forecast_horizon_days must be positive")
        st.session_state["forecast_horizon_days"] = value

    @property
    def current_state_id(self) -> str | None:
        """The ``ClimateState.state_id`` currently in view, if loaded."""
        return st.session_state.get("current_state_id")

    @current_state_id.setter
    def current_state_id(self, value: str | None) -> None:
        st.session_state["current_state_id"] = value

    def as_dict(self) -> dict[str, Any]:
        """Snapshot all tracked session keys as a plain dictionary.

        Returns:
            A dictionary of the current values for every tracked session key.
        """
        return {key: st.session_state.get(key) for key in _SESSION_KEYS}


def get_session_manager() -> SessionManager:
    """Construct a :class:`SessionManager` and ensure it is initialized.

    Returns:
        An initialized :class:`SessionManager` instance.
    """
    manager = SessionManager()
    manager.initialize()
    return manager
