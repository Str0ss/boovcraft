"""Phase 1b — applicability empty-state branches.

Covers FR-026 and output-shape invariants 1, 2, 7.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from processor.team.shape import _detect_applicability_reason, assemble_team_block

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def auras_table():
    with (PROCESSOR_DIR / "auras.json").open() as f:
        return json.load(f)


def test_base_2_applicable(base_2_parser_output, auras_table):
    """Real 3v3 fixture MUST be applicable=true."""
    block = assemble_team_block(base_2_parser_output, auras_table)
    assert block["applicable"] is True
    # Shape B: eight keys when applicable
    assert set(block.keys()) == {
        "applicable", "sharedControl", "findings", "battles",
        "itemTransfers", "supportEvents", "resourceCooperation",
        "players", "battleSummary",
    }


def test_no_allies_branch(base_2_parser_output, auras_table):
    """Strip down to one player per team → noAllies."""
    po = copy.deepcopy(base_2_parser_output)
    # Keep only one player per team
    seen_teams = set()
    keep = []
    for p in po["players"]:
        team = p.get("teamid")
        if team in seen_teams:
            continue
        seen_teams.add(team)
        keep.append(p)
    po["players"] = keep
    block = assemble_team_block(po, auras_table)
    assert block["applicable"] is False
    assert block["reason"] == "noAllies"
    # Empty-state minimality (invariant 2)
    assert set(block.keys()) == {"applicable", "reason"}


def test_ffa_branch(base_2_parser_output, auras_table):
    """Disable fixedTeams AND give each player a unique teamid → ffa."""
    po = copy.deepcopy(base_2_parser_output)
    po["settings"]["fixedTeams"] = False
    for i, p in enumerate(po["players"]):
        p["teamid"] = 100 + i  # unique teamid per player
    block = assemble_team_block(po, auras_table)
    assert block["applicable"] is False
    assert block["reason"] == "ffa"


def test_empty_state_minimality(base_2_parser_output, auras_table):
    """When applicable=false, only `applicable` and `reason` keys are present."""
    po = copy.deepcopy(base_2_parser_output)
    po["players"] = [po["players"][0]]  # noAllies
    block = assemble_team_block(po, auras_table)
    assert block["applicable"] is False
    extra_keys = set(block.keys()) - {"applicable", "reason"}
    assert not extra_keys, f"empty state has unexpected keys: {extra_keys}"
