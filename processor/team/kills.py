"""Kill estimation + match-level KP%.

Phase 3 implementation of FR-019. v1 conservative: kills are inferred
from handle disappearance (selection silence ≥ 30 s post-engagement).
Damage-share kill-credit by attack-action share in 5-s pre-death
window.

Pure stdlib; no external imports.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .battles import BattleWindow
from .events import (
    ACT_HOTKEY_GROUP,
    ACT_SELECTION,
    ACT_TARGET_POSITION_AND_UNIT,
    NEUTRAL_SLOT_IDS,
    iter_command_actions,
)
from .ownership import Handle, OwnershipRow, _normalize_handle

# --- Heuristic constants (research.md § R3) ---------------------------------

PRE_DEATH_WINDOW_MS = 5_000   # 5-s window for damage-share attribution
DEATH_SILENCE_MS = 30_000     # handle silent for ≥ 30 s ⇒ death


def estimate_kills(
    battle: BattleWindow,
    parser_output: dict[str, Any],
    ownership: dict[Handle, OwnershipRow],
    unit_costs: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Estimate kills inside one battle window.

    Returns (kills_list, unattributed_count). ``unattributed_count`` is
    the number of handle-disappearances that had zero attack-action
    coverage in the pre-death window — these are NOT emitted but feed
    one match-level diagnostics.cohesionMetricGaps[] entry.

    v1 simplification: deriving handle-death from selection silence is
    inherently noisy. We are CONSERVATIVE — only emit kills with clear
    attribution. Phase 3+4 builds the per-battle TEI on top of this.
    """
    side_a = set(battle.sides["teamA"])
    side_b = set(battle.sides["teamB"])

    # Track last selection time per handle inside the battle window
    last_seen: dict[Handle, int] = {}
    # Track which side each handle's owner is on
    handle_side: dict[Handle, str] = {}

    # Collect attack actions — for kill-credit attribution we need
    # 0x12 actions targeting each handle in the window
    attacks_by_handle: dict[Handle, list[tuple[int, int]]] = defaultdict(list)

    for time_ms, player_id, action in iter_command_actions(parser_output):
        if time_ms > battle.end_ms + DEATH_SILENCE_MS:
            break
        if time_ms < battle.start_ms:
            continue

        action_id = action.get("id")
        if action_id in (ACT_SELECTION, ACT_HOTKEY_GROUP):
            for raw in action.get("units") or []:
                handle = _normalize_handle(raw)
                if handle is None:
                    continue
                last_seen[handle] = time_ms
                row = ownership.get(handle)
                if row is None:
                    continue
                if row.owner in side_a:
                    handle_side[handle] = "teamA"
                elif row.owner in side_b:
                    handle_side[handle] = "teamB"
        elif action_id == ACT_TARGET_POSITION_AND_UNIT:
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
            actor_team_a = player_id in side_a
            target_team_a = target_slot in side_a
            if actor_team_a == target_team_a:
                continue  # same-team or unclassified
            attacks_by_handle[target_handle].append((time_ms, player_id))
            if time_ms <= battle.end_ms:
                last_seen[target_handle] = max(last_seen.get(target_handle, 0), time_ms)
                if target_slot in side_a:
                    handle_side[target_handle] = "teamA"
                elif target_slot in side_b:
                    handle_side[target_handle] = "teamB"

    out: list[dict[str, Any]] = []
    unattributed = 0

    for handle, attacks in attacks_by_handle.items():
        if not attacks:
            continue
        # Disappearance check: was this handle never seen again after
        # the last attack inside the window?
        last_attack_time = max(t for t, _ in attacks)
        if last_attack_time > battle.end_ms:
            continue  # attack landed after the window — out of scope
        last_selection_after_attack = max(
            (t for t in [last_seen.get(handle, 0)] if t > last_attack_time),
            default=None,
        )
        # If the handle is selected ≥ 5s after the last attack on it,
        # it survived — not a kill.
        if last_selection_after_attack is not None and last_selection_after_attack > last_attack_time + PRE_DEATH_WINDOW_MS:
            continue

        # Damage-share credit: actors who attacked in [last_attack - 5s, last_attack]
        pre_death_attackers: dict[int, int] = defaultdict(int)
        for t, actor in attacks:
            if last_attack_time - PRE_DEATH_WINDOW_MS <= t <= last_attack_time:
                pre_death_attackers[actor] += 1

        if not pre_death_attackers:
            unattributed += 1
            continue

        total = sum(pre_death_attackers.values())
        credits = [
            {"slot": slot, "fraction": count / total}
            for slot, count in sorted(pre_death_attackers.items())
        ]

        # Resolve victim's gold value from owner's heroes / units list
        target_row = ownership.get(handle)
        victim_slot = target_row.owner if target_row else None
        victim_value = 0
        victim_entity = {"id": "UNKN", "name": "UNKN", "unknown": True}
        # Best-effort: if we know victim's slot, find a likely entity
        # from the player's most-produced unit type. v1 approximation —
        # without per-handle unit-type tracking, we use a default value.
        if victim_slot is not None:
            for p in parser_output.get("players", []) or []:
                if p.get("id") != victim_slot:
                    continue
                # Use the most-produced unit's cost as proxy
                units_summary = (p.get("units") or {}).get("summary") or {}
                if units_summary:
                    most_built_id = max(units_summary, key=lambda k: units_summary[k].get("count", 0) if isinstance(units_summary[k], dict) else 0)
                    cost_record = unit_costs.get(most_built_id) or {}
                    victim_value = int(cost_record.get("gold", 0)) + int(cost_record.get("lumber", 0))
                    victim_entity = {"id": most_built_id, "name": most_built_id, "unknown": True}
                break

        side_label = handle_side.get(handle, "teamA")

        out.append({
            "victimHandle":   list(handle),
            "victimEntity":   victim_entity,
            "victimSide":     side_label,
            "victimValue":    victim_value,
            "killTimeMs":     last_attack_time,
            "credits":        credits,
        })

    return out, unattributed


def compute_match_kp_percent(
    battles: list[Any],
    players_analysis: list[dict[str, Any]],
) -> dict[int, float | None]:
    """Per-player KP% across the match.

    KP% = sum(player credits across all battle kills) / total team kills × 100
    """
    out: dict[int, float | None] = {}
    if not battles:
        return out

    per_player: dict[int, float] = defaultdict(float)
    total_kills = 0
    for battle_block in battles:
        for kill in battle_block.get("kills", []) or []:
            total_kills += 1
            for credit in kill.get("credits", []) or []:
                per_player[credit["slot"]] += credit.get("fraction", 0.0)

    for player in players_analysis:
        slot = player.get("id")
        if not isinstance(slot, int):
            continue
        if total_kills == 0:
            out[slot] = None
        else:
            out[slot] = 100.0 * per_player.get(slot, 0.0) / total_kills

    return out
