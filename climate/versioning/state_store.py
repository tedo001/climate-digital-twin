"""Durable persistence of :class:`ClimateState` snapshots.

Implements the storage split of SAD Section 5.4 for assimilated states: the
lightweight version/lineage row lives in the DuckDB ``historical_states`` table,
while the serialized state payload is written as JSON under
:data:`config.paths.STATE_SNAPSHOTS_DIR` and referenced by ``payload_path``.
States are immutable, so a snapshot is written once and read back by id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from climate.versioning.serialization import state_from_dict, state_to_dict
from config.paths import STATE_SNAPSHOTS_DIR
from core.models.climate_state import ClimateState
from storage.db.duckdb_connector import DuckDBConnector
from utils.exceptions import StateNotFoundError, StatePersistenceError
from utils.logger import get_logger

logger = get_logger(__name__)


class StateStore:
    """Persist and retrieve immutable ClimateState snapshots.

    Args:
        connector: DuckDB connector (a default is created if omitted).
        snapshots_dir: Directory for serialized JSON payloads.
    """

    def __init__(
        self,
        connector: DuckDBConnector | None = None,
        snapshots_dir: Path = STATE_SNAPSHOTS_DIR,
    ) -> None:
        self._db = connector or DuckDBConnector()
        self._snapshots_dir = Path(snapshots_dir)
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: ClimateState) -> Path:
        """Persist a state snapshot (payload file + version row).

        Args:
            state: The immutable state to persist.

        Returns:
            The path of the written JSON payload.

        Raises:
            StatePersistenceError: If the payload cannot be serialized or written.
        """
        payload_path = self._snapshots_dir / f"{state.state_id}.json"
        try:
            payload_path.write_text(
                json.dumps(state_to_dict(state), indent=2, sort_keys=True), encoding="utf-8"
            )
        except (OSError, TypeError, ValueError) as exc:
            raise StatePersistenceError(
                "Failed to serialize ClimateState payload",
                details={"state_id": state.state_id, "error": str(exc)},
            ) from exc

        self._db.execute(
            "INSERT OR REPLACE INTO historical_states "
            "(state_id, parent_version_id, valid_time, created_at, state_type, "
            "payload_path, region_ids) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                state.state_id,
                state.parent_version_id,
                state.valid_time,
                state.created_at,
                state.state_type.value,
                str(payload_path),
                json.dumps(list(state.region_ids())),
            ),
        )
        logger.info("Persisted ClimateState %s → %s", state.state_id, payload_path)
        return payload_path

    def load(self, state_id: str) -> ClimateState:
        """Load a persisted state snapshot by id.

        Args:
            state_id: The state's UUID.

        Returns:
            The reconstructed :class:`ClimateState`.

        Raises:
            StateNotFoundError: If no snapshot with that id exists.
            StatePersistenceError: If the payload file is missing or unreadable.
        """
        rows = self._db.fetch_all(
            "SELECT payload_path FROM historical_states WHERE state_id = ?", (state_id,)
        )
        if not rows:
            raise StateNotFoundError("No persisted state with that id", details={"id": state_id})
        return self._load_payload(str(rows[0][0]), state_id)

    def latest(self) -> ClimateState | None:
        """Return the most recent persisted state, or ``None`` if the store is empty.

        Recency is ordered by ``valid_time`` then ``created_at``.

        Returns:
            The newest :class:`ClimateState`, or ``None``.
        """
        rows = self._db.fetch_all(
            "SELECT state_id, payload_path FROM historical_states "
            "ORDER BY valid_time DESC, created_at DESC LIMIT 1"
        )
        if not rows:
            return None
        return self._load_payload(str(rows[0][1]), str(rows[0][0]))

    def exists(self, state_id: str) -> bool:
        """Return whether a snapshot with ``state_id`` is persisted."""
        rows = self._db.fetch_all("SELECT 1 FROM historical_states WHERE state_id = ?", (state_id,))
        return bool(rows)

    def count(self) -> int:
        """Return the number of persisted state snapshots."""
        rows = self._db.fetch_all("SELECT COUNT(*) FROM historical_states")
        return int(cast(int, rows[0][0])) if rows else 0

    def _load_payload(self, payload_path: str, state_id: str) -> ClimateState:
        """Read and deserialize a payload file."""
        path = Path(payload_path)
        if not path.exists():
            raise StatePersistenceError(
                "State payload file missing",
                details={"state_id": state_id, "path": payload_path},
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return state_from_dict(data)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise StatePersistenceError(
                "Failed to read ClimateState payload",
                details={"state_id": state_id, "error": str(exc)},
            ) from exc
