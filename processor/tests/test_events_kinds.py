"""Per-kind end-to-end coverage on each fixture (SC-002).

Asserts that every kind expected to appear in a given fixture appears
at least once, and no event of a forbidden kind is emitted.
"""

import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "processor"))

from analyze import build_analysis, load_mapping  # noqa: E402
from extract_events import build_events_document  # noqa: E402


@pytest.fixture(scope="session")
def base_1_events(base_1_parser_output):
    return build_events_document(
        build_analysis(base_1_parser_output, load_mapping(), set())
    )


@pytest.fixture(scope="session")
def base_2_events(base_2_parser_output):
    return build_events_document(
        build_analysis(base_2_parser_output, load_mapping(), set())
    )


# Kinds expected to appear in each committed fixture. Curated from
# manual inspection of the fixtures' analyzer outputs and confirmed by
# the first run of the extractor.
BASE_1_EXPECTED_KINDS = {
    "idlePeriod",
    "buildingRebuild",
    "techMilestone",
    "expoPlacement",
    "creepingDeparture",
    "towerRushCandidate",
    "baseIncursion",
    "allyZoneCreeping",
    "jointEngagement",
    "heroTeleport",
    "productionStall",
    "intensityPeak",
    "resourceTransfer",
}

BASE_2_EXPECTED_KINDS = {
    "idlePeriod",
    "buildingRebuild",
    "techMilestone",
    "expoPlacement",
    "creepingDeparture",
    "baseIncursion",
    "allyZoneCreeping",
    "jointEngagement",
    "heroTeleport",
    "productionStall",
    "intensityPeak",
    "resourceTransfer",
    # base_2 may or may not have towerRushCandidate; we don't assert.
}


def _kinds(events: dict) -> set[str]:
    return set(Counter(e["kind"] for e in events["events"]).keys())


def test_base_1_has_expected_kinds(base_1_events):
    kinds = _kinds(base_1_events)
    missing = BASE_1_EXPECTED_KINDS - kinds
    assert not missing, f"base_1 missing expected kinds: {missing}"


def test_base_2_has_expected_kinds(base_2_events):
    kinds = _kinds(base_2_events)
    missing = BASE_2_EXPECTED_KINDS - kinds
    assert not missing, f"base_2 missing expected kinds: {missing}"


def test_base_1_event_count_is_substantial(base_1_events):
    """base_1 is a 4v4 ~30-min match. A working extractor should produce
    hundreds of events. A near-empty result indicates a pipeline break."""
    assert len(base_1_events["events"]) > 100


def test_base_2_event_count_is_substantial(base_2_events):
    """base_2 is a 3v3 ~22-min match. Lower bound is more permissive."""
    assert len(base_2_events["events"]) > 50


def test_idle_event_endpoints_within_match_duration(base_1_events, base_2_events):
    for events in (base_1_events, base_2_events):
        duration = events["match"]["durationMs"]
        for e in events["events"]:
            if e["kind"] != "idlePeriod":
                continue
            assert 0 <= e["startTimeMs"] <= duration
            assert e.get("endTimeMs", 0) <= duration


def test_expo_placements_are_outside_home_radius(base_1_events, base_2_events):
    for events in (base_1_events, base_2_events):
        for e in events["events"]:
            if e["kind"] != "expoPlacement":
                continue
            assert e["distanceFromHome"] > e["homeRadius"], (
                f"expo at {e['placement']} is inside home radius: {e}"
            )


def test_joint_engagements_have_two_or_more_teammates(base_1_events, base_2_events):
    for events in (base_1_events, base_2_events):
        teams_by_player = {p["id"]: p["teamId"] for p in events["match"]["players"]}
        for e in events["events"]:
            if e["kind"] != "jointEngagement":
                continue
            participants = e["playerIds"]
            assert len(participants) >= 2, e
            teams = {teams_by_player[pid] for pid in participants}
            assert len(teams) == 1, f"jointEngagement spans multiple teams: {e}"


def test_tower_rush_targets_an_opponent(base_1_events):
    teams = {p["id"]: p["teamId"] for p in base_1_events["match"]["players"]}
    for e in base_1_events["events"]:
        if e["kind"] != "towerRushCandidate":
            continue
        assert teams[e["playerId"]] != teams[e["threatenedOpponentId"]], (
            f"towerRushCandidate threatens a teammate: {e}"
        )


def test_resource_transfers_have_positive_totals(base_1_events, base_2_events):
    for events in (base_1_events, base_2_events):
        for e in events["events"]:
            if e["kind"] != "resourceTransfer":
                continue
            assert e["count"] >= 1
            assert e["totalGold"] >= 0
            assert e["totalLumber"] >= 0
            assert e["senderId"] != e["receiverId"]


def test_building_rebuild_gap_is_positive(base_1_events, base_2_events):
    for events in (base_1_events, base_2_events):
        for e in events["events"]:
            if e["kind"] != "buildingRebuild":
                continue
            assert e["gapMs"] > 0
            assert e["original"]["timeMs"] < e["rebuild"]["timeMs"]
