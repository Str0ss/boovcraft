"""Tier 2 foundation — position state machine.

Covers FR-002 prerequisite (centroid computation reads from
PositionState) and the worker→building handoff invariant.
"""

from __future__ import annotations

from collections import Counter

import pytest

from processor.team.events import NEUTRAL_SLOT_IDS
from processor.team.ownership import build_ownership_map
from processor.team.positions import PositionState, run_position_state


def test_base_2_position_state_non_empty(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    assert state.by_handle, "position state MUST be non-empty after running on base_2"


def test_position_state_owners_match_ownership(base_2_parser_output):
    """Every position record's owner MUST match the ownership map's
    owner for that handle."""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    for handle, record in state.by_handle.items():
        assert handle in ownership
        assert ownership[handle].owner == record.owner, (
            f"handle {handle}: ownership {ownership[handle].owner} != position {record.owner}"
        )


def test_base_2_per_player_position_coverage(base_2_parser_output):
    """Every non-neutral player observed in base_2's ownership map MUST
    have at least one handle with a known position. (T014 acceptance bar.)"""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    owners = {row.owner for row in ownership.values()}
    for slot in owners:
        if slot in NEUTRAL_SLOT_IDS:
            continue
        positions_for_slot = [r for r in state.by_handle.values() if r.owner == slot]
        assert positions_for_slot, (
            f"slot {slot} has 0 position records — selected handles never received position commands"
        )


def test_finite_coordinates(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    import math

    for handle, record in state.by_handle.items():
        assert math.isfinite(record.x), f"handle {handle} non-finite x={record.x}"
        assert math.isfinite(record.y), f"handle {handle} non-finite y={record.y}"


def test_centroid_at_returns_none_outside_window(base_2_parser_output):
    """Centroid computed for an empty time window MUST be None."""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    # An out-of-replay window: ms 999_999_999 ahead of any real activity
    for slot in {row.owner for row in ownership.values()}:
        c = state.centroid_at(slot, 999_999_999, 1_000_000_000)
        assert c is None, f"slot {slot} unexpectedly had centroid in empty window: {c}"


def test_centroid_at_returns_finite_when_data_exists(base_2_parser_output):
    """For each player with at least one position record, centroid over
    [0, duration_ms] MUST be a finite (x, y) pair."""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    duration_ms = base_2_parser_output["duration"]
    import math

    owners_with_positions = {r.owner for r in state.by_handle.values()}
    for slot in owners_with_positions:
        c = state.centroid_at(slot, 0, duration_ms)
        assert c is not None, f"slot {slot} has positions but centroid_at returned None"
        x, y = c
        assert math.isfinite(x) and math.isfinite(y), (
            f"slot {slot}: non-finite centroid ({x}, {y})"
        )


def test_position_state_is_deterministic(base_2_parser_output):
    """Re-running run_position_state on the same input MUST produce
    byte-equivalent state."""
    ownership = build_ownership_map(base_2_parser_output)
    a = run_position_state(base_2_parser_output, ownership)
    b = run_position_state(base_2_parser_output, ownership)
    assert a.by_handle.keys() == b.by_handle.keys()
    for handle in a.by_handle:
        assert a.by_handle[handle] == b.by_handle[handle]


def test_worker_handoff_observed(base_2_parser_output):
    """At least one position record on base_2 SHOULD have source=='build',
    indicating a worker→building handoff occurred. (T014 acceptance.)"""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    sources = Counter(r.source for r in state.by_handle.values())
    assert sources.get("build", 0) >= 1, (
        f"expected at least one worker→building handoff, got source breakdown: {dict(sources)}"
    )


def test_base_1_state_non_empty(base_1_parser_output):
    """Same coverage check for base_1 (4v4, longer fixture)."""
    ownership = build_ownership_map(base_1_parser_output)
    state = run_position_state(base_1_parser_output, ownership)
    assert len(state.by_handle) >= 500, (
        f"base_1 position coverage too low: {len(state.by_handle)} records"
    )
