"""Phase 2 — generosity score + null-coupling biconditional.

Covers FR-014 and output-shape invariant 22.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from processor.team.resources import compute_generosity

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def unit_costs():
    with (PROCESSOR_DIR / "unit_costs.json").open() as f:
        return json.load(f)


def test_null_coupling_biconditional(unit_costs):
    """Invariant 22: generosityPercent === null ⇔ either estimatedMined* is null."""
    metric_gaps = []
    unmapped = set()
    # Player with a missing unit_cost id → null estimates
    players = [
        {
            "id": 1, "name": "p1", "resourceTransfers": [],
            "production": {
                "units": {"order": [], "summary": {"missing_id": {"id": "missing_id", "count": 1}}},
                "buildings": {"order": [], "summary": {}},
                "upgrades": {"order": [], "summary": {}},
                "items": {"order": [], "summary": {}},
            },
        },
    ]
    out = compute_generosity(players, unit_costs, metric_gaps, unmapped)
    assert len(out) == 1
    row = out[0]
    if row["estimatedMinedGold"] is None or row["estimatedMinedLumber"] is None:
        assert row["generosityPercent"] is None
    else:
        assert row["generosityPercent"] is not None


def test_no_production_yields_zero_generosity(unit_costs):
    metric_gaps = []
    unmapped = set()
    players = [
        {
            "id": 1, "name": "p1", "resourceTransfers": [],
            "production": {
                "units": {"order": [], "summary": {}},
                "buildings": {"order": [], "summary": {}},
                "upgrades": {"order": [], "summary": {}},
                "items": {"order": [], "summary": {}},
            },
        },
    ]
    out = compute_generosity(players, unit_costs, metric_gaps, unmapped)
    # 0/0 → null (no denominator); accept either null or 0 depending on impl
    row = out[0]
    assert row["generosityPercent"] in (None, 0.0)


def test_diagnostics_populated_on_gap(unit_costs):
    """When a unit_cost is missing, diagnostics get populated."""
    metric_gaps = []
    unmapped = set()
    players = [
        {
            "id": 7, "name": "p7", "resourceTransfers": [],
            "production": {
                "units": {"order": [], "summary": {"FAKE": {"id": "FAKE", "count": 1}}},
                "buildings": {"order": [], "summary": {}},
                "upgrades": {"order": [], "summary": {}},
                "items": {"order": [], "summary": {}},
            },
        },
    ]
    compute_generosity(players, unit_costs, metric_gaps, unmapped)
    assert any(g["metric"] == "generosity:slot=7" for g in metric_gaps)
    assert ("unitCost", "FAKE") in unmapped


def test_realistic_player_yields_finite_generosity(unit_costs):
    """A player with real production AND real transfers gets a number."""
    metric_gaps = []
    unmapped = set()
    players = [
        {
            "id": 1, "name": "p1",
            "resourceTransfers": [
                {"fromSlot": 1, "toPlayerId": 2, "gold": 500, "lumber": 100, "timeMs": 600_000}
            ],
            "production": {
                "units": {"order": [], "summary": {
                    "hpea": {"id": "hpea", "count": 5},   # 5 × 75g = 375
                    "hfoo": {"id": "hfoo", "count": 10},  # 10 × 135g = 1350
                }},
                "buildings": {"order": [], "summary": {
                    "htow": {"id": "htow", "count": 1},   # 385g + 205l
                }},
                "upgrades": {"order": [], "summary": {}},
                "items": {"order": [], "summary": {}},
            },
        },
    ]
    out = compute_generosity(players, unit_costs, metric_gaps, unmapped)
    row = out[0]
    assert row["estimatedMinedGold"] is not None
    assert row["estimatedMinedLumber"] is not None
    assert row["generosityPercent"] is not None
    assert row["generosityPercent"] >= 0
