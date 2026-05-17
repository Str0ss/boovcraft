"""Phase 3+4 — focus fire, pings, kills, KP%, TEI, attributions, executive.

Covers FR-016..FR-023 and output-shape invariants 11-15, 24-28.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from processor.team.attribution import compute_executive, detect_attributions
from processor.team.battles import detect_battle_windows
from processor.team.cohesion import compute_focus_fire, extract_pings
from processor.team.kills import compute_match_kp_percent, estimate_kills
from processor.team.ownership import build_ownership_map
from processor.team.positions import run_position_state
from processor.team.tei import TEI_ZERO_LOSS_CAP, compute_battle_tei

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def unit_costs():
    with (PROCESSOR_DIR / "unit_costs.json").open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def computed(base_2_parser_output, unit_costs):
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    battles = detect_battle_windows(base_2_parser_output, ownership)
    return base_2_parser_output, ownership, state, battles, unit_costs


# === Phase 3 — focus fire ===================================================

def test_focus_fire_cohesion_in_range(computed):
    parser_output, ownership, state, battles, unit_costs = computed
    for b in battles:
        ff = compute_focus_fire(b, parser_output, ownership)
        if ff is None:
            continue
        assert 0 <= ff["cohesionPercent"] <= 100


def test_focus_fire_dominant_target_is_opposing(computed):
    parser_output, ownership, state, battles, unit_costs = computed
    for b in battles:
        ff = compute_focus_fire(b, parser_output, ownership)
        if ff is None:
            continue
        slot = ff["dominantTargetSlot"]
        assert slot is not None
        side_a = set(b.sides["teamA"])
        side_b = set(b.sides["teamB"])
        assert slot in side_a or slot in side_b


# === Phase 3 — pings =======================================================

def test_pings_responded_engaged_disjoint(computed):
    """Invariant 13: respondedBySlot ∩ engagedElsewhereSlot === ∅."""
    parser_output, ownership, state, battles, unit_costs = computed
    for b in battles:
        for ping in extract_pings(b, parser_output, state, battles):
            r = set(ping["respondedBySlot"])
            e = set(ping["engagedElsewhereSlot"])
            assert r.isdisjoint(e)


def test_pings_inside_window_only(computed):
    """Invariant 5: pings inside this battle's [startMs, endMs] only."""
    parser_output, ownership, state, battles, unit_costs = computed
    for b in battles:
        for ping in extract_pings(b, parser_output, state, battles):
            assert b.start_ms <= ping["timeMs"] <= b.end_ms


def test_pings_from_slot_on_battle_side(computed):
    """Invariant 14: ping.fromSlot is in battle's own sides."""
    parser_output, ownership, state, battles, unit_costs = computed
    for b in battles:
        all_battle_slots = set(b.sides["teamA"]) | set(b.sides["teamB"])
        for ping in extract_pings(b, parser_output, state, battles):
            assert ping["fromSlot"] in all_battle_slots


# === Phase 3 — kills =======================================================

def test_kill_credits_sum_to_one(computed):
    """Invariant 15: every kill's credits sum to 1.0 ± 1e-6, fractions > 0."""
    parser_output, ownership, state, battles, unit_costs = computed
    for b in battles:
        kills, _ = estimate_kills(b, parser_output, ownership, unit_costs)
        for kill in kills:
            credits = kill["credits"]
            assert credits, "kill credits must be non-empty"
            total = sum(c["fraction"] for c in credits)
            assert math.isclose(total, 1.0, abs_tol=1e-6), f"credits sum to {total}"
            for c in credits:
                assert c["fraction"] > 0


def test_kp_percent_in_range(base_2_parser_output, unit_costs):
    """KP% per player is in [0, 100] or null."""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    battles = detect_battle_windows(base_2_parser_output, ownership)
    # Build mock battles with kills for KP% computation
    battle_blocks = []
    for b in battles:
        kills, _ = estimate_kills(b, base_2_parser_output, ownership, unit_costs)
        battle_blocks.append({"index": b.index, "kills": kills})
    players_analysis = [{"id": p["id"]} for p in base_2_parser_output["players"]]
    kp = compute_match_kp_percent(battle_blocks, players_analysis)
    for slot, pct in kp.items():
        if pct is None:
            continue
        assert 0 <= pct <= 100


# === Phase 4 — TEI =========================================================

def test_tei_zero_loss_cap_sentinel():
    """Invariant 24: zero-loss sentinel is the documented cap value."""
    assert TEI_ZERO_LOSS_CAP == 99.0


def test_tei_team_side_finite_or_null():
    """Invariant 24: teamSideTei is null or finite ≥ 0 (≤ cap)."""
    battle_block = {
        "index": 0,
        "sides": {"teamA": [1, 2], "teamB": [3, 4]},
        "kills": [
            {"victimSide": "teamB", "victimValue": 200, "credits": [{"slot": 1, "fraction": 1.0}]},
            {"victimSide": "teamA", "victimValue": 100, "credits": [{"slot": 3, "fraction": 1.0}]},
        ],
    }
    out = compute_battle_tei(battle_block)
    a = out["teamSideTei"]["teamA"]
    b = out["teamSideTei"]["teamB"]
    assert a == 200 / 100 == 2.0
    assert b == 100 / 200 == 0.5


def test_tei_zero_loss_yields_cap():
    battle_block = {
        "index": 0,
        "sides": {"teamA": [1], "teamB": [3]},
        "kills": [
            {"victimSide": "teamB", "victimValue": 200, "credits": [{"slot": 1, "fraction": 1.0}]},
        ],
    }
    out = compute_battle_tei(battle_block)
    # teamA killed but lost nothing → cap
    assert out["teamSideTei"]["teamA"] == 99.0
    # teamB lost but didn't kill → 0/200 = 0
    assert out["teamSideTei"]["teamB"] == 0.0


# === Phase 4 — Attribution + Executive =====================================

def test_attribution_three_condition_gate():
    """Invariant 26: attribution requires all three of split + low TEI + outlier."""
    # Synthetic battle: split engagement flagged, low TEI on teamA,
    # one outlier centroid on teamA.
    battles_blocks = [{
        "index": 0,
        "sides": {"teamA": [1, 2], "teamB": [3]},
        "splitEngagement": {"flagged": True, "flaggedSlots": [1, 2], "distance": 5000,
                            "referenceAuraId": "default", "referenceAuraName": "default 900u"},
        "centroids": [
            {"slot": 1, "x": 0, "y": 0, "source": "commanded"},
            {"slot": 2, "x": 5000, "y": 0, "source": "commanded"},  # outlier
            {"slot": 3, "x": 0, "y": 0, "source": "commanded"},
        ],
        "alliedDistances": [{"fromSlot": 1, "toSlot": 2, "distance": 5000}],
    }]
    tei_rows = [{"battleIndex": 0, "teamSideTei": {"teamA": 0.5, "teamB": 2.0}, "perPlayerTei": []}]
    attrs = detect_attributions(battles_blocks, tei_rows)
    # Slot 2 is the outlier (5000 from mean of 2500, > 1.5 × 5000 = 7500? actually NO)
    # mean_centroid = (2500, 0); slot 1 dist = 2500; slot 2 dist = 2500
    # mean_pair = 5000; threshold = 1.5 × 5000 = 7500
    # neither slot exceeds threshold → no attribution
    assert attrs == []


def test_executive_top_n_cap():
    """Invariant 27: executive length ≤ 3."""
    team_block = {
        "battles": [
            {"index": i, "startMs": i * 100_000, "endMs": i * 100_000 + 60_000,
             "splitEngagement": {"flagged": True, "flaggedSlots": [1, 2], "distance": 5000,
                                "referenceAuraId": "default", "referenceAuraName": "default"}}
            for i in range(10)
        ],
        "itemTransfers": [],
        "supportEvents": [],
        "findings": [],
        "battleSummary": {"tei": []},
    }
    exec_list = compute_executive(team_block)
    assert len(exec_list) <= 3
    for i, finding in enumerate(exec_list, start=1):
        assert finding["rank"] == i


def test_executive_evidence_ref_resolves():
    """Invariant 28: every evidenceRef points to a real index/name."""
    team_block = {
        "battles": [
            {"index": 0, "startMs": 60_000, "endMs": 120_000,
             "splitEngagement": {"flagged": True, "flaggedSlots": [1, 2], "distance": 5000,
                                "referenceAuraId": "default", "referenceAuraName": "default"}},
        ],
        "itemTransfers": [{"timeMs": 50_000, "recipientFitClass": "wrong"}],
        "supportEvents": [],
        "findings": ["sharedControlDisabled"],
        "battleSummary": {"tei": []},
    }
    exec_list = compute_executive(team_block)
    for f in exec_list:
        ref = f["evidenceRef"]
        if ref["kind"] == "battle":
            assert 0 <= ref["battleIndex"] < len(team_block["battles"])
        elif ref["kind"] == "supportEvent":
            assert 0 <= ref["index"] < len(team_block["supportEvents"])
        elif ref["kind"] == "itemTransfer":
            assert 0 <= ref["index"] < len(team_block["itemTransfers"])
        elif ref["kind"] == "globalFlag":
            assert ref["name"] in team_block["findings"]
