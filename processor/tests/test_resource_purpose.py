"""Phase 2 — resource transfer purpose-hint classification.

Covers FR-012 and output-shape invariant 21.
"""

from __future__ import annotations

from processor.team.resources import annotate_transfers


def test_purpose_hint_enum_base_2(base_2_parser_output):
    """Invariant 21: every purposeHint ∈ closed enum."""
    # Mock players_analysis with the same shape analyze.py produces
    players = []
    for p in base_2_parser_output["players"]:
        slot = p["id"]
        players.append({
            "id": slot,
            "name": p.get("name", ""),
            "resourceTransfers": [
                {"fromSlot": slot, "toPlayerId": t["playerId"], "toPlayerName": t["playerName"],
                 "gold": t["gold"], "lumber": t["lumber"], "timeMs": t["msElapsed"]}
                for t in p.get("resourceTransfers", []) or []
            ],
            "production": {
                "buildings": {"order": [], "summary": {}},
                "units": {"order": [], "summary": {}},
                "upgrades": {"order": [], "summary": {}},
                "items": {"order": [], "summary": {}},
            },
        })
    out = annotate_transfers(base_2_parser_output, players)
    valid = {"tierUpAssist", "baseDefense", "lateGameTopUp", "none"}
    for t in out:
        assert t["purposeHint"] in valid, t["purposeHint"]


def test_late_game_classification(base_2_parser_output):
    """A transfer past 75% of match duration with no other classifier
    matching MUST be 'lateGameTopUp'."""
    duration = base_2_parser_output["duration"]
    late_threshold = duration * 0.75
    # Create a synthetic transfer at 80% of the match
    players = [
        {"id": 1, "name": "p1", "resourceTransfers": [{
            "fromSlot": 1, "toPlayerId": 2, "toPlayerName": "p2",
            "gold": 100, "lumber": 0, "timeMs": int(duration * 0.8),
        }], "production": {"buildings": {"order": [], "summary": {}}, "units": {"order": [], "summary": {}}, "upgrades": {"order": [], "summary": {}}, "items": {"order": [], "summary": {}}}},
        {"id": 2, "name": "p2", "resourceTransfers": [], "production": {"buildings": {"order": [], "summary": {}}, "units": {"order": [], "summary": {}}, "upgrades": {"order": [], "summary": {}}, "items": {"order": [], "summary": {}}}},
    ]
    out = annotate_transfers(base_2_parser_output, players)
    assert len(out) == 1
    assert out[0]["purposeHint"] == "lateGameTopUp"
