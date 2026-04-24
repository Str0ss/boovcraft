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


def test_base_1_has_8_players(base_1_analysis):
    assert len(base_1_analysis["players"]) == 8


def test_base_1_chat_count(base_1_analysis):
    assert len(base_1_analysis["chat"]) == 81
    for c in base_1_analysis["chat"]:
        assert c["text"] != ""


def test_base_1_game_type(base_1_analysis):
    assert base_1_analysis["match"]["gameType"] == "4on4"


def test_observers_passthrough(base_1_analysis, base_1_parser_output, base_2_analysis, base_2_parser_output):
    assert base_1_analysis["observers"] == list(base_1_parser_output["observers"])
    assert base_2_analysis["observers"] == list(base_2_parser_output["observers"])


def test_base_2_has_6_players(base_2_analysis):
    assert len(base_2_analysis["players"]) == 6


def test_base_2_chat_is_empty_array(base_2_analysis):
    assert base_2_analysis["chat"] == []


def test_base_2_game_type(base_2_analysis):
    assert base_2_analysis["match"]["gameType"] == "3on3"


def test_player_passthrough_fields(base_1_analysis, base_1_parser_output):
    src = {p["id"]: p for p in base_1_parser_output["players"]}
    for p in base_1_analysis["players"]:
        s = src[p["id"]]
        assert p["name"] == s["name"]
        assert p["color"] == s["color"]
        assert p["teamId"] == s["teamid"]


def test_diagnostics_parser_id_verbatim(base_1_analysis, base_1_parser_output):
    assert base_1_analysis["diagnostics"]["parserId"] == base_1_parser_output["id"]


def test_diagnostics_parse_time_passthrough(base_1_analysis, base_1_parser_output):
    assert base_1_analysis["diagnostics"]["parserParseTimeMs"] == base_1_parser_output["parseTime"]


def test_apm_timeline_has_bucket_width(base_1_analysis, base_1_parser_output):
    expected_width = base_1_parser_output["apm"]["trackingInterval"]
    for p in base_1_analysis["players"]:
        assert p["actions"]["apmTimeline"]["bucketWidthMs"] == expected_width
        assert isinstance(p["actions"]["apmTimeline"]["buckets"], list)
