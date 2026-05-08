"""Phase 1b — battle window detection.

Covers FR-001 and output-shape invariants 4-6.
"""

from __future__ import annotations

import pytest

from processor.team.battles import BUCKET_MS, GAP_TOLERANCE, RUN_FLOOR, detect_battle_windows
from processor.team.ownership import build_ownership_map


def test_base_2_at_least_one_battle(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    battles = detect_battle_windows(base_2_parser_output, ownership)
    assert len(battles) >= 1, "base_2 MUST produce at least one battle window"


def test_base_1_at_least_one_battle(base_1_parser_output):
    ownership = build_ownership_map(base_1_parser_output)
    battles = detect_battle_windows(base_1_parser_output, ownership)
    assert len(battles) >= 1, "base_1 MUST produce at least one battle window"


def test_battle_indices_are_contiguous(base_2_parser_output):
    """Invariant 5: indices are 0, 1, 2, ... no gaps, no duplicates."""
    ownership = build_ownership_map(base_2_parser_output)
    battles = detect_battle_windows(base_2_parser_output, ownership)
    for i, b in enumerate(battles):
        assert b.index == i, f"battle position {i} has index={b.index}"


def test_battle_time_bounds(base_1_parser_output):
    """Invariant 6: 0 <= startMs < endMs <= duration; no overlaps."""
    ownership = build_ownership_map(base_1_parser_output)
    battles = detect_battle_windows(base_1_parser_output, ownership)
    duration = base_1_parser_output["duration"]
    prev_end = -1
    for b in battles:
        assert 0 <= b.start_ms < b.end_ms <= duration
        assert b.start_ms > prev_end, f"battle [{b.index}] overlaps previous: prev_end={prev_end} start={b.start_ms}"
        prev_end = b.end_ms


def test_sides_disjoint_and_non_empty(base_1_parser_output):
    """Invariant 4: teamA and teamB are non-empty and disjoint."""
    ownership = build_ownership_map(base_1_parser_output)
    battles = detect_battle_windows(base_1_parser_output, ownership)
    for b in battles:
        side_a = set(b.sides["teamA"])
        side_b = set(b.sides["teamB"])
        assert side_a, f"battle [{b.index}] teamA empty"
        assert side_b, f"battle [{b.index}] teamB empty"
        assert side_a & side_b == set(), f"battle [{b.index}] sides overlap: {side_a & side_b}"


def test_constants_match_research_md():
    """The committed heuristic constants from research.md § R3."""
    assert BUCKET_MS == 5_000
    assert RUN_FLOOR == 3
    assert GAP_TOLERANCE == 2


def test_detection_is_deterministic(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    a = detect_battle_windows(base_2_parser_output, ownership)
    b = detect_battle_windows(base_2_parser_output, ownership)
    assert [(x.index, x.start_ms, x.end_ms, x.sides) for x in a] == [
        (x.index, x.start_ms, x.end_ms, x.sides) for x in b
    ]
