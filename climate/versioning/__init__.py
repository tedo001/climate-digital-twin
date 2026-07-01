"""ClimateState versioning and durable snapshot persistence (SAD Section 5.3-5.4).

Exposes the persistent :class:`~climate.versioning.state_store.StateStore` and
the JSON (de)serialization helpers for ClimateState snapshot payloads.
"""

from __future__ import annotations

from climate.versioning.serialization import state_from_dict, state_to_dict
from climate.versioning.state_store import StateStore

__all__ = [
    "StateStore",
    "state_from_dict",
    "state_to_dict",
]
