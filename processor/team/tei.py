"""Trade-Efficiency Index (TEI) — gold + lumber per battle.

Phase 4 implementation of FR-021. Sentinel cap at 99.0 for zero-loss.

Pure stdlib; no external imports.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

TEI_ZERO_LOSS_CAP = 99.0
TEI_LOSS_FLOOR = 1  # max(player_value_lost, 1) per spec


def compute_battle_tei(
    battle_block: dict[str, Any],
) -> dict[str, Any]:
    """Compute team-side and per-player TEI for one battle.

    Reads ``battle_block.kills[]`` (must already be populated).
    """
    side_a = set(battle_block.get("sides", {}).get("teamA", []))
    side_b = set(battle_block.get("sides", {}).get("teamB", []))

    # Team-side: value killed by teamA (= victims on teamB) ÷ value lost by teamA (= victims on teamA)
    value_killed_by: dict[str, int] = {"teamA": 0, "teamB": 0}
    value_lost_by: dict[str, int] = {"teamA": 0, "teamB": 0}

    # Per-player attack share aggregation
    per_player_value_killed: dict[int, float] = defaultdict(float)
    per_player_value_lost: dict[int, int] = defaultdict(int)
    per_player_attack_share_total: dict[int, float] = defaultdict(float)

    for kill in battle_block.get("kills", []) or []:
        victim_side = kill.get("victimSide")  # "teamA" | "teamB"
        victim_value = kill.get("victimValue", 0) or 0
        if victim_side not in ("teamA", "teamB"):
            continue
        # The killing side is the OTHER team
        killing_side = "teamB" if victim_side == "teamA" else "teamA"
        value_killed_by[killing_side] += victim_value
        value_lost_by[victim_side] += victim_value

        # Per-player credits — distribute victim_value by fraction
        for credit in kill.get("credits", []) or []:
            slot = credit.get("slot")
            fraction = credit.get("fraction", 0.0) or 0.0
            if isinstance(slot, int):
                per_player_value_killed[slot] += victim_value * fraction
                per_player_attack_share_total[slot] += fraction

        # Victim's value adds to victim's slot's lost-tally — best
        # effort, since victim_slot inferred from victimSide is
        # team-level not player-level. We don't have per-handle owner
        # at this point in the data model; accept the team-level
        # approximation.

    def _team_tei(side: str) -> float | None:
        killed = value_killed_by[side]
        lost = value_lost_by[side]
        if killed == 0 and lost == 0:
            return None  # truly insufficient data
        if lost == 0:
            return TEI_ZERO_LOSS_CAP
        return min(TEI_ZERO_LOSS_CAP, killed / lost)

    team_side_tei = {
        "teamA": _team_tei("teamA"),
        "teamB": _team_tei("teamB"),
    }

    per_player_tei: list[dict[str, Any]] = []
    all_slots = sorted(side_a | side_b)
    # v1 limitation: per-player value_lost is not tracked (requires
    # per-handle owner attribution at kill time, which is more invasive
    # than the v1 estimate_kills heuristic supports). When no per-player
    # losses are observable, emit null per-player TEI rather than a
    # misleading 99.0 sentinel for everyone. The team-side TEI remains
    # accurate and is the more useful metric.
    any_per_player_loss = any(per_player_value_lost.get(s, 0) > 0 for s in all_slots)
    for slot in all_slots:
        if not any_per_player_loss:
            tei = None
        else:
            killed = per_player_value_killed.get(slot, 0.0)
            lost = max(per_player_value_lost.get(slot, 0), TEI_LOSS_FLOOR)
            if per_player_attack_share_total.get(slot, 0.0) == 0.0 and killed == 0:
                tei = None
            else:
                tei = min(TEI_ZERO_LOSS_CAP, killed / lost)
        per_player_tei.append({"slot": slot, "tei": tei})

    return {
        "battleIndex":  battle_block.get("index", 0),
        "teamSideTei":  team_side_tei,
        "perPlayerTei": per_player_tei,
    }
