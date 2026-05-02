"""Coverage for the per-event `players[].actions.timedActions`
extraction added in feature 004.

Invariant: for every player and every category present in
`actions.totals`, the count of entries in `timedActions` with that
category equals the total. This is the primary correctness check
on the new extractor — both fields derive from the same w3gjs
event stream and any drift between them surfaces a classifier bug.
"""

import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "processor"))

from analyze import build_analysis  # noqa: E402


@pytest.fixture(scope="session")
def base_1_analysis(base_1_parser_output):
    return build_analysis(base_1_parser_output, {}, set())


@pytest.fixture(scope="session")
def base_2_analysis(base_2_parser_output):
    return build_analysis(base_2_parser_output, {}, set())


@pytest.fixture(
    scope="session", params=["base_1", "base_2"], ids=["base_1", "base_2"]
)
def analysis(request, base_1_analysis, base_2_analysis):
    return {"base_1": base_1_analysis, "base_2": base_2_analysis}[request.param]

ALL_TOTAL_CATEGORIES = {
    "assigngroup",
    "rightclick",
    "basic",
    "buildtrain",
    "ability",
    "item",
    "select",
    "removeunit",
    "subgroup",
    "selecthotkey",
    "esc",
}


def test_every_player_has_timed_actions_field(analysis):
    for p in analysis["players"]:
        actions = p["actions"]
        assert "timedActions" in actions, f"player {p['id']} missing timedActions"
        assert isinstance(actions["timedActions"], list)


def test_timed_actions_record_shape(analysis):
    for p in analysis["players"]:
        for entry in p["actions"]["timedActions"]:
            assert set(entry.keys()) == {"timeMs", "category"}, (
                f"player {p['id']} entry has unexpected keys: {set(entry.keys())}"
            )
            assert isinstance(entry["timeMs"], int)
            assert entry["timeMs"] >= 0
            assert isinstance(entry["category"], str)
            assert entry["category"] in ALL_TOTAL_CATEGORIES, (
                f"player {p['id']} unrecognised category {entry['category']!r}"
            )


def test_timed_actions_sorted_by_time(analysis):
    for p in analysis["players"]:
        ta = p["actions"]["timedActions"]
        for i in range(1, len(ta)):
            assert ta[i - 1]["timeMs"] <= ta[i]["timeMs"], (
                f"player {p['id']} not sorted at index {i}"
            )


def test_timed_actions_within_match_duration(analysis):
    duration_ms = analysis["match"]["durationMs"]
    for p in analysis["players"]:
        for entry in p["actions"]["timedActions"]:
            assert 0 <= entry["timeMs"] <= duration_ms, (
                f"player {p['id']} entry timeMs={entry['timeMs']} outside [0, {duration_ms}]"
            )


def test_timed_actions_count_matches_totals(analysis):
    """Primary correctness invariant — each category's bucket count
    in `timedActions` must equal the count w3gjs reports in `totals`.
    """
    for p in analysis["players"]:
        actions = p["actions"]
        ta = actions["timedActions"]
        totals = actions["totals"]
        observed = Counter(entry["category"] for entry in ta)
        for cat, expected_count in totals.items():
            assert observed.get(cat, 0) == expected_count, (
                f"player {p['id']} category {cat}: "
                f"timedActions has {observed.get(cat, 0)}, totals has {expected_count}"
            )


def test_no_extra_categories_beyond_totals(analysis):
    """Categories emitted by the extractor must be a subset of the
    categories w3gjs reports — no novel labels.
    """
    for p in analysis["players"]:
        actions = p["actions"]
        emitted_categories = {entry["category"] for entry in actions["timedActions"]}
        # Allowed: any category present in w3gjs totals (even with count 0).
        # `subgroup` is initialised but never incremented by w3gjs, so it
        # is allowed here too — extractor must simply not emit anything
        # the totals do not also count.
        allowed_categories = set(actions["totals"].keys())
        unknown = emitted_categories - allowed_categories
        assert not unknown, f"player {p['id']} emitted unknown categories: {unknown}"
