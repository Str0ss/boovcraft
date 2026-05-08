"""Hedging-discipline tests (FR-022..FR-026, SC-008).

Enforces:
 - Every inferred-kind event carries the documented `inferenceLabel`.
 - Every factual-kind event has `inferenceLabel: null`.
 - The events document contains zero outcome-vocabulary tokens
   (`killed`, `destroyed`, `stole`, `won`) used as factual claims.
"""

import json
import re
import sys
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


@pytest.fixture(
    scope="session", params=["base_1", "base_2"], ids=["base_1", "base_2"]
)
def events(request, base_1_events, base_2_events):
    return {"base_1": base_1_events, "base_2": base_2_events}[request.param]


INFERRED_KINDS = {
    "towerRushCandidate": "towerRushCandidate",
    "baseIncursion": "baseIncursionCandidate",
    "allyZoneCreeping": "allyZoneCreepingCandidate",
    "jointEngagement": "jointEngagementCandidate",
    "intensityPeak": "intensityPeakCandidate",
}

# Outcome-vocabulary tokens — words that imply combat resolution we
# cannot observe. Whole-word, case-insensitive (SC-008).
FORBIDDEN_TOKENS = ("killed", "destroyed", "stole", "won")


def test_inferred_kinds_have_inference_label(events):
    for e in events["events"]:
        if e["kind"] in INFERRED_KINDS:
            assert e["inferenceLabel"] == INFERRED_KINDS[e["kind"]], e


def test_factual_kinds_have_null_inference_label(events):
    for e in events["events"]:
        if e["kind"] not in INFERRED_KINDS:
            assert e["inferenceLabel"] is None, (
                f"factual kind {e['kind']} unexpectedly has label "
                f"{e['inferenceLabel']!r}: {e}"
            )


def test_no_forbidden_outcome_vocabulary(events):
    """SC-008. The serialized document must not contain any forbidden
    outcome-vocabulary token as a whole word.
    """
    text = json.dumps(events).lower()
    for token in FORBIDDEN_TOKENS:
        pattern = r"\b" + re.escape(token) + r"\b"
        match = re.search(pattern, text)
        assert match is None, (
            f"forbidden outcome token {token!r} appears in events document at "
            f"position {match.start()}: ...{text[max(0, match.start() - 30):match.end() + 30]}..."
        )


def test_every_event_records_thresholds_when_kind_uses_them(events):
    """FR-024: every event whose kind depends on a per-replay threshold
    exposes the threshold values used."""
    EXPECTED_THRESHOLDS = {
        "idlePeriod": {"idleMinGapMs"},
        "buildingRebuild": {"rebuildBucketSize"},
        "expoPlacement": {"homeRadius"},
        "creepingDeparture": {"homeRadius", "minDurationMs"},
        "towerRushCandidate": {"homeRadius"},
        "baseIncursion": {"opponentHomeRadius"},
        "allyZoneCreeping": {"allyHomeRadius", "minActionCount"},
        "jointEngagement": {"engagementRadius", "engagementTimeWindowSeconds"},
        "productionStall": {"productionStallMinGapMs"},
        "intensityPeak": {"windowSeconds", "peakSigma"},
        "resourceTransfer": {"burstGapMs"},
        # techMilestone, heroTeleport — no per-replay threshold.
    }
    for e in events["events"]:
        expected = EXPECTED_THRESHOLDS.get(e["kind"])
        if expected is None:
            continue
        actual = set(e.get("thresholds", {}).keys())
        missing = expected - actual
        assert not missing, (
            f"{e['kind']} event missing thresholds {missing}: {e}"
        )
