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


@pytest.fixture(
    scope="session", params=["base_1", "base_2"], ids=["base_1", "base_2"]
)
def parser_and_analysis(
    request, base_1_parser_output, base_2_parser_output, base_1_analysis, base_2_analysis
):
    return {
        "base_1": (base_1_parser_output, base_1_analysis),
        "base_2": (base_2_parser_output, base_2_analysis),
    }[request.param]

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
    required = {"timeMs", "category"}
    optional = {"x", "y"}
    allowed = required | optional
    for p in analysis["players"]:
        for entry in p["actions"]["timedActions"]:
            keys = set(entry.keys())
            assert required <= keys <= allowed, (
                f"player {p['id']} entry has unexpected keys: {keys}"
            )
            # x and y co-occur — present together or absent together (FR-003).
            assert ("x" in keys) == ("y" in keys), (
                f"player {p['id']} entry has mismatched x/y presence: {keys}"
            )
            assert isinstance(entry["timeMs"], int)
            assert entry["timeMs"] >= 0
            assert isinstance(entry["category"], str)
            assert entry["category"] in ALL_TOTAL_CATEGORIES, (
                f"player {p['id']} unrecognised category {entry['category']!r}"
            )
            if "x" in keys:
                assert isinstance(entry["x"], (int, float))
                assert isinstance(entry["y"], (int, float))


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


def test_coord_bearing_count_matches_parser_action_count(parser_and_analysis):
    """Drift detector: the count of coord-bearing entries in each
    category must equal the count of parser-output actions in
    {0x11, 0x12, 0x13, 0x14} that classified into that category. Both
    derive from the same w3gjs event stream — drift surfaces a
    classifier or coord-extraction bug.
    """
    from collections import defaultdict
    from analyze import _classify_action  # noqa: PLC0415

    parser_output, analysis = parser_and_analysis
    POSITION_BEARING_IDS = {0x11, 0x12, 0x13, 0x14}

    # Walk the parser-output events and count, per (player_id, category),
    # the actions whose w3gjs id is in POSITION_BEARING_IDS and whose
    # classification is non-None.
    parser_counts: dict[tuple[int, str], int] = defaultdict(int)
    for ev in parser_output.get("events") or []:
        for cb in ev.get("commandBlocks") or []:
            player_id = cb.get("playerId")
            if player_id is None:
                continue
            last_was_deselect = False
            for action in cb.get("actions") or []:
                category, last_was_deselect = _classify_action(action, last_was_deselect)
                if category is None:
                    continue
                if action.get("id") not in POSITION_BEARING_IDS:
                    continue
                parser_counts[(player_id, category)] += 1

    # Count, per (player_id, category), the timedActions entries that
    # carry coords.
    analysis_counts: dict[tuple[int, str], int] = defaultdict(int)
    for p in analysis["players"]:
        for entry in p["actions"]["timedActions"]:
            if "x" in entry:
                analysis_counts[(p["id"], entry["category"])] += 1

    assert parser_counts == analysis_counts, (
        "drift between parser-action coord-bearing counts and analysis "
        f"timedActions coord-bearing counts:\nparser: {dict(parser_counts)}\n"
        f"analysis: {dict(analysis_counts)}"
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
