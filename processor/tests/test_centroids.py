"""Phase 1b — centroid computation, allied distances.

Covers FR-002 and output-shape invariants 7, 8.
"""

from __future__ import annotations

import math

import pytest

from processor.team.battles import detect_battle_windows
from processor.team.centroids import compute_allied_distances, compute_centroids
from processor.team.ownership import build_ownership_map
from processor.team.positions import run_position_state


@pytest.fixture(scope="module")
def battles_and_state(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    battles = detect_battle_windows(base_2_parser_output, ownership)
    return battles, state


def test_centroid_coordinate_consistency(battles_and_state):
    """Invariant 7: x === null ⇔ y === null ⇔ source === missing."""
    battles, state = battles_and_state
    for b in battles:
        for c in compute_centroids(b, state):
            if c.source == "missing":
                assert c.x is None and c.y is None
            else:
                assert c.x is not None and c.y is not None
                assert math.isfinite(c.x) and math.isfinite(c.y)


def test_centroid_one_per_participating_player(battles_and_state):
    """Every slot in either side has exactly one CentroidRow."""
    battles, state = battles_and_state
    for b in battles:
        all_slots = set(b.sides["teamA"]) | set(b.sides["teamB"])
        centroids = compute_centroids(b, state)
        emitted_slots = {c.slot for c in centroids}
        assert emitted_slots == all_slots, (
            f"battle [{b.index}]: expected slots {all_slots}, got {emitted_slots}"
        )


def test_allied_distance_canonicalization(battles_and_state):
    """Invariant 8: fromSlot < toSlot, distance non-negative finite."""
    battles, state = battles_and_state
    for b in battles:
        centroids = compute_centroids(b, state)
        dists = compute_allied_distances(b, centroids)
        for d in dists:
            assert d.from_slot < d.to_slot, f"non-canonical pair: {d.from_slot} >= {d.to_slot}"
            assert d.distance >= 0
            assert math.isfinite(d.distance)


def test_allied_distances_only_intra_side(battles_and_state):
    """Allied distances are intra-side only — no cross-team pairs."""
    battles, state = battles_and_state
    for b in battles:
        centroids = compute_centroids(b, state)
        dists = compute_allied_distances(b, centroids)
        side_a = set(b.sides["teamA"])
        side_b = set(b.sides["teamB"])
        for d in dists:
            same_side_a = d.from_slot in side_a and d.to_slot in side_a
            same_side_b = d.from_slot in side_b and d.to_slot in side_b
            assert same_side_a or same_side_b, (
                f"battle [{b.index}] cross-side pair: {d.from_slot}-{d.to_slot}"
            )
