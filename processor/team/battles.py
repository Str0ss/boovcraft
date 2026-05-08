"""Battle window detection — Phase 1b foundation.

Walks the parser-output event stream and identifies contiguous time
ranges in which both opposing teams are actively dealing damage to
each other. Output: a list of ``BattleWindow`` records consumed by
``team/centroids.py`` (split engagement) and ``team/cohesion.py``
(focus fire, pings, kills) in later phases.

Heuristic — bucket-and-runs (research.md § R3):
  - bucket size: 5 seconds (BUCKET_MS)
  - run-length floor: ≥ 3 buckets (RUN_FLOOR) → 15 s minimum to qualify
  - gap tolerance: ≤ 2 buckets (GAP_TOLERANCE) → 10 s of inactivity
    before the window closes

A bucket is "engaged" when at least one PvP attack action targets a
unit owned by the opposing team in that bucket. PvP attack actions:
``0x12`` (target-position-and-unit, where ``object`` resolves to an
opposing-team unit per ownership map). ``0x11`` is excluded — pure
position targets do not name a unit so we cannot tell if they are
attack-moving onto an enemy. Creep aggro is excluded by ownership
filtering (neutral handles 12 / 15).

Pure stdlib; no external imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .events import (
    ACT_TARGET_POSITION_AND_UNIT,
    NEUTRAL_SLOT_IDS,
    iter_command_actions,
)
from .ownership import Handle, OwnershipRow, _normalize_handle

# --- Heuristic constants (research.md § R3) ---------------------------------

BUCKET_MS = 5_000           # 5-second buckets
RUN_FLOOR = 3               # ≥ 3 consecutive engaged buckets opens a window
GAP_TOLERANCE = 2           # ≤ 2 consecutive non-engaged buckets keeps it open


@dataclass(frozen=True)
class BattleWindow:
    """One detected battle window.

    `sides` maps ``"teamA"`` / ``"teamB"`` to a tuple of slot ids that
    issued at least one PvP attack action in this window. Labels are
    deterministic-arbitrary: the side with the lowest slot id is
    ``teamA``.
    """

    index: int
    start_ms: int
    end_ms: int
    sides: dict[str, tuple[int, ...]]


def _slot_to_team(parser_output: dict[str, Any]) -> dict[int, int]:
    """Build {slot_id: team_id} from parser_output.players."""
    out: dict[int, int] = {}
    for p in parser_output.get("players", []) or []:
        slot = p.get("id")
        team = p.get("teamid")
        if isinstance(slot, int) and isinstance(team, int):
            out[slot] = team
    return out


def _is_pvp_attack(
    action: dict[str, Any],
    actor_slot: int,
    slot_to_team: dict[int, int],
    ownership: dict[Handle, OwnershipRow],
) -> bool:
    """Return True iff ``action`` is a 0x12 targeting an opposing-team unit."""
    if action.get("id") != ACT_TARGET_POSITION_AND_UNIT:
        return False
    target_obj = action.get("object")
    if not isinstance(target_obj, list) or len(target_obj) != 2:
        return False
    handle = _normalize_handle(target_obj)
    if handle is None:
        return False
    target_row = ownership.get(handle)
    if target_row is None:
        # Likely a creep / neutral — exclude.
        return False
    target_slot = target_row.owner
    if target_slot in NEUTRAL_SLOT_IDS:
        return False
    actor_team = slot_to_team.get(actor_slot)
    target_team = slot_to_team.get(target_slot)
    if actor_team is None or target_team is None:
        return False
    return actor_team != target_team


def detect_battle_windows(
    parser_output: dict[str, Any],
    ownership: dict[Handle, OwnershipRow],
) -> list[BattleWindow]:
    """Detect battle windows in the parser-output event stream.

    Returns a list sorted by ``start_ms`` ascending with stable
    ``index`` values (0, 1, 2, ...).
    """
    duration_ms = parser_output.get("duration", 0) or 0
    if duration_ms <= 0:
        return []

    slot_to_team = _slot_to_team(parser_output)
    if not slot_to_team:
        return []

    n_buckets = (duration_ms // BUCKET_MS) + 1

    # Per bucket, track:
    #   engaged[i]              — at least one PvP attack action observed
    #   actors_per_team[i][team] — set of slot ids that issued a PvP attack
    engaged = [False] * n_buckets
    actors_per_bucket: list[dict[int, set[int]]] = [
        {} for _ in range(n_buckets)
    ]

    for time_ms, player_id, action in iter_command_actions(parser_output):
        if player_id in NEUTRAL_SLOT_IDS:
            continue
        if not _is_pvp_attack(action, player_id, slot_to_team, ownership):
            continue
        bucket_idx = time_ms // BUCKET_MS
        if bucket_idx >= n_buckets:
            continue
        engaged[bucket_idx] = True
        actor_team = slot_to_team.get(player_id)
        if actor_team is None:
            continue
        team_actors = actors_per_bucket[bucket_idx].setdefault(actor_team, set())
        team_actors.add(player_id)

    # Run-and-gap detection.
    windows: list[tuple[int, int, dict[int, set[int]]]] = []
    i = 0
    while i < n_buckets:
        if not engaged[i]:
            i += 1
            continue
        # Find the run length and any internal gaps.
        run_start = i
        run_actors: dict[int, set[int]] = {}
        consecutive_engaged = 0
        gap_count = 0
        last_engaged_idx = i

        while i < n_buckets:
            if engaged[i]:
                consecutive_engaged += 1
                last_engaged_idx = i
                gap_count = 0
                for team, slots in actors_per_bucket[i].items():
                    run_actors.setdefault(team, set()).update(slots)
                i += 1
            else:
                gap_count += 1
                if gap_count > GAP_TOLERANCE:
                    break
                i += 1

        # The window ends at last_engaged_idx (inclusive).
        # We require the total number of engaged buckets in this run to
        # meet RUN_FLOOR.
        engaged_count = sum(1 for j in range(run_start, last_engaged_idx + 1) if engaged[j])
        if engaged_count >= RUN_FLOOR:
            windows.append((run_start, last_engaged_idx, run_actors))

    # Filter to two-side battles only — at least two distinct teams must
    # have issued PvP attacks during the window.
    out: list[BattleWindow] = []
    next_index = 0
    for run_start, run_end, run_actors in windows:
        teams = sorted(t for t, slots in run_actors.items() if slots)
        if len(teams) < 2:
            continue
        # Pick the two teams with the most actor diversity (or lowest team ids).
        team_a_id, team_b_id = teams[0], teams[1]
        side_a = tuple(sorted(run_actors[team_a_id]))
        side_b = tuple(sorted(run_actors[team_b_id]))
        if not side_a or not side_b:
            continue
        out.append(
            BattleWindow(
                index=next_index,
                start_ms=run_start * BUCKET_MS,
                end_ms=(run_end + 1) * BUCKET_MS - 1,
                sides={"teamA": side_a, "teamB": side_b},
            )
        )
        next_index += 1

    return out
