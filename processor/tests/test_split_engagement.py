"""Phase 1b — split-engagement flag.

Covers FR-005 and output-shape invariant 9 (biconditional).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from processor.team.battles import detect_battle_windows
from processor.team.centroids import (
    compute_allied_distances,
    compute_centroids,
    flag_split_engagement,
)
from processor.team.ownership import build_ownership_map
from processor.team.positions import run_position_state

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def auras_table():
    with (PROCESSOR_DIR / "auras.json").open() as f:
        return json.load(f)


def test_flagged_biconditional_base_2(base_2_parser_output, auras_table):
    """Invariant 9: flagged === true ⇔ flaggedSlots.length === 2 ⇔ distance > radius."""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    battles = detect_battle_windows(base_2_parser_output, ownership)
    for b in battles:
        cs = compute_centroids(b, state)
        ds = compute_allied_distances(b, cs)
        split = flag_split_engagement(b, cs, ds, base_2_parser_output, auras_table)

        # Resolve the radius for comparison: lookup the aura record or use 900 default
        if split.reference_aura_id == "default":
            radius = 900
        else:
            rec = auras_table[split.reference_aura_id]
            radius = rec["radius"]

        if split.flagged:
            assert len(split.flagged_slots) == 2
            assert split.distance > radius
        else:
            assert len(split.flagged_slots) == 0
            assert split.distance <= radius


def test_flagged_pair_is_intra_side(base_1_parser_output, auras_table):
    """The flagged pair MUST belong entirely to one side of the battle."""
    ownership = build_ownership_map(base_1_parser_output)
    state = run_position_state(base_1_parser_output, ownership)
    battles = detect_battle_windows(base_1_parser_output, ownership)
    for b in battles:
        cs = compute_centroids(b, state)
        ds = compute_allied_distances(b, cs)
        split = flag_split_engagement(b, cs, ds, base_1_parser_output, auras_table)
        if not split.flagged:
            continue
        a, c = split.flagged_slots
        side_a = set(b.sides["teamA"])
        side_b = set(b.sides["teamB"])
        assert {a, c}.issubset(side_a) or {a, c}.issubset(side_b), (
            f"battle [{b.index}]: flagged pair {split.flagged_slots} spans sides"
        )


def test_no_distance_no_flag(base_2_parser_output, auras_table):
    """When alliedDistances is empty, split-engagement MUST default to non-flagged."""
    from processor.team.centroids import flag_split_engagement
    ownership = build_ownership_map(base_2_parser_output)
    battles = detect_battle_windows(base_2_parser_output, ownership)
    if not battles:
        pytest.skip("no battles in base_2")
    b = battles[0]
    # Empty centroids, empty distances
    split = flag_split_engagement(b, [], [], base_2_parser_output, auras_table)
    assert split.flagged is False
    assert split.flagged_slots == ()
