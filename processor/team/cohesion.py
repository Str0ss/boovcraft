"""Tactical cohesion — focus fire dominant target + ping reactions.

Phase 3 implementation of FR-016 / FR-017 / FR-018.

Pure stdlib; no external imports.
"""

from __future__ import annotations

import math
from typing import Any

from .battles import BattleWindow
from .events import (
    ACT_MINIMAP_SIGNAL,
    ACT_TARGET_POSITION_AND_UNIT,
    NEUTRAL_SLOT_IDS,
    iter_command_actions,
)
from .ownership import Handle, OwnershipRow, _normalize_handle
from .positions import PositionState

# --- Heuristic constants (research.md § R3) ---------------------------------

MIN_RESPONSE_DELTA = 200          # WC3 map units
RESPONSE_WINDOW_MS = 15_000       # 15-s ping look-ahead


def compute_focus_fire(
    battle: BattleWindow,
    parser_output: dict[str, Any],
    ownership: dict[Handle, OwnershipRow],
) -> dict[str, Any] | None:
    """Compute dominant target + cohesion percent for one battle.

    Walks 0x12 actions inside [start_ms, end_ms] whose `object` handle
    is owned by an opposing-team slot. Aggregates by target handle;
    dominant = max-attacked. Returns None when no enemy-handle ownership
    is inferable in the window.
    """
    side_a = set(battle.sides["teamA"])
    side_b = set(battle.sides["teamB"])

    target_counts: dict[Handle, int] = {}
    contributing_actors: dict[int, int] = {}  # actor_slot → count

    for time_ms, player_id, action in iter_command_actions(parser_output):
        if time_ms < battle.start_ms or time_ms > battle.end_ms:
            if time_ms > battle.end_ms:
                break
            continue
        if action.get("id") != ACT_TARGET_POSITION_AND_UNIT:
            continue
        if player_id in NEUTRAL_SLOT_IDS:
            continue

        target_obj = action.get("object")
        if not isinstance(target_obj, list) or len(target_obj) != 2:
            continue
        target_handle = _normalize_handle(target_obj)
        if target_handle is None:
            continue
        target_row = ownership.get(target_handle)
        if target_row is None:
            continue
        target_slot = target_row.owner

        # PvP only — actor and target on opposing sides
        if player_id in side_a and target_slot in side_b:
            pass
        elif player_id in side_b and target_slot in side_a:
            pass
        else:
            continue

        target_counts[target_handle] = target_counts.get(target_handle, 0) + 1
        contributing_actors[player_id] = contributing_actors.get(player_id, 0) + 1

    if not target_counts:
        return None

    # Dominant target = handle with the most attacks
    dominant_handle, dominant_count = max(target_counts.items(), key=lambda kv: kv[1])
    dominant_row = ownership.get(dominant_handle)
    dominant_slot = dominant_row.owner if dominant_row else None

    total_attacks = sum(target_counts.values())
    cohesion_percent = 100.0 * dominant_count / total_attacks if total_attacks else 0.0

    contributing = sorted(
        [{"slot": s, "attackCount": c} for s, c in contributing_actors.items()],
        key=lambda d: -d["attackCount"],
    )

    return {
        "dominantTargetSlot":   dominant_slot,
        "dominantTargetEntity": {"id": "UNKN", "name": "UNKN", "unknown": True},
        "cohesionPercent":      cohesion_percent,
        "contributingPlayers":  contributing,
    }


def extract_pings(
    battle: BattleWindow,
    parser_output: dict[str, Any],
    position_state: PositionState,
    all_battles: list[BattleWindow],
) -> list[dict[str, Any]]:
    """Walk 0x68 events inside the battle window; emit Ping records.

    ``respondedBySlot`` per the formula:
      distance(centroid_at_t0, ping) - distance(centroid_at_t0+15s, ping) >= MIN_RESPONSE_DELTA

    ``engagedElsewhereSlot`` — slot was inside *some other* battle
    window's [start, end] at ping.timeMs.
    """
    out: list[dict[str, Any]] = []
    side_a = set(battle.sides["teamA"])
    side_b = set(battle.sides["teamB"])

    for time_ms, player_id, action in iter_command_actions(parser_output):
        if time_ms > battle.end_ms:
            break
        if time_ms < battle.start_ms:
            continue
        if action.get("id") != ACT_MINIMAP_SIGNAL:
            continue
        if player_id in NEUTRAL_SLOT_IDS:
            continue

        pos = action.get("pos")
        if not isinstance(pos, list) or len(pos) != 2:
            continue
        try:
            x, y = float(pos[0]), float(pos[1])
        except (TypeError, ValueError):
            continue

        # Determine which side the pinger is on; allies are the
        # other slots on that side.
        if player_id in side_a:
            allies = side_a - {player_id}
        elif player_id in side_b:
            allies = side_b - {player_id}
        else:
            allies = set()

        # Compute response classification per ally
        responded: list[int] = []
        engaged_elsewhere: list[int] = []
        for ally in sorted(allies):
            # Engaged elsewhere check
            in_other_battle = False
            for other in all_battles:
                if other.index == battle.index:
                    continue
                if other.start_ms <= time_ms <= other.end_ms:
                    if ally in other.sides.get("teamA", ()) or ally in other.sides.get("teamB", ()):
                        in_other_battle = True
                        break
            if in_other_battle:
                engaged_elsewhere.append(ally)
                continue
            # Response delta check
            c0 = position_state.centroid_at(ally, max(0, time_ms - 5000), time_ms)
            c1 = position_state.centroid_at(ally, time_ms, time_ms + RESPONSE_WINDOW_MS)
            if c0 is None or c1 is None:
                continue
            d0 = math.hypot(c0[0] - x, c0[1] - y)
            d1 = math.hypot(c1[0] - x, c1[1] - y)
            if d0 - d1 >= MIN_RESPONSE_DELTA:
                responded.append(ally)

        out.append({
            "fromSlot":            player_id,
            "x":                   x,
            "y":                   y,
            "timeMs":              time_ms,
            "duration":            action.get("duration", 0),
            "respondedBySlot":     responded,
            "engagedElsewhereSlot": engaged_elsewhere,
        })

    return out
