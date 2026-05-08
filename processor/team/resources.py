"""Resource cooperation — annotated transfers + generosity score.

Phase 2 implementation of FR-012 / FR-013 / FR-014.

Pure stdlib; no external imports.
"""

from __future__ import annotations

from typing import Any

# --- Heuristic constants (research.md § R3) ---------------------------------

PURPOSE_WINDOW_MS = 60_000          # ±60 s window for purposeHint classification
LATE_GAME_THRESHOLD_RATIO = 0.75    # past 75% of match → "lateGameTopUp"
BASE_DEFENSE_BUILDING_LOSSES = 3    # ≥ 3 buildings lost ≈ a base attack

# Tier-up building ids — when one of these appears in the recipient's
# production.buildings.order around transfer time, classify as
# "tierUpAssist".
TIER_UP_BUILDINGS = frozenset({
    "hkee", "hcas",          # Human Keep, Castle
    "ostr", "ofrt",          # Orc Stronghold, Fortress
    "unp1", "unp2",          # Undead Halls of the Dead, Black Citadel
    "etoa", "etoe",          # Night Elf Tree of Ages, Tree of Eternity
})


def annotate_transfers(
    parser_output: dict[str, Any],
    players_analysis: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mirror players[].resourceTransfers with added purposeHint."""
    duration_ms = parser_output.get("duration", 0) or 0
    out: list[dict[str, Any]] = []

    # Index players by id for O(1) recipient lookup
    by_id = {p["id"]: p for p in players_analysis if isinstance(p.get("id"), int)}

    for sender in players_analysis:
        for transfer in sender.get("resourceTransfers", []) or []:
            from_slot = transfer.get("fromSlot")
            to_player_id = transfer.get("toPlayerId")
            time_ms = transfer.get("timeMs", 0)
            gold = transfer.get("gold", 0)
            lumber = transfer.get("lumber", 0)
            to_name = transfer.get("toPlayerName", "")

            recipient = by_id.get(to_player_id)
            purpose_hint = "none"

            if recipient is not None:
                # Tier-up window: any tier-up building in [t-60s, t+60s]
                build_order = recipient.get("production", {}).get("buildings", {}).get("order", []) or []
                tier_up_seen = any(
                    entry.get("id") in TIER_UP_BUILDINGS
                    and abs(entry.get("timeMs", 0) - time_ms) <= PURPOSE_WINDOW_MS
                    for entry in build_order
                )
                if tier_up_seen:
                    purpose_hint = "tierUpAssist"
                elif duration_ms > 0 and time_ms > duration_ms * LATE_GAME_THRESHOLD_RATIO:
                    purpose_hint = "lateGameTopUp"
                # baseDefense detection requires removeunit-of-buildings
                # tracking, which the parser doesn't expose cleanly; we
                # leave it as "none" rather than emit a noisy false
                # signal.

            out.append({
                "fromSlot":     from_slot,
                "toPlayerId":   to_player_id,
                "toPlayerName": to_name,
                "gold":         gold,
                "lumber":       lumber,
                "timeMs":       time_ms,
                "purposeHint":  purpose_hint,
            })
    return out


# --- Generosity score -------------------------------------------------------

def compute_generosity(
    players_analysis: list[dict[str, Any]],
    unit_costs: dict[str, dict[str, Any]],
    diagnostics_metric_gaps: list[dict[str, str]],
    diagnostics_unmapped: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Per-player generosity score — `(sentGold + sentLumber) / mined estimate`.

    The mined estimate is the sum of unit_costs over the player's
    production.{units,buildings,upgrades,items}.summary. When ANY
    summary entry is missing from unit_costs.json, the entire estimate
    poisons to null and a metric-gap is recorded.
    """
    out: list[dict[str, Any]] = []
    seen_gaps: set[tuple[str, str]] = set()

    for player in players_analysis:
        slot = player.get("id")
        name = player.get("name", "")

        sent_gold = sum(t.get("gold", 0) for t in player.get("resourceTransfers", []) or [])
        sent_lumber = sum(t.get("lumber", 0) for t in player.get("resourceTransfers", []) or [])

        prod = player.get("production", {}) or {}
        estimated_gold = 0
        estimated_lumber = 0
        any_missing = False
        # Items are picked up / dropped, not "minted" by the player —
        # excluded from the totalMined estimate. unit_costs.json only
        # carries production-side entities (units, buildings, upgrades).
        for category in ("units", "buildings", "upgrades"):
            summary = (prod.get(category) or {}).get("summary") or {}
            for entity_id, entry in summary.items():
                count = entry.get("count", 0) if isinstance(entry, dict) else 0
                cost_record = unit_costs.get(entity_id)
                if cost_record is None:
                    any_missing = True
                    key = ("unitCost", entity_id)
                    if key not in seen_gaps:
                        seen_gaps.add(key)
                        diagnostics_unmapped.add(key)
                    continue
                estimated_gold += int(cost_record.get("gold", 0)) * count
                estimated_lumber += int(cost_record.get("lumber", 0)) * count

        if any_missing or estimated_gold + estimated_lumber == 0:
            estimated_mined_gold = None
            estimated_mined_lumber = None
            generosity_percent = None
            if any_missing:
                gap_key = f"generosity:slot={slot}"
                if not any(g.get("metric") == gap_key for g in diagnostics_metric_gaps):
                    diagnostics_metric_gaps.append({
                        "metric": gap_key,
                        "reason": "missing unit_cost entries in player's production",
                    })
        else:
            estimated_mined_gold = estimated_gold
            estimated_mined_lumber = estimated_lumber
            denom = estimated_gold + estimated_lumber
            numer = sent_gold + sent_lumber
            generosity_percent = 100.0 * numer / denom if denom > 0 else 0.0

        out.append({
            "slot":                  slot,
            "name":                  name,
            "sentGold":              sent_gold,
            "sentLumber":            sent_lumber,
            "estimatedMinedGold":    estimated_mined_gold,
            "estimatedMinedLumber":  estimated_mined_lumber,
            "generosityPercent":     generosity_percent,
        })
    return out
