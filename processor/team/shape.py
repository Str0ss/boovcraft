"""Team-block envelope assembler.

Single source of truth for the JSON shape of the ``team`` top-level
key. Called from ``processor/analyze.py``; reads internal state objects
produced by other ``team/*`` modules and emits the JSON-ready dict.

In Phase 1b only the ``battles`` and ``sharedControl`` portions are
populated; ``itemTransfers``, ``supportEvents``, ``resourceCooperation``,
``players``, and ``battleSummary`` ship as empty-shape placeholders to
keep the data-model contract's "Shape B has all eight keys" invariant
satisfied. Subsequent phases fill them in.

Pure stdlib; no external imports.

See:
  - specs/007-team-cohesion-analysis/data-model.md § TeamBlock
  - specs/007-team-cohesion-analysis/contracts/output-shape.md
"""

from __future__ import annotations

from typing import Any

from .battles import BattleWindow
from .centroids import (
    AlliedDistanceRow,
    CentroidRow,
    SplitEngagementResult,
    active_aura_radius,
    compute_allied_distances,
    compute_centroids,
    flag_split_engagement,
)
from .ownership import build_ownership_map
from .positions import run_position_state


# --- Applicability detection -----------------------------------------------

def _detect_applicability_reason(
    parser_output: dict[str, Any],
    battles: list[BattleWindow],
) -> str | None:
    """Return ``None`` if applicable; otherwise a Shape A reason string.

    Reasons:
      - "noAllies"        : no team has ≥ 2 non-AI players
      - "ffa"             : fixedTeams === false AND no two non-AI
                            players share a teamId
      - "noBattlesDetected": fixedTeams + allies present but zero
                             battle windows AND no allied transfers
                             AND no shared control
    """
    players = parser_output.get("players", []) or []
    settings = parser_output.get("settings", {}) or {}
    fixed_teams = bool(settings.get("fixedTeams"))

    # team_id → count of non-neutral players
    teams: dict[int, list[int]] = {}
    for p in players:
        slot = p.get("id")
        team = p.get("teamid")
        if not isinstance(slot, int) or not isinstance(team, int):
            continue
        teams.setdefault(team, []).append(slot)

    has_allies = any(len(slots) >= 2 for slots in teams.values())
    # Check FFA first — it's the more specific intent. A 1v1 has
    # fixedTeams=true + no allies → noAllies. A FFA replay has
    # fixedTeams=false → ffa, regardless of team distribution.
    if not fixed_teams:
        return "ffa"
    if not has_allies:
        return "noAllies"

    if not battles:
        # Check for any allied 0x51 transfers as a secondary signal
        any_transfer = False
        for p in players:
            for t in p.get("resourceTransfers", []) or []:
                any_transfer = True
                break
            if any_transfer:
                break
        shared_control = bool(settings.get("fullSharedUnitControl"))
        if not any_transfer and not shared_control:
            return "noBattlesDetected"

    return None


# --- Per-entity emitters ----------------------------------------------------

def _emit_centroid(row: CentroidRow) -> dict[str, Any]:
    return {
        "slot":   row.slot,
        "x":      row.x,
        "y":      row.y,
        "source": row.source,
    }


def _emit_allied_distance(row: AlliedDistanceRow) -> dict[str, Any]:
    return {
        "fromSlot": row.from_slot,
        "toSlot":   row.to_slot,
        "distance": row.distance,
    }


def _emit_split_engagement(split: SplitEngagementResult) -> dict[str, Any]:
    return {
        "flagged":           split.flagged,
        "distance":          split.distance,
        "referenceAuraId":   split.reference_aura_id,
        "referenceAuraName": split.reference_aura_name,
        "flaggedSlots":      list(split.flagged_slots),
    }


def _emit_battle(
    battle: BattleWindow,
    centroids: list[CentroidRow],
    distances: list[AlliedDistanceRow],
    split: SplitEngagementResult,
) -> dict[str, Any]:
    return {
        "index":           battle.index,
        "startMs":         battle.start_ms,
        "endMs":           battle.end_ms,
        "sides": {
            "teamA": list(battle.sides["teamA"]),
            "teamB": list(battle.sides["teamB"]),
        },
        "centroids":       [_emit_centroid(c) for c in centroids],
        "alliedDistances": [_emit_allied_distance(d) for d in distances],
        "splitEngagement": _emit_split_engagement(split),
        # Fields populated in subsequent phases — empty placeholders for now.
        "focusFire":       None,
        "pings":           [],
        "kills":           [],
    }


# --- Top-level assembler ----------------------------------------------------

def assemble_team_block(
    parser_output: dict[str, Any],
    auras_table: dict[str, dict[str, Any]],
    item_attributes: dict[str, dict[str, Any]] | None = None,
    rescue_items: list[str] | None = None,
    unit_costs: dict[str, dict[str, Any]] | None = None,
    entity_names: dict[str, str] | None = None,
    players_analysis: list[dict[str, Any]] | None = None,
    diagnostics_metric_gaps: list[dict[str, str]] | None = None,
    diagnostics_item_gaps: list[dict[str, str]] | None = None,
    diagnostics_unmapped: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Compute and assemble the full ``team`` block.

    Phase 2: emits battles + centroids + splitEngagement +
    itemTransfers + resourceCooperation + sharedControl + findings.
    Phase 3+ sub-blocks (focusFire/pings/kills, TEI, attributions,
    executive) ship as empty placeholders.
    """
    settings = parser_output.get("settings", {}) or {}

    # Build state machines
    ownership = build_ownership_map(parser_output)

    # Detect battles BEFORE running position state — this lets us
    # short-circuit the expensive position-state walk for replays
    # where applicability is "noAllies" / "ffa".
    from .battles import detect_battle_windows
    battles = detect_battle_windows(parser_output, ownership)

    reason = _detect_applicability_reason(parser_output, battles)
    if reason is not None:
        return {"applicable": False, "reason": reason}

    state = run_position_state(parser_output, ownership)

    # Per-battle computation (Phase 1b + 3 + 4)
    from .cohesion import compute_focus_fire, extract_pings
    from .kills import estimate_kills

    battles_out: list[dict[str, Any]] = []
    total_unattributed = 0
    for battle in battles:
        centroids = compute_centroids(battle, state)
        distances = compute_allied_distances(battle, centroids)
        split = flag_split_engagement(battle, centroids, distances, parser_output, auras_table)

        # Phase 3 — focus fire + pings
        focus_fire = compute_focus_fire(battle, parser_output, ownership) if ownership else None
        pings = extract_pings(battle, parser_output, state, battles)

        # Phase 3 — kill estimation
        kills_list, unattributed = ([], 0)
        if unit_costs is not None:
            kills_list, unattributed = estimate_kills(battle, parser_output, ownership, unit_costs)
        total_unattributed += unattributed

        battle_block = _emit_battle(battle, centroids, distances, split)
        battle_block["focusFire"] = focus_fire
        battle_block["pings"] = pings
        battle_block["kills"] = kills_list
        battles_out.append(battle_block)

        if focus_fire is None and diagnostics_metric_gaps is not None:
            diagnostics_metric_gaps.append({
                "metric": f"focusFire:battle={battle.index}",
                "reason": "no enemy unit-handle ownership inferable in window",
            })

    if total_unattributed > 0 and diagnostics_metric_gaps is not None:
        diagnostics_metric_gaps.append({
            "metric": "killParticipation",
            "reason": f"{total_unattributed} kills had no attack-action coverage",
        })

    # Top-level findings (only "sharedControlDisabled" in v1 closed enum)
    findings: list[str] = []
    full_shared = settings.get("fullSharedUnitControl")
    if full_shared is False:
        findings.append("sharedControlDisabled")

    # --- Phase 2: support events + resource cooperation ----------------
    item_transfers: list[dict[str, Any]] = []
    support_events: list[dict[str, Any]] = []
    resource_transfers: list[dict[str, Any]] = []
    generosity: list[dict[str, Any]] = []

    if item_attributes is not None and entity_names is not None and diagnostics_item_gaps is not None:
        from .support import detect_missed_saves, extract_item_transfers
        item_transfers = extract_item_transfers(
            parser_output, ownership, item_attributes, entity_names, diagnostics_item_gaps,
        )
        support_events = detect_missed_saves(
            parser_output, ownership, state, rescue_items or [], entity_names, battles,
        )

    if players_analysis is not None and unit_costs is not None and diagnostics_metric_gaps is not None and diagnostics_unmapped is not None:
        from .resources import annotate_transfers, compute_generosity
        resource_transfers = annotate_transfers(parser_output, players_analysis)
        generosity = compute_generosity(
            players_analysis, unit_costs, diagnostics_metric_gaps, diagnostics_unmapped,
        )

    # --- Phase 4: TEI + attributions + executive ---------------------------
    from .attribution import compute_executive, detect_attributions
    from .kills import compute_match_kp_percent
    from .tei import compute_battle_tei

    tei_rows = [compute_battle_tei(b) for b in battles_out]

    kp_per_player = compute_match_kp_percent(battles_out, players_analysis or [])
    players_block = []
    for p in parser_output.get("players", []) or []:
        slot = p.get("id")
        if not isinstance(slot, int):
            continue
        players_block.append({
            "slot": slot,
            "name": p.get("name", ""),
            "killParticipationPercent": kp_per_player.get(slot),
        })

    attributions = detect_attributions(battles_out, tei_rows)

    # Build the team_block first (with empty executive), then compute
    # executive (which reads from the rest of the block), then merge.
    team_block_partial = {
        "applicable":          True,
        "sharedControl":       {"enabled": bool(full_shared)},
        "findings":            findings,
        "battles":             battles_out,
        "itemTransfers":       item_transfers,
        "supportEvents":       support_events,
        "resourceCooperation": {
            "transfers":  resource_transfers,
            "generosity": generosity,
        },
        "players":             players_block,
        "battleSummary":       {
            "tei":          tei_rows,
            "attributions": attributions,
            "executive":    [],
        },
    }
    team_block_partial["battleSummary"]["executive"] = compute_executive(team_block_partial)

    # --- Phase 1 of feature 009: centroid timeline -----------------------
    if unit_costs is not None:
        from .timeline import compute_centroid_timeline
        team_block_partial["centroidTimeline"] = compute_centroid_timeline(
            parser_output, state, unit_costs,
        )

    return team_block_partial

    # Unreachable — preserved for safety
    _unused_legacy = {
        "applicable":          True,
        "sharedControl":       {"enabled": bool(full_shared)},
        "findings":            findings,
        "battles":             battles_out,
        "itemTransfers":       item_transfers,
        "supportEvents":       support_events,
        "resourceCooperation": {
            "transfers":  resource_transfers,
            "generosity": generosity,
        },
        "players":             [
            {"slot": p["id"], "name": p.get("name", ""), "killParticipationPercent": None}
            for p in parser_output.get("players", []) or []
            if isinstance(p.get("id"), int)
        ],
        "battleSummary":       {"tei": [], "attributions": [], "executive": []},
    }
