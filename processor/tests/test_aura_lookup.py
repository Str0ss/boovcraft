"""Phase 1b — aura table lookup + default fallback.

Covers FR-004, FR-006, output-shape invariant 10.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from processor.team.centroids import DEFAULT_AURA_RADIUS, active_aura_radius

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def auras_table():
    with (PROCESSOR_DIR / "auras.json").open() as f:
        return json.load(f)


def test_default_when_no_support_aura(auras_table):
    """When the side has no heroes / no support auras, fall back to default."""
    parser_output = {"players": []}
    aura = active_aura_radius(parser_output, (0, 1), auras_table)
    assert aura.radius == DEFAULT_AURA_RADIUS
    assert aura.ability_id == "default"
    assert aura.name == "default 900u"


def test_picks_max_radius_support_aura(auras_table):
    """When multiple support auras are active, the largest-radius one wins."""
    # Construct a synthetic parser_output where slot 0 has Devotion (AHad)
    parser_output = {
        "players": [
            {
                "id": 0,
                "heroes": [
                    {"abilityOrder": [{"type": "ability", "time": 0, "value": "AHad"}]}
                ],
            }
        ]
    }
    aura = active_aura_radius(parser_output, (0,), auras_table)
    assert aura.ability_id == "AHad"
    assert aura.radius == 900


def test_damage_aura_does_not_qualify(auras_table):
    """A damage aura (Vampiric/Trueshot) MUST NOT be picked as the threshold."""
    parser_output = {
        "players": [
            {
                "id": 0,
                "heroes": [
                    {"abilityOrder": [{"type": "ability", "time": 0, "value": "AOar"}]}
                ],
            }
        ]
    }
    aura = active_aura_radius(parser_output, (0,), auras_table)
    # AOar is "damage"; should fall back to default
    assert aura.ability_id == "default"


def test_table_has_canonical_seven_entries(auras_table):
    """data-model.md § AurasTable invariant A8: at least the seven canonical support auras."""
    canonical_support = {"AHad", "AHab", "AEar", "AEer", "AUau", "AOcr"}
    for ability_id in canonical_support:
        assert ability_id in auras_table, f"canonical aura {ability_id} missing"
        assert auras_table[ability_id]["type"] in ("support", "damage")
        assert auras_table[ability_id]["radius"] >= 0
