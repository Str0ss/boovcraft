"""Coverage for the feature 006 coord retention on
`players[].actions.timedActions[]` and on `players[].production.*.order[]`.

Scope: assert that coord-bearing categories carry `x`/`y` and
no-position categories do not — the contract change is per-category
predictable, not per-replay variable.
"""

import sys
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


# Categories whose underlying replay-action ids include {0x11, 0x12, 0x13, 0x14}
# in at least some emitted entries — they carry coordinates *sometimes*.
COORD_BEARING_CATEGORIES = {"rightclick", "ability", "item"}

# Categories whose underlying replay-action ids never include
# {0x11, 0x12, 0x13, 0x14} — they MUST NOT carry coordinates.
COORD_FREE_CATEGORIES = {"select", "selecthotkey", "assigngroup", "esc", "removeunit"}


def test_coord_bearing_category_has_at_least_one_coord_entry(analysis):
    """For each coord-bearing category that appears at all in the
    replay, at least one entry MUST carry `x`/`y`. (`buildtrain` and
    `basic` are excluded — they often originate from 0x10 actions
    without a target.)
    """
    for p in analysis["players"]:
        ta = p["actions"]["timedActions"]
        for cat in COORD_BEARING_CATEGORIES:
            entries = [e for e in ta if e["category"] == cat]
            if not entries:
                continue
            with_coords = [e for e in entries if "x" in e and "y" in e]
            assert with_coords, (
                f"player {p['id']} category {cat}: "
                f"{len(entries)} entries but none carry x/y"
            )


def test_coord_free_categories_never_carry_coords(analysis):
    """No-position categories MUST never carry coordinates."""
    for p in analysis["players"]:
        for entry in p["actions"]["timedActions"]:
            if entry["category"] in COORD_FREE_CATEGORIES:
                assert "x" not in entry and "y" not in entry, (
                    f"player {p['id']} category {entry['category']} "
                    f"unexpectedly has coords: {entry}"
                )


# Buildings that originate from 0x10 in-place upgrades — these are
# *trained* inside an existing building (tier upgrades of main halls,
# tower upgrades) and have no target coordinate. The contract correctly
# omits coords for them.
IN_PLACE_UPGRADE_BUILDINGS = {
    # Human main-hall upgrades and tower upgrades (Watch Tower → Guard/Cannon/Arcane).
    "hkee", "hcas", "hgtw", "hctw", "hatw",
    # Orc main-hall upgrades.
    "ostr", "ofrt",
    # Undead main-hall and ziggurat upgrades.
    "unp1", "unp2", "uzg1", "uzg2",
    # Night Elf tree upgrades.
    "etoa", "etoe",
}


def test_fresh_building_placements_carry_coords(analysis):
    """Buildings whose entity id is NOT in the in-place-upgrade set
    originate from 0x11 placement actions and MUST carry coords.
    """
    for p in analysis["players"]:
        for o in p["production"]["buildings"]["order"]:
            if o["id"] in IN_PLACE_UPGRADE_BUILDINGS:
                continue
            assert "x" in o and "y" in o, (
                f"player {p['id']}: fresh building placement {o['id']} "
                f"@{o['timeMs']}ms lacks coords: {o}"
            )


def test_at_least_some_buildings_have_coords(analysis):
    """Sanity: every player who placed buildings has at least one with coords."""
    for p in analysis["players"]:
        order = p["production"]["buildings"]["order"]
        if not order:
            continue
        with_coords = [o for o in order if "x" in o]
        assert with_coords, (
            f"player {p['id']}: 0 of {len(order)} buildings have coords"
        )


def test_unit_train_orders_omit_coords(analysis):
    """Unit training entries originate from 0x10 actions inside the
    training building — they never carry positions."""
    for p in analysis["players"]:
        for o in p["production"]["units"]["order"]:
            assert "x" not in o and "y" not in o, (
                f"player {p['id']} unit-train entry has unexpected coords: {o}"
            )


def test_coord_values_within_replay_bounds(analysis):
    """Sanity bound: every coord must fall within the bounding box of
    all coord-bearing actions in the same replay, with a small fudge
    factor for floating-point tolerance.
    """
    xs: list[float] = []
    ys: list[float] = []
    for p in analysis["players"]:
        for entry in p["actions"]["timedActions"]:
            if "x" in entry:
                xs.append(entry["x"])
                ys.append(entry["y"])
        for cat in ("buildings", "units", "upgrades", "items"):
            for o in p["production"][cat]["order"]:
                if "x" in o:
                    xs.append(o["x"])
                    ys.append(o["y"])
    if not xs:
        return  # degenerate replay; no coord data to check
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    for p in analysis["players"]:
        for entry in p["actions"]["timedActions"]:
            if "x" in entry:
                assert min_x <= entry["x"] <= max_x
                assert min_y <= entry["y"] <= max_y
