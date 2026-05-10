"""Centroid timeline — pre-computed per-bucket centroids + combat-unit
food / count for the Map-tab scrubber (feature 009).

Walks the same Tier-2 PositionState the rest of feature 007 uses, but
samples it at fixed intervals (5s) for the duration of the match. Each
bucket carries one centroid record per non-AI player slot, augmented
with cumulative combat-unit food and count.

Pure stdlib.

See specs/009-map-tab-centroid-scrubber/spec.md and research.md for
rationale.
"""

from __future__ import annotations

from typing import Any

from .events import NEUTRAL_SLOT_IDS
from .ownership import Handle, OwnershipRow
from .positions import PositionState

# --- Heuristic constants (research.md § R3 / R5) ---------------------------

BUCKET_WIDTH_MS = 5_000             # Same coarseness as battle-window buckets
CENTROID_LOOKBACK_MS = 60_000       # Inherited from team/centroids.py

# Workers are excluded from combat-unit tallies — see research.md § R3.
WORKER_IDS = frozenset({
    "hpea",  # Peasant   (Human)
    "opeo",  # Peon      (Orc)
    "uaco",  # Acolyte   (Undead)
    "ewsp",  # Wisp      (Night Elf)
})


def compute_centroid_timeline(
    parser_output: dict[str, Any],
    position_state: PositionState,
    unit_costs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build the ``team.centroidTimeline`` block.

    Returns the dict shape from spec FR-001:

      {
        "bucketWidthMs": 5000,
        "buckets": [
          { "tMs": 0, "centroids": [{slot, x, y, source, combatFood, combatUnitCount}, ...] },
          ...
        ]
      }
    """
    duration_ms = int(parser_output.get("duration", 0) or 0)
    if duration_ms <= 0:
        return {"bucketWidthMs": BUCKET_WIDTH_MS, "buckets": []}

    n_buckets = (duration_ms // BUCKET_WIDTH_MS) + 1

    # Pre-build per-player combat-unit production events, sorted by time.
    # Combat units come from two sources:
    #   1. production.units.order — Grunts, Ghouls, Knights, etc.
    #   2. players[i].heroes — heroes (summoned at altar; appear when first
    #      ability is learned, which is at level 1 ≈ summon time).
    #
    # Both source-shapes carry a time field but use different keys:
    # parser-output uses {time, value} while analyzer-output uses
    # {timeMs, id}. Handle both for robustness.
    player_units: dict[int, list[tuple[int, str]]] = {}
    for player in parser_output.get("players", []) or []:
        slot = player.get("id")
        if not isinstance(slot, int) or slot in NEUTRAL_SLOT_IDS:
            continue

        events: list[tuple[int, str]] = []

        # Source 1 — production.units.order (Grunts, Ghouls, etc.)
        units_order = (player.get("units") or {}).get("order") or []
        for entry in units_order:
            t_ms = entry.get("timeMs")
            if t_ms is None:
                t_ms = entry.get("ms")
            uid = entry.get("id")
            if uid is None:
                uid = entry.get("value")
            if isinstance(t_ms, (int, float)) and isinstance(uid, str):
                events.append((int(t_ms), uid))

        # Source 2 — heroes (summon time ≈ first ability learn time)
        for hero in player.get("heroes", []) or []:
            hero_id = hero.get("id")
            if not isinstance(hero_id, str) or hero_id == "UNKN":
                continue
            ability_order = hero.get("abilityOrder") or []
            summon_ms: int | None = None
            for ab in ability_order:
                # Parser-output uses 'time'; analyzer-output uses 'timeMs'.
                t = ab.get("time")
                if t is None:
                    t = ab.get("timeMs")
                if isinstance(t, (int, float)):
                    if summon_ms is None or int(t) < summon_ms:
                        summon_ms = int(t)
            if summon_ms is not None:
                events.append((summon_ms, hero_id))

        events.sort(key=lambda x: x[0])
        player_units[slot] = events

    # Cursor + cumulative state for the streaming combat-food walk
    cursor: dict[int, int] = {slot: 0 for slot in player_units}
    cumulative_food: dict[int, int] = {slot: 0 for slot in player_units}
    cumulative_count: dict[int, int] = {slot: 0 for slot in player_units}

    buckets: list[dict[str, Any]] = []
    for i in range(n_buckets):
        t_ms = i * BUCKET_WIDTH_MS

        # Advance the cursors for each player up to t_ms
        for slot, events in player_units.items():
            cur = cursor[slot]
            while cur < len(events) and events[cur][0] <= t_ms:
                _et, uid = events[cur]
                if uid not in WORKER_IDS:
                    cost = unit_costs.get(uid) or {}
                    cumulative_food[slot] += int(cost.get("supply", 0) or 0)
                    cumulative_count[slot] += 1
                cur += 1
            cursor[slot] = cur

        # Per-slot centroid + cumulative tallies. Three-tier fallback so
        # every player has a visible position at every bucket from t=0
        # onward — even before their first commanded action (FR amended
        # per user feedback 2026-05-08):
        #   1. Fresh 60-second window centroid → "commanded"
        #   2. Last-known position before t (any age) → "stale"
        #   3. Forward look — first commanded position at or after t,
        #      i.e., "where the player will appear soon" → "starting"
        #   4. None → "missing" (only when player never commands ever)
        centroids: list[dict[str, Any]] = []
        for slot in sorted(player_units.keys()):
            lookback_from = max(0, t_ms - CENTROID_LOOKBACK_MS)
            c = position_state.centroid_at(slot, lookback_from, t_ms)
            source = "missing"
            x: float | None = None
            y: float | None = None
            if c is not None:
                x, y, source = c[0], c[1], "commanded"
            else:
                # Fallback 1: most recently commanded position before t.
                most_recent = _last_known_position(position_state, slot, t_ms)
                if most_recent is not None:
                    x, y, source = most_recent[0], most_recent[1], "stale"
                else:
                    # Fallback 2: forward look — earliest future commanded
                    # position. The player hasn't moved yet, but here is
                    # roughly where they'll first appear.
                    earliest_future = _earliest_future_position(
                        position_state, slot, t_ms,
                    )
                    if earliest_future is not None:
                        x, y, source = earliest_future[0], earliest_future[1], "starting"

            centroids.append({
                "slot": slot, "x": x, "y": y, "source": source,
                "combatFood": cumulative_food[slot],
                "combatUnitCount": cumulative_count[slot],
            })

        buckets.append({"tMs": t_ms, "centroids": centroids})

    return {"bucketWidthMs": BUCKET_WIDTH_MS, "buckets": buckets}


def _earliest_future_position(
    position_state: PositionState,
    slot: int,
    after_t_ms: int,
) -> tuple[float, float] | None:
    """Centroid over each owned handle whose most-recent commanded
    position lies at or after ``after_t_ms``.

    Used as a third-tier fallback: when the player hasn't issued any
    command yet at time t, peek forward to find roughly where they'll
    first appear (their starting spot, give-or-take). Source becomes
    ``"starting"`` for these placements.
    """
    xs: list[float] = []
    ys: list[float] = []
    for record in position_state.by_handle.values():
        if record.owner != slot:
            continue
        if record.last_updated_ms < after_t_ms:
            continue
        xs.append(record.x)
        ys.append(record.y)
    if not xs:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _last_known_position(
    position_state: PositionState,
    slot: int,
    before_t_ms: int,
) -> tuple[float, float] | None:
    """Centroid over each owned handle's most-recent commanded position
    BEFORE ``before_t_ms``, regardless of how stale.

    Used as a fallback when the 60-second window centroid is empty —
    keeps a player visible on the map after a period of inactivity.
    """
    xs: list[float] = []
    ys: list[float] = []
    for record in position_state.by_handle.values():
        if record.owner != slot:
            continue
        if record.last_updated_ms > before_t_ms:
            continue
        xs.append(record.x)
        ys.append(record.y)
    if not xs:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)
