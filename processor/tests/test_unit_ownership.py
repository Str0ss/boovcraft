"""Tier 2 foundation — handle ownership map.

Covers FR-001 prerequisite (battle window detection consumes ownership
to filter creep aggro) and feeds every spatial / cohesion metric in
later phases.
"""

from __future__ import annotations

from collections import Counter

import pytest

from processor.team.events import NEUTRAL_SLOT_IDS
from processor.team.ownership import build_ownership_map


def test_base_2_ownership_map_is_non_empty(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    assert ownership, "ownership map MUST contain at least one handle"
    # base_2 has 6 non-AI players; each should own at least 1 handle
    by_owner = Counter(row.owner for row in ownership.values())
    assert len(by_owner) >= 6, f"expected ≥ 6 owners, got {len(by_owner)}: {dict(by_owner)}"


def test_base_1_ownership_map_is_non_empty(base_1_parser_output):
    ownership = build_ownership_map(base_1_parser_output)
    assert ownership, "ownership map MUST contain at least one handle"
    by_owner = Counter(row.owner for row in ownership.values())
    # base_1 is 4v4, so 8 non-AI players
    assert len(by_owner) >= 8, f"expected ≥ 8 owners, got {len(by_owner)}: {dict(by_owner)}"


def test_neutral_slots_are_excluded(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    for handle, row in ownership.items():
        assert row.owner not in NEUTRAL_SLOT_IDS, (
            f"handle {handle} owned by neutral slot {row.owner}"
        )


def test_ownership_is_deterministic(base_2_parser_output):
    """Re-running build_ownership_map on the same input MUST produce the
    same dict (Python 3.7+ insertion-order guarantee)."""
    a = build_ownership_map(base_2_parser_output)
    b = build_ownership_map(base_2_parser_output)
    assert list(a.keys()) == list(b.keys())
    assert a == b


def test_handles_have_non_negative_event_idx(base_2_parser_output):
    ownership = build_ownership_map(base_2_parser_output)
    for handle, row in ownership.items():
        assert row.first_seen_event_idx >= 0, (
            f"handle {handle} has negative first_seen_event_idx={row.first_seen_event_idx}"
        )


def test_co_controlled_excludes_owner(base_2_parser_output):
    """A handle's owner must not appear in its own co_controlled_by list."""
    ownership = build_ownership_map(base_2_parser_output)
    for handle, row in ownership.items():
        assert row.owner not in row.co_controlled_by, (
            f"handle {handle} owner {row.owner} appears in coControlled {row.co_controlled_by}"
        )


def test_co_controlled_has_no_duplicates(base_1_parser_output):
    ownership = build_ownership_map(base_1_parser_output)
    for handle, row in ownership.items():
        assert len(row.co_controlled_by) == len(set(row.co_controlled_by)), (
            f"handle {handle} has duplicate entries in coControlledBy={row.co_controlled_by}"
        )


def test_base_2_coverage_floor(base_2_parser_output):
    """Per tasks.md T013 — base_2 ownership map should cover the bulk
    of selectable handles. Empirical floor: ≥ 200 handles on the 3v3
    fixture (observed ~328 at the time of writing)."""
    ownership = build_ownership_map(base_2_parser_output)
    assert len(ownership) >= 200, (
        f"base_2 ownership coverage too low: {len(ownership)} handles"
    )
