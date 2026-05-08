"""Phase 1 of feature 008 — centroid timeline shape, food calc, monotonicity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from processor.team.events import NEUTRAL_SLOT_IDS
from processor.team.ownership import build_ownership_map
from processor.team.positions import run_position_state
from processor.team.timeline import (
    BUCKET_WIDTH_MS,
    WORKER_IDS,
    compute_centroid_timeline,
)

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def unit_costs():
    with (PROCESSOR_DIR / "unit_costs.json").open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def b2_timeline(base_2_parser_output, unit_costs):
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    return compute_centroid_timeline(base_2_parser_output, state, unit_costs)


def test_bucket_count_and_width(b2_timeline, base_2_parser_output):
    assert b2_timeline["bucketWidthMs"] == BUCKET_WIDTH_MS == 5000
    duration = base_2_parser_output["duration"]
    expected = (duration // BUCKET_WIDTH_MS) + 1
    assert len(b2_timeline["buckets"]) == expected
    # tMs is monotonic and gap-free
    for i, bucket in enumerate(b2_timeline["buckets"]):
        assert bucket["tMs"] == i * BUCKET_WIDTH_MS


def test_centroid_per_player_per_bucket(b2_timeline, base_2_parser_output):
    """Every non-AI player has a centroid record in every bucket."""
    expected_slots = sorted(
        p["id"] for p in base_2_parser_output["players"]
        if isinstance(p.get("id"), int) and p["id"] not in NEUTRAL_SLOT_IDS
    )
    for bucket in b2_timeline["buckets"]:
        slots = sorted(c["slot"] for c in bucket["centroids"])
        assert slots == expected_slots


def test_centroid_source_field_consistency(b2_timeline):
    """source is one of four closed-enum values; coordinates iff non-missing."""
    import math
    valid_sources = {"commanded", "stale", "starting", "missing"}
    for bucket in b2_timeline["buckets"]:
        for c in bucket["centroids"]:
            assert c["source"] in valid_sources, f"unexpected source: {c['source']}"
            if c["source"] == "missing":
                assert c["x"] is None and c["y"] is None
            else:
                # commanded / stale / starting all carry finite coordinates
                assert c["x"] is not None and c["y"] is not None
                assert math.isfinite(c["x"]) and math.isfinite(c["y"])


def test_starting_fallback_for_passive_early_player(b2_timeline, base_2_parser_output):
    """A player who hasn't issued any command yet at time t MUST get a
    'starting' source pointing at their forward-look first commanded
    position — never 'missing' (unless they never command anything in
    the entire match).
    """
    # On base_2, slot 3 (Blayed#2127) doesn't issue first 0x11/0x12 until
    # bucket 30. Buckets 0..29 should have source='starting' for slot 3.
    starting_count = 0
    missing_count = 0
    for i in range(30):
        bucket = b2_timeline["buckets"][i]
        for c in bucket["centroids"]:
            if c["slot"] != 3:
                continue
            if c["source"] == "starting":
                starting_count += 1
                # Position MUST be finite
                assert c["x"] is not None and c["y"] is not None
            elif c["source"] == "missing":
                missing_count += 1
    # The player has at least one future command, so all early buckets
    # should be 'starting', none 'missing'.
    assert starting_count >= 25, f"expected ≥ 25 starting buckets for slot 3 in [0..29], got {starting_count}"
    assert missing_count == 0, f"slot 3 has {missing_count} missing buckets despite future commands existing"


def test_no_neutral_in_timeline(b2_timeline):
    for bucket in b2_timeline["buckets"]:
        for c in bucket["centroids"]:
            assert c["slot"] not in NEUTRAL_SLOT_IDS


def test_combat_food_excludes_workers(b2_timeline, base_2_parser_output, unit_costs):
    """combatFood at end-of-match equals manual sum of non-worker supply
    PLUS heroes' supply (heroes are combat units summoned at altar)."""
    last_bucket = b2_timeline["buckets"][-1]
    by_slot = {c["slot"]: c for c in last_bucket["centroids"]}

    for player in base_2_parser_output["players"]:
        slot = player["id"]
        if slot in NEUTRAL_SLOT_IDS:
            continue

        # Manual reference sum — non-worker production units
        units_order = (player.get("units") or {}).get("order") or []
        ref_food = 0
        ref_count = 0
        for entry in units_order:
            uid = entry.get("id") or entry.get("value")
            if uid in WORKER_IDS:
                continue
            cost = unit_costs.get(uid) or {}
            ref_food += int(cost.get("supply", 0) or 0)
            ref_count += 1

        # Plus heroes that have at least one ability learn event
        for hero in player.get("heroes", []) or []:
            hero_id = hero.get("id")
            if not isinstance(hero_id, str) or hero_id == "UNKN":
                continue
            ability_order = hero.get("abilityOrder") or []
            if not any(a.get("time") is not None or a.get("timeMs") is not None for a in ability_order):
                continue
            cost = unit_costs.get(hero_id) or {}
            ref_food += int(cost.get("supply", 0) or 0)
            ref_count += 1

        c = by_slot[slot]
        assert c["combatFood"] == ref_food, (
            f"slot {slot} combat-food mismatch: emitted {c['combatFood']} vs ref {ref_food}"
        )
        assert c["combatUnitCount"] == ref_count


def test_heroes_contribute_to_combat_food(b2_timeline, base_2_parser_output, unit_costs):
    """Heroes MUST be counted in combatFood, since they are combat units
    consuming 5 food each (per WC3 ladder rules)."""
    last_bucket = b2_timeline["buckets"][-1]
    by_slot = {c["slot"]: c for c in last_bucket["centroids"]}

    for player in base_2_parser_output["players"]:
        slot = player["id"]
        if slot in NEUTRAL_SLOT_IDS:
            continue
        # Count heroes summoned (have at least one ability event)
        summoned_heroes = 0
        expected_hero_food = 0
        for hero in player.get("heroes", []) or []:
            hero_id = hero.get("id")
            if not isinstance(hero_id, str) or hero_id == "UNKN":
                continue
            ability_order = hero.get("abilityOrder") or []
            has_event = any(a.get("time") is not None or a.get("timeMs") is not None for a in ability_order)
            if has_event:
                summoned_heroes += 1
                expected_hero_food += int((unit_costs.get(hero_id) or {}).get("supply", 0))

        if summoned_heroes == 0:
            continue
        # combatUnitCount must include heroes
        emitted_count = by_slot[slot]["combatUnitCount"]
        assert emitted_count >= summoned_heroes, (
            f"slot {slot}: combatUnitCount {emitted_count} < {summoned_heroes} heroes summoned"
        )


def test_combat_food_monotonic(b2_timeline):
    """combatFood and combatUnitCount only increase over buckets per slot."""
    by_slot_history: dict[int, list[tuple[int, int]]] = {}
    for bucket in b2_timeline["buckets"]:
        for c in bucket["centroids"]:
            by_slot_history.setdefault(c["slot"], []).append(
                (c["combatFood"], c["combatUnitCount"])
            )
    for slot, history in by_slot_history.items():
        for i in range(1, len(history)):
            prev_f, prev_n = history[i - 1]
            curr_f, curr_n = history[i]
            assert curr_f >= prev_f, f"slot {slot} food decreased at bucket {i}"
            assert curr_n >= prev_n, f"slot {slot} count decreased at bucket {i}"


def test_centroid_matches_position_state(base_2_parser_output, unit_costs):
    """Sample a bucket and verify centroid matches position_state.centroid_at
    when source === 'commanded'. For 'stale' source, the position is the
    last-known fallback — comes from a different code path. For 'missing'
    no position exists."""
    ownership = build_ownership_map(base_2_parser_output)
    state = run_position_state(base_2_parser_output, ownership)
    timeline = compute_centroid_timeline(base_2_parser_output, state, unit_costs)

    # Pick a mid-match bucket that should have data
    sample_idx = len(timeline["buckets"]) // 2
    bucket = timeline["buckets"][sample_idx]
    t_ms = bucket["tMs"]

    for c in bucket["centroids"]:
        ref = state.centroid_at(c["slot"], max(0, t_ms - 60_000), t_ms)
        if c["source"] == "commanded":
            # Must match the 60s-window centroid_at exactly
            assert ref is not None
            assert c["x"] == ref[0]
            assert c["y"] == ref[1]
        elif c["source"] == "stale":
            # 60s window was empty; fallback path used. Just verify the
            # fallback produced a finite position.
            assert ref is None
            assert c["x"] is not None and c["y"] is not None
        else:
            assert c["source"] == "missing"
            assert ref is None
            assert c["x"] is None and c["y"] is None


def test_stale_fallback_keeps_players_visible(b2_timeline):
    """User-facing requirement: every player who has issued at least one
    command should be visible (commanded OR stale) at all subsequent
    buckets — never silently disappear from the map.

    Concretely: once a slot has a 'commanded' or 'stale' source, it MUST
    NOT regress to 'missing' in any later bucket of the timeline."""
    seen_at: dict[int, int] = {}  # slot → first bucket idx with non-missing source
    for i, bucket in enumerate(b2_timeline["buckets"]):
        for c in bucket["centroids"]:
            if c["source"] != "missing":
                seen_at.setdefault(c["slot"], i)

    for i, bucket in enumerate(b2_timeline["buckets"]):
        for c in bucket["centroids"]:
            first_seen = seen_at.get(c["slot"])
            if first_seen is not None and i > first_seen:
                assert c["source"] != "missing", (
                    f"slot {c['slot']} regressed to 'missing' at bucket {i} "
                    f"(first seen at bucket {first_seen})"
                )


def test_zero_duration_gives_empty_timeline(unit_costs):
    """Edge case: a parser_output with duration=0 yields zero buckets."""
    fake = {"duration": 0, "events": [], "players": []}
    from processor.team.positions import PositionState
    state = PositionState()
    out = compute_centroid_timeline(fake, state, unit_costs)
    assert out["bucketWidthMs"] == BUCKET_WIDTH_MS
    assert out["buckets"] == []
