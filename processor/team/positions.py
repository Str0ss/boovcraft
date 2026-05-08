"""Position state machine — Tier 2 foundation.

Walks the parser-output event stream and maintains, for each unit
handle, its last-commanded position in WC3 map units. Used by
``processor/team/centroids.py`` to compute per-player army centroids
at battle start.

The state machine is "last-commanded" — it does NOT model unit walk
time, pathfinding, or in-flight motion. When a player issues a
position-targeted command (``0x11`` / ``0x12`` / ``0x14``) with a
selection active, every handle in the active selection has its
position updated to the command's target coordinates. This is an
approximation; see ``research.md § R2`` for tier-2 vs. tier-3 trade-off.

Special handling:
  - ``0x10`` (NoTarget) build/train commands: the *worker's* current
    position becomes the implied position of the new building. The
    building's eventual handle is tied to the worker via subsequent
    ``0x16`` selection events.
  - ``0x13`` (give-item) updates the giver's selected handles' positions
    to ``target`` (the give location).

Pure stdlib; no external imports.

See:
  - specs/006-team-cohesion-analysis/data-model.md § PositionState
  - specs/006-team-cohesion-analysis/plan.md § Heuristic decisions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .events import (
    ACT_GIVE_ITEM,
    ACT_HOTKEY_GROUP,
    ACT_NO_TARGET,
    ACT_SELECTION,
    ACT_TARGET_POSITION,
    ACT_TARGET_POSITION_AND_UNIT,
    ACT_TWO_TARGETS,
    NEUTRAL_SLOT_IDS,
    iter_command_actions,
)
from .ownership import Handle, OwnershipRow, _normalize_handle


@dataclass(frozen=True)
class PositionRecord:
    """One handle's last-known position."""

    owner: int
    x: float
    y: float
    last_updated_ms: int
    source: str  # "command" | "build" | "selection"


@dataclass
class PositionState:
    """Mutable position state during a single ``analyze.py`` run.

    Maintains a per-handle ``PositionRecord`` map plus a per-player
    ``ActiveSelection`` tracking the most recent selection. Both are
    updated by ``step()`` on each event.
    """

    by_handle: dict[Handle, PositionRecord] = field(default_factory=dict)
    active_selection: dict[int, list[Handle]] = field(default_factory=dict)
    # Handles in flight as build orders, keyed by issuing player slot.
    # When a 0x10 build action fires, the worker's current position is
    # remembered; the next selection event that introduces a new handle
    # owned by this player picks up the position. This is a coarse
    # heuristic — see the worker-handoff invariant in tests.
    _pending_build_position: dict[int, tuple[float, float, int]] = field(default_factory=dict)

    def step(
        self,
        time_ms: int,
        player_id: int,
        action: dict[str, Any],
        ownership: dict[Handle, OwnershipRow],
    ) -> None:
        """Process one action; update ``by_handle`` and ``active_selection``."""
        if player_id in NEUTRAL_SLOT_IDS:
            return

        action_id = action.get("id")

        # Selection events update the active selection set; they also
        # may carry build-handoff handles for buildings just constructed.
        if action_id in (ACT_SELECTION, ACT_HOTKEY_GROUP):
            handles = []
            for raw in action.get("units") or []:
                h = _normalize_handle(raw)
                if h is not None:
                    handles.append(h)
            self.active_selection[player_id] = handles

            # Worker-handoff: if there is a pending build for this player,
            # any handle in this new selection that is owned by this
            # player AND is not already in by_handle gets the pending
            # position.
            pending = self._pending_build_position.pop(player_id, None)
            if pending is not None:
                bx, by_, bt = pending
                for h in handles:
                    if h not in self.by_handle and ownership.get(h) and ownership[h].owner == player_id:
                        self.by_handle[h] = PositionRecord(
                            owner=player_id, x=bx, y=by_, last_updated_ms=bt, source="build"
                        )
            return

        # Position-bearing commands update every active-selection handle.
        target = self._extract_target(action_id, action)
        if target is None:
            # 0x10 build orders carry no target — but the selected
            # worker's current position becomes the pending build
            # position. (Buildings stamped at the worker's spot, more
            # or less.)
            if action_id == ACT_NO_TARGET:
                worker_pos = self._first_selection_position(player_id)
                if worker_pos is not None:
                    wx, wy = worker_pos
                    self._pending_build_position[player_id] = (wx, wy, time_ms)
            return

        x, y = target
        for handle in self.active_selection.get(player_id, ()):
            owner_row = ownership.get(handle)
            if owner_row is None or owner_row.owner != player_id:
                # Handle in active selection but not owned by this player —
                # that is a co-control case; we do not update its position
                # because the original owner is the source of truth.
                continue
            self.by_handle[handle] = PositionRecord(
                owner=player_id, x=x, y=y, last_updated_ms=time_ms, source="command"
            )

        # Give-item: the receiving handle's position is also touched.
        # Note: the receiving hero handle (action["unit"]) is the ally
        # hero. We do NOT update its position — that hero is owned by
        # someone else and updates only via their commands.

    def _first_selection_position(self, player_id: int) -> tuple[float, float] | None:
        """Best-effort position of the player's currently-selected unit.

        Used as the worker's position when a build order fires.
        Returns the position of the first handle in the active
        selection that has a known position; None otherwise.
        """
        for handle in self.active_selection.get(player_id, ()):
            rec = self.by_handle.get(handle)
            if rec is not None:
                return rec.x, rec.y
        return None

    @staticmethod
    def _extract_target(action_id: int, action: dict[str, Any]) -> tuple[float, float] | None:
        """Pick the position-target from an action, or return None."""
        if action_id in (ACT_TARGET_POSITION, ACT_TARGET_POSITION_AND_UNIT, ACT_GIVE_ITEM):
            target = action.get("target")
            if isinstance(target, list) and len(target) == 2:
                try:
                    return float(target[0]), float(target[1])
                except (TypeError, ValueError):
                    return None
        elif action_id == ACT_TWO_TARGETS:
            target = action.get("targetA")
            if isinstance(target, list) and len(target) == 2:
                try:
                    return float(target[0]), float(target[1])
                except (TypeError, ValueError):
                    return None
        return None

    # --- read-side helpers -----------------------------------------------

    def handles_for(self, slot: int) -> Iterable[Handle]:
        """Yield every handle currently owned by ``slot`` with a known position."""
        for handle, record in self.by_handle.items():
            if record.owner == slot:
                yield handle

    def centroid_at(
        self,
        slot: int,
        lookback_from_ms: int,
        lookback_to_ms: int,
    ) -> tuple[float, float] | None:
        """Arithmetic mean of positions for ``slot``'s handles updated in the
        ``[lookback_from_ms, lookback_to_ms]`` time window.

        Returns ``None`` when no handle in that window has a position
        (the ``Centroid.source = "missing"`` case in the data model).
        """
        xs: list[float] = []
        ys: list[float] = []
        for record in self.by_handle.values():
            if record.owner != slot:
                continue
            if not (lookback_from_ms <= record.last_updated_ms <= lookback_to_ms):
                continue
            xs.append(record.x)
            ys.append(record.y)
        if not xs:
            return None
        return sum(xs) / len(xs), sum(ys) / len(ys)


def run_position_state(
    parser_output: dict[str, Any],
    ownership: dict[Handle, OwnershipRow],
) -> PositionState:
    """Walk the full event stream and return the final ``PositionState``.

    Determinism: same input + same ownership → same final state.
    """
    state = PositionState()
    for time_ms, player_id, action in iter_command_actions(parser_output):
        state.step(time_ms, player_id, action, ownership)
    return state
