"""Pure-helper unit tests for `processor/extract_events.py`.

Inputs are derived from the committed fixture replays' analyzer
output — never hand-rolled (Principle IV).
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "processor"))

from analyze import build_analysis, load_mapping  # noqa: E402
from extract_events import (  # noqa: E402
    HOME_RADIUS_DIAGONAL_FRACTION,
    _compute_map_active_region,
    _derive_player_home_radii,
    _derive_player_homes,
    _emit_transfer_burst,
    _engagement_radius,
    _engagement_time_scale,
    _event_id,
    _load_actions_dataframe,
    _rebuild_bucket_size,
)


@pytest.fixture(scope="session")
def base_1_analysis(base_1_parser_output):
    return build_analysis(base_1_parser_output, load_mapping(), set())


def test_event_id_deterministic():
    a = _event_id("idlePeriod", 1000, [3], "")
    b = _event_id("idlePeriod", 1000, [3], "")
    assert a == b
    assert len(a) == 16
    assert all(c in "0123456789abcdef" for c in a)


def test_event_id_kind_disambiguates():
    a = _event_id("idlePeriod", 1000, [3], "")
    b = _event_id("expoPlacement", 1000, [3], "")
    assert a != b


def test_event_id_participant_order_invariant():
    a = _event_id("jointEngagement", 1000, [3, 7], "")
    b = _event_id("jointEngagement", 1000, [7, 3], "")
    assert a == b


def test_event_id_disambiguator_distinguishes():
    a = _event_id("buildingRebuild", 1000, [3], "hbar@10,20")
    b = _event_id("buildingRebuild", 1000, [3], "hbar@11,20")
    assert a != b


def test_compute_map_active_region_on_fixture(base_1_analysis):
    df = _load_actions_dataframe(base_1_analysis)
    min_x, max_x, min_y, max_y, diag = _compute_map_active_region(df)
    assert min_x < max_x
    assert min_y < max_y
    assert diag > 0
    assert diag == pytest.approx(((max_x - min_x) ** 2 + (max_y - min_y) ** 2) ** 0.5)


def test_engagement_radius_scales_with_diagonal(base_1_analysis):
    df = _load_actions_dataframe(base_1_analysis)
    _, _, _, _, diag = _compute_map_active_region(df)
    eps = _engagement_radius(diag)
    assert eps == pytest.approx(0.05 * diag)


def test_engagement_time_scale_is_radius_per_window(base_1_analysis):
    df = _load_actions_dataframe(base_1_analysis)
    _, _, _, _, diag = _compute_map_active_region(df)
    scale = _engagement_time_scale(diag)
    assert scale == pytest.approx(_engagement_radius(diag) / 5)


def test_rebuild_bucket_size_is_diagonal_fraction(base_1_analysis):
    df = _load_actions_dataframe(base_1_analysis)
    _, _, _, _, diag = _compute_map_active_region(df)
    bucket = _rebuild_bucket_size(diag)
    assert bucket == pytest.approx(0.01 * diag)


def test_derive_homes_marks_primary_for_full_data(base_1_analysis):
    df = _load_actions_dataframe(base_1_analysis)
    homes, methods = _derive_player_homes(base_1_analysis, df)
    # Every base_1 player has dozens of building placements in the
    # first 120 s — all should derive via the primary path.
    primary = [pid for pid, m in methods.items() if m == "primary"]
    assert len(primary) == len(base_1_analysis["players"])
    for pid, (hx, hy) in homes.items():
        assert isinstance(hx, float)
        assert isinstance(hy, float)


def test_home_radius_floor_kicks_in_for_tight_openings(base_1_analysis):
    df = _load_actions_dataframe(base_1_analysis)
    _, _, _, _, diag = _compute_map_active_region(df)
    homes, _ = _derive_player_homes(base_1_analysis, df)
    radii, _ = _derive_player_home_radii(base_1_analysis, homes, diag)
    floor = HOME_RADIUS_DIAGONAL_FRACTION * diag
    for r in radii.values():
        assert r >= floor - 1e-6


def test_emit_transfer_burst_aggregates():
    transfers = [
        {"timeMs": 100, "gold": 50, "lumber": 0},
        {"timeMs": 200, "gold": 0, "lumber": 30},
        {"timeMs": 250, "gold": 100, "lumber": 0},
    ]
    e = _emit_transfer_burst(1, 2, transfers)
    assert e["kind"] == "resourceTransfer"
    assert e["startTimeMs"] == 100
    assert e["endTimeMs"] == 250
    assert e["count"] == 3
    assert e["totalGold"] == 150
    assert e["totalLumber"] == 30


def test_emit_transfer_burst_singleton_omits_end():
    e = _emit_transfer_burst(1, 2, [{"timeMs": 500, "gold": 75, "lumber": 25}])
    assert e["startTimeMs"] == 500
    assert "endTimeMs" not in e
    assert e["count"] == 1
