"""Structural shape tests for the events JSON document.

Verifies the contract in
specs/006-event-extraction/contracts/events-output-shape.md.
"""

import re
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
    analysis = build_analysis(base_1_parser_output, load_mapping(), set())
    return build_events_document(analysis)


@pytest.fixture(scope="session")
def base_2_events(base_2_parser_output):
    analysis = build_analysis(base_2_parser_output, load_mapping(), set())
    return build_events_document(analysis)


@pytest.fixture(
    scope="session", params=["base_1", "base_2"], ids=["base_1", "base_2"]
)
def events(request, base_1_events, base_2_events):
    return {"base_1": base_1_events, "base_2": base_2_events}[request.param]


ID_RE = re.compile(r"^[0-9a-f]{16}$")

KIND_LABELS = {
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

INFERRED_KIND_LABELS = {
    "towerRushCandidate": "towerRushCandidate",
    "baseIncursion": "baseIncursionCandidate",
    "allyZoneCreeping": "allyZoneCreepingCandidate",
    "jointEngagement": "jointEngagementCandidate",
    "intensityPeak": "intensityPeakCandidate",
}


def test_top_level_keys_exact(events):
    assert set(events.keys()) == {"match", "events", "diagnostics"}


def test_match_block_shape(events):
    m = events["match"]
    assert isinstance(m["parserId"], str) and m["parserId"]
    assert isinstance(m["durationMs"], int)
    assert m["durationMs"] >= 0
    assert isinstance(m["players"], list)
    for p in m["players"]:
        assert set(p.keys()) >= {"id", "teamId", "name"}


def test_every_event_has_required_fields(events):
    for e in events["events"]:
        for key in ("id", "kind", "startTimeMs", "participants", "inferenceLabel", "thresholds"):
            assert key in e, f"event missing {key}: {e}"
        assert ID_RE.match(e["id"]), f"bad id: {e['id']}"
        assert e["kind"] in KIND_LABELS, f"unknown kind: {e['kind']}"
        assert isinstance(e["startTimeMs"], int)
        assert e["startTimeMs"] >= 0
        assert isinstance(e["participants"], list)
        assert all(isinstance(p, int) for p in e["participants"])
        assert isinstance(e["thresholds"], dict)


def test_events_sorted_chronologically(events):
    last_key = (-1, "", ())
    for e in events["events"]:
        key = (e["startTimeMs"], e["kind"], tuple(sorted(e["participants"])))
        assert key >= last_key, f"event out of order: {e}"
        last_key = key


def test_inferred_kinds_have_matching_label(events):
    for e in events["events"]:
        if e["kind"] in INFERRED_KIND_LABELS:
            assert e["inferenceLabel"] == INFERRED_KIND_LABELS[e["kind"]], (
                f"{e['kind']} expected label {INFERRED_KIND_LABELS[e['kind']]} got {e['inferenceLabel']}"
            )
        else:
            assert e["inferenceLabel"] is None, (
                f"factual kind {e['kind']} unexpectedly has label {e['inferenceLabel']}"
            )


def test_event_ids_are_unique(events):
    ids = [e["id"] for e in events["events"]]
    counts = Counter(ids)
    duplicates = {i: c for i, c in counts.items() if c > 1}
    assert not duplicates, f"duplicate ids: {duplicates}"


def test_diagnostics_event_counts_sum_matches_events_len(events):
    counts = events["diagnostics"]["eventCounts"]
    assert sum(counts.values()) == len(events["events"])


def test_diagnostics_required_keys(events):
    d = events["diagnostics"]
    for key in ("extractorVersion", "parserId", "players", "thresholds", "eventCounts"):
        assert key in d, f"diagnostics missing {key}"
    for pid_methods in d["players"].values():
        assert "homeDerivation" in pid_methods
        assert "homeRadiusDerivation" in pid_methods


def test_match_parser_id_matches_diagnostics(events):
    assert events["match"]["parserId"] == events["diagnostics"]["parserId"]
