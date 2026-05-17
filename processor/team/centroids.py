"""Centroids, allied pair distances, active-aura lookup, split-engagement flag.

Phase 1b implementation. Reads from:
  - ``BattleWindow`` (from team.battles)
  - ``PositionState`` (from team.positions)
  - ``processor/auras.json`` (loaded by analyze.py and threaded through)
  - parser_output["players"][i].heroes (for hero ownership)

Emits the per-battle ``centroids``, ``alliedDistances``, and
``splitEngagement`` portions of ``team.battles[i]``.

Pure stdlib; no external imports.
"""

from __future__ import annotations

import math
from typing import Any, NamedTuple

from .battles import BattleWindow
from .positions import PositionState

# --- Heuristic constants (research.md § R3) ---------------------------------

CENTROID_LOOKBACK_MS = 60_000     # 60 s before battle start
DEFAULT_AURA_RADIUS = 900         # WC3 Devotion Aura canonical range


# --- Aura lookup ------------------------------------------------------------

class AuraResolution(NamedTuple):
    radius: int
    ability_id: str   # 4-char ability id, OR "default"
    name: str         # display name, OR "default 900u"


def _heroes_for_battle_team(
    parser_output: dict[str, Any],
    side_slots: tuple[int, ...],
) -> set[str]:
    """Collect every hero ability id learned by any player on this side.

    Used to determine which auras are "active" — a player who learned a
    Paladin's Devotion Aura ability during the match has the aura
    available.
    """
    hero_abilities: set[str] = set()
    for player in parser_output.get("players", []) or []:
        if player.get("id") not in side_slots:
            continue
        for hero in player.get("heroes", []) or []:
            # Parser-output abilityOrder entries: {type, time, value}.
            # The 4-char ability id lives in `value` (not `id`).
            for ability in hero.get("abilityOrder", []) or []:
                aid = ability.get("value")
                if isinstance(aid, str) and len(aid) == 4:
                    hero_abilities.add(aid)
            # Heroes may also expose an `abilities` map keyed by id.
            abilities_map = hero.get("abilities") or {}
            if isinstance(abilities_map, dict):
                for aid in abilities_map.keys():
                    if isinstance(aid, str) and len(aid) == 4:
                        hero_abilities.add(aid)
    return hero_abilities


def active_aura_radius(
    parser_output: dict[str, Any],
    side_slots: tuple[int, ...],
    auras_table: dict[str, dict[str, Any]],
) -> AuraResolution:
    """Return the largest active *support* aura radius for this side.

    Falls back to (DEFAULT_AURA_RADIUS, "default", "default 900u") when
    no support aura is learned by the side's heroes.
    """
    learned = _heroes_for_battle_team(parser_output, side_slots)

    best: tuple[int, str, str] | None = None
    # Sort for deterministic tie-breaking: every aura in auras.json shares
    # radius 900, so set-iteration order would otherwise leak Python's
    # per-process hash randomization into the analyzer output.
    for ability_id in sorted(learned):
        record = auras_table.get(ability_id)
        if record is None:
            continue
        if record.get("type") != "support":
            continue
        radius = record.get("radius")
        name = record.get("name", ability_id)
        if not isinstance(radius, (int, float)):
            continue
        radius_int = int(radius)
        if best is None or radius_int > best[0]:
            best = (radius_int, ability_id, name)

    if best is None:
        return AuraResolution(radius=DEFAULT_AURA_RADIUS, ability_id="default", name="default 900u")
    return AuraResolution(radius=best[0], ability_id=best[1], name=best[2])


# --- Centroid + distance helpers --------------------------------------------

class CentroidRow(NamedTuple):
    slot: int
    x: float | None
    y: float | None
    source: str  # "commanded" | "missing"


class AlliedDistanceRow(NamedTuple):
    from_slot: int
    to_slot: int
    distance: float


def compute_centroids(
    battle: BattleWindow,
    position_state: PositionState,
) -> list[CentroidRow]:
    """One CentroidRow per participating non-AI player on each side."""
    out: list[CentroidRow] = []
    all_slots = sorted(set(battle.sides["teamA"]) | set(battle.sides["teamB"]))

    lookback_from = max(0, battle.start_ms - CENTROID_LOOKBACK_MS)
    lookback_to = battle.start_ms

    for slot in all_slots:
        c = position_state.centroid_at(slot, lookback_from, lookback_to)
        if c is None:
            # Try a longer fallback — single most-recent commanded position
            # over the entire match so far.
            c = position_state.centroid_at(slot, 0, battle.start_ms)
        if c is None:
            out.append(CentroidRow(slot=slot, x=None, y=None, source="missing"))
        else:
            out.append(CentroidRow(slot=slot, x=c[0], y=c[1], source="commanded"))
    return out


def compute_allied_distances(
    battle: BattleWindow,
    centroids: list[CentroidRow],
) -> list[AlliedDistanceRow]:
    """Per-side pairwise Euclidean distances. fromSlot < toSlot canonical."""
    by_slot: dict[int, CentroidRow] = {row.slot: row for row in centroids}
    out: list[AlliedDistanceRow] = []
    for side_label in ("teamA", "teamB"):
        side_slots = sorted(battle.sides[side_label])
        for i, a in enumerate(side_slots):
            for b in side_slots[i + 1:]:
                ra = by_slot.get(a)
                rb = by_slot.get(b)
                if ra is None or rb is None:
                    continue
                if ra.x is None or ra.y is None or rb.x is None or rb.y is None:
                    continue
                dx = ra.x - rb.x
                dy = ra.y - rb.y
                out.append(AlliedDistanceRow(from_slot=a, to_slot=b, distance=math.hypot(dx, dy)))
    return out


# --- Split engagement -------------------------------------------------------

class SplitEngagementResult(NamedTuple):
    flagged: bool
    distance: float
    reference_aura_id: str
    reference_aura_name: str
    flagged_slots: tuple[int, ...]


def flag_split_engagement(
    battle: BattleWindow,
    centroids: list[CentroidRow],
    allied_distances: list[AlliedDistanceRow],
    parser_output: dict[str, Any],
    auras_table: dict[str, dict[str, Any]],
) -> SplitEngagementResult:
    """Compute per-side split-engagement; emit one result for the side
    with the maximum allied centroid distance.

    Implementation note: spec invariant 9 requires ``flagged === true ⇔
    distance > radius``. We pick the maximum distance across BOTH sides
    (because either side's split is a legitimate finding) and compare
    that to the larger of the two sides' active aura radii.
    """
    if not allied_distances:
        return SplitEngagementResult(
            flagged=False,
            distance=0.0,
            reference_aura_id="default",
            reference_aura_name="default 900u",
            flagged_slots=(),
        )

    max_dist_row = max(allied_distances, key=lambda r: r.distance)
    max_distance = max_dist_row.distance
    flagged_pair = (max_dist_row.from_slot, max_dist_row.to_slot)

    # Determine the side that the flagged pair belongs to, and resolve
    # its active aura radius.
    pair_set = set(flagged_pair)
    side_for_pair = "teamA" if pair_set.issubset(set(battle.sides["teamA"])) else "teamB"
    side_slots = battle.sides[side_for_pair]
    aura = active_aura_radius(parser_output, side_slots, auras_table)

    flagged = max_distance > aura.radius

    return SplitEngagementResult(
        flagged=flagged,
        distance=max_distance,
        reference_aura_id=aura.ability_id,
        reference_aura_name=aura.name,
        flagged_slots=tuple(flagged_pair) if flagged else (),
    )
