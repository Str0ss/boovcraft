"""Handle ownership map — Tier 2 foundation.

Walks every `0x16` (selection) and `0x17` (hotkey + units) action in
the parser-output's events stream in chronological order, attributing
each unit handle to the player who first selected it.

The first player to select a handle is its `owner`. Subsequent
selections by other players append to `coControlledBy` (used as
evidence for shared-control reporting; not used in centroid math —
the original owner is preserved for centroid attribution).

Neutral / creep handles (owners 12 / 15) are excluded from the map —
their selections do happen in observer-style replays, but we do not
treat neutral creature handles as belonging to any player.

Pure stdlib; no external imports.

See:
  - specs/006-team-cohesion-analysis/data-model.md § HandleOwnership
  - specs/006-team-cohesion-analysis/plan.md § Heuristic decisions
  - specs/006-team-cohesion-analysis/contracts/output-shape.md § structural invariants
"""

from __future__ import annotations

from typing import Any, NamedTuple

from .events import (
    ACT_HOTKEY_GROUP,
    ACT_SELECTION,
    NEUTRAL_SLOT_IDS,
    iter_command_actions,
)

Handle = tuple[int, int]


class OwnershipRow(NamedTuple):
    """Per-handle ownership record."""

    owner: int
    first_seen_event_idx: int
    co_controlled_by: tuple[int, ...]


def _normalize_handle(units_entry: Any) -> Handle | None:
    """Convert one ``units`` entry from a 0x16/0x17 action into a (hi, lo) tuple.

    w3gjs emits selection units as ``[hi, lo]`` lists. Returns None for
    malformed entries (non-list, wrong length, non-integer halves).
    """
    if not isinstance(units_entry, list) or len(units_entry) != 2:
        return None
    try:
        return (int(units_entry[0]), int(units_entry[1]))
    except (TypeError, ValueError):
        return None


def build_ownership_map(parser_output: dict[str, Any]) -> dict[Handle, OwnershipRow]:
    """Walk the parser-output event stream and return handle → OwnershipRow.

    Determinism: handle insertion order in the returned dict mirrors
    the chronological-first-selection order. Re-running on the same
    input produces the same dict (Python 3.7+ insertion-order
    guarantee).
    """
    ownership: dict[Handle, OwnershipRow] = {}
    event_idx = 0

    for _time_ms, player_id, action in iter_command_actions(parser_output):
        action_id = action.get("id")
        if action_id not in (ACT_SELECTION, ACT_HOTKEY_GROUP):
            event_idx += 1
            continue
        event_idx += 1

        if player_id in NEUTRAL_SLOT_IDS:
            continue

        units = action.get("units") or []
        for raw_handle in units:
            handle = _normalize_handle(raw_handle)
            if handle is None:
                continue
            existing = ownership.get(handle)
            if existing is None:
                ownership[handle] = OwnershipRow(
                    owner=player_id,
                    first_seen_event_idx=event_idx,
                    co_controlled_by=(),
                )
            elif existing.owner != player_id and player_id not in existing.co_controlled_by:
                ownership[handle] = OwnershipRow(
                    owner=existing.owner,
                    first_seen_event_idx=existing.first_seen_event_idx,
                    co_controlled_by=existing.co_controlled_by + (player_id,),
                )

    return ownership


def owner_of(ownership: dict[Handle, OwnershipRow], handle: Handle) -> int | None:
    """Return the owning slot id of ``handle``, or None if not in the map."""
    row = ownership.get(handle)
    return row.owner if row is not None else None
