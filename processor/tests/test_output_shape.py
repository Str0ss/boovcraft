import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "processor"))

from analyze import build_analysis, load_mapping  # noqa: E402


def _strip_coords(obj):
    """Recursively remove every `x` and `y` key from a JSON-shaped object.

    Used by the byte-additivity check to verify the feature 006
    coord-retention change is strictly additive on the analyzer-output
    contract: post-006 output stripped of `x`/`y` MUST equal the
    pre-006 output.
    """
    if isinstance(obj, dict):
        return {k: _strip_coords(v) for k, v in obj.items() if k not in ("x", "y")}
    if isinstance(obj, list):
        return [_strip_coords(x) for x in obj]
    return obj


TOP_KEYS = {"match", "settings", "map", "players", "observers", "chat", "diagnostics"}
RACES_CHOSEN = {"H", "O", "U", "N", "R"}
RACES_DETECTED = {"H", "O", "U", "N"}
ID_RE = re.compile(r"^[A-Za-z0-9]{4}$")


@pytest.fixture(scope="session")
def empty_mapping():
    return {}


@pytest.fixture(scope="session")
def base_1_analysis(base_1_parser_output, empty_mapping):
    warned = set()
    return build_analysis(base_1_parser_output, empty_mapping, warned)


@pytest.fixture(scope="session")
def base_2_analysis(base_2_parser_output, empty_mapping):
    warned = set()
    return build_analysis(base_2_parser_output, empty_mapping, warned)


@pytest.fixture(
    scope="session", params=["base_1", "base_2"], ids=["base_1", "base_2"]
)
def analysis(request, base_1_analysis, base_2_analysis):
    return {"base_1": base_1_analysis, "base_2": base_2_analysis}[request.param]


def test_top_level_key_set_is_exact(analysis):
    assert set(analysis.keys()) == TOP_KEYS


def test_match_is_object(analysis):
    assert isinstance(analysis["match"], dict)


def test_settings_is_object(analysis):
    assert isinstance(analysis["settings"], dict)


def test_map_is_object(analysis):
    assert isinstance(analysis["map"], dict)


def test_diagnostics_is_object(analysis):
    assert isinstance(analysis["diagnostics"], dict)


def test_arrays_are_arrays(analysis):
    assert isinstance(analysis["players"], list)
    assert isinstance(analysis["observers"], list)
    assert isinstance(analysis["chat"], list)


def test_duration_is_non_negative_int(analysis):
    d = analysis["match"]["durationMs"]
    assert isinstance(d, int)
    assert d >= 0


def test_winner_shape(analysis):
    w = analysis["match"]["winner"]
    assert w is None or (isinstance(w, dict) and set(w.keys()) == {"teamId"} and isinstance(w["teamId"], int))


def test_players_have_full_key_set(analysis):
    expected = {
        "id",
        "name",
        "teamId",
        "color",
        "race",
        "raceDetected",
        "apm",
        "isWinner",
        "actions",
        "groupHotkeys",
        "heroes",
        "production",
        "resourceTransfers",
    }
    for p in analysis["players"]:
        assert set(p.keys()) == expected, f"player {p.get('id')} keys {set(p.keys())}"


def test_actions_have_full_key_set(analysis):
    expected = {"apmTimeline", "totals", "timedActions"}
    for p in analysis["players"]:
        assert set(p["actions"].keys()) == expected, (
            f"player {p['id']} actions keys {set(p['actions'].keys())}"
        )


def test_player_races(analysis):
    for p in analysis["players"]:
        assert p["race"] in RACES_CHOSEN
        assert p["raceDetected"] in RACES_DETECTED


def test_is_winner_matches_team(analysis):
    w = analysis["match"]["winner"]
    winning_team = None if w is None else w["teamId"]
    for p in analysis["players"]:
        assert p["isWinner"] == (winning_team is not None and p["teamId"] == winning_team)


def test_production_section_keys(analysis):
    for p in analysis["players"]:
        prod = p["production"]
        assert set(prod.keys()) == {"buildings", "units", "upgrades", "items"}
        for cat, section in prod.items():
            assert set(section.keys()) == {"order", "summary"}, f"player {p['id']} cat {cat}"
            assert isinstance(section["order"], list)
            assert isinstance(section["summary"], dict)


def _entity_refs(obj):
    """Yield every entity-ref dict (has `id`, `name`, `unknown`) found in obj."""
    if isinstance(obj, dict):
        keys = obj.keys()
        if {"id", "name", "unknown"}.issubset(keys) and isinstance(obj.get("id"), str):
            yield obj
        for v in obj.values():
            yield from _entity_refs(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _entity_refs(v)


def test_every_entity_ref_has_invariant_shape(analysis):
    saw_any = False
    for ref in _entity_refs(analysis):
        saw_any = True
        assert isinstance(ref["id"], str)
        assert ID_RE.match(ref["id"]), f"bad id: {ref['id']!r}"
        assert isinstance(ref["name"], str) and ref["name"] != ""
        assert isinstance(ref["unknown"], bool)
        if ref["unknown"]:
            assert ref["name"] == ref["id"]
    assert saw_any, "no entity refs found in analysis"


def test_chat_entry_keys(analysis):
    for c in analysis["chat"]:
        assert set(c.keys()) == {"playerId", "playerName", "mode", "text", "timeMs"}


def test_diagnostics_unmapped_is_dedup_list(analysis):
    unm = analysis["diagnostics"]["unmappedEntityIds"]
    assert isinstance(unm, list)
    seen = set()
    for e in unm:
        assert set(e.keys()) == {"category", "id"}
        assert isinstance(e["category"], str) and isinstance(e["id"], str)
        key = (e["category"], e["id"])
        assert key not in seen, f"duplicate diagnostic: {key}"
        seen.add(key)


def test_timestamp_fields_are_int(analysis):
    assert isinstance(analysis["match"]["durationMs"], int)
    for c in analysis["chat"]:
        assert isinstance(c["timeMs"], int)
    for p in analysis["players"]:
        for rt in p["resourceTransfers"]:
            assert isinstance(rt["timeMs"], int)
        for cat in ("buildings", "units", "upgrades", "items"):
            for entry in p["production"][cat]["order"]:
                assert isinstance(entry["timeMs"], int)
        for h in p["heroes"]:
            for ab in h["abilityOrder"]:
                assert isinstance(ab["timeMs"], int)


# ---------------------------------------------------------------
# Byte-additivity check (feature 006 coord retention; SC-005).
#
# Strips every `x` and `y` key from the post-006 analyzer output and
# asserts the result equals the pre-006 reference saved to /tmp/ by
# the feature 006 quickstart workflow. Skips with a clear message
# when the reference file is absent (e.g., a fresh checkout without
# the dev-workflow setup step) — the manual `quickstart.md` Step 1
# diff and CI integration cover those environments.
# ---------------------------------------------------------------

@pytest.fixture(
    scope="session", params=["base_1", "base_2"], ids=["base_1", "base_2"]
)
def fixture_name(request):
    return request.param


def test_post006_minus_coords_equals_pre006_reference(
    fixture_name, base_1_parser_output, base_2_parser_output
):
    pre_path = Path(f"/tmp/{fixture_name}.pre006.json")
    if not pre_path.exists():
        pytest.skip(
            f"pre-006 reference {pre_path} not found; "
            "save one with `cp sample_replays/{fixture}.w3g.analysis.json {pre_path}` "
            "from the pre-006 codebase to enable this byte-additivity check."
        )
    with pre_path.open("r", encoding="utf-8") as f:
        pre006 = json.load(f)

    # Re-run with the production mapping so the entity-name resolution
    # matches the saved pre-006 reference (which was emitted by the
    # CLI, which loads `processor/entity_names.json`).
    parser_output = (
        base_1_parser_output if fixture_name == "base_1" else base_2_parser_output
    )
    mapping = load_mapping()
    post006 = build_analysis(parser_output, mapping, set())
    stripped = _strip_coords(post006)

    # Normalize the two known per-build / per-run differences:
    #   - `parserParseTimeMs` is volatile (wall-clock).
    #   - `analyzerVersion` bumped from 0.1.0 to 0.2.0 in feature 006.
    # Both are diagnostics-block fields and are NOT covered by the
    # byte-additivity guarantee (which is about the data, not the
    # tooling stamp).
    for doc in (pre006, stripped):
        doc["diagnostics"]["parserParseTimeMs"] = 0
        doc["diagnostics"]["analyzerVersion"] = "<normalized>"
    assert stripped == pre006, (
        f"{fixture_name}: stripping x/y from post-006 analyzer output does NOT "
        "yield the pre-006 reference — coord retention is not strictly additive."
    )
