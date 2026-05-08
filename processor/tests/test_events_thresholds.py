"""Threshold-consistency tests (FR-024).

For every event that records per-replay threshold values, those
values must equal the per-replay values declared in the document's
top-level `diagnostics.thresholds` block. The cross-document
consistency catches drift between per-event and per-replay
recordings of the same threshold.
"""

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


# Mapping from per-event threshold key to per-replay diagnostics
# threshold key. A `None` value means the threshold is event-specific
# (e.g., per-player home radius) and not directly comparable.
PER_EVENT_TO_GLOBAL_THRESHOLD = {
    "idleMinGapMs": "idleMinGapMs",
    "productionStallMinGapMs": "productionStallMinGapMs",
    "burstGapMs": "transferBurstGapMs",
    "rebuildBucketSize": "rebuildBucketSize",
    "engagementRadius": "engagementRadius",
    "engagementTimeWindowSeconds": "engagementTimeWindowSeconds",
    "windowSeconds": "intensityWindowSeconds",
    "peakSigma": "intensityPeakSigma",
    # Per-player thresholds — not directly comparable to the global block:
    "homeRadius": None,
    "opponentHomeRadius": None,
    "allyHomeRadius": None,
    "minDurationMs": None,
    "minActionCount": None,
}


def test_per_event_thresholds_match_diagnostics_globals(events):
    globals_ = events["diagnostics"]["thresholds"]
    for e in events["events"]:
        for key, value in (e.get("thresholds") or {}).items():
            global_key = PER_EVENT_TO_GLOBAL_THRESHOLD.get(key)
            if global_key is None:
                continue
            assert global_key in globals_, (
                f"diagnostics.thresholds missing {global_key} "
                f"(referenced by event kind {e['kind']})"
            )
            assert value == globals_[global_key], (
                f"event-{e['kind']}.thresholds.{key}={value} "
                f"does not match diagnostics.thresholds.{global_key}={globals_[global_key]}"
            )


def test_per_player_home_radius_thresholds_are_positive(events):
    """Per-player thresholds aren't directly comparable, but they
    should at least be non-negative numbers."""
    for e in events["events"]:
        for key in ("homeRadius", "opponentHomeRadius", "allyHomeRadius"):
            v = (e.get("thresholds") or {}).get(key)
            if v is None:
                continue
            assert isinstance(v, (int, float))
            assert v >= 0
