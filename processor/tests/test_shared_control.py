"""Phase 2 — shared control banner + findings.

Covers FR-013 and output-shape invariant 23.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from processor.team.shape import assemble_team_block

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def auras_table():
    with (PROCESSOR_DIR / "auras.json").open() as f:
        return json.load(f)


def test_shared_control_mirrors_settings(base_2_parser_output, auras_table):
    """team.sharedControl.enabled === settings.fullSharedUnitControl."""
    block = assemble_team_block(base_2_parser_output, auras_table)
    expected = bool(base_2_parser_output["settings"]["fullSharedUnitControl"])
    assert block["sharedControl"]["enabled"] == expected


def test_findings_includes_disabled_when_off(base_2_parser_output, auras_table):
    """When fullSharedUnitControl is False, findings includes 'sharedControlDisabled'."""
    po = copy.deepcopy(base_2_parser_output)
    po["settings"]["fullSharedUnitControl"] = False
    block = assemble_team_block(po, auras_table)
    if block["applicable"]:
        assert "sharedControlDisabled" in block["findings"]


def test_findings_excludes_when_on(base_2_parser_output, auras_table):
    """When fullSharedUnitControl is True, 'sharedControlDisabled' MUST NOT appear."""
    po = copy.deepcopy(base_2_parser_output)
    po["settings"]["fullSharedUnitControl"] = True
    block = assemble_team_block(po, auras_table)
    if block["applicable"]:
        assert "sharedControlDisabled" not in block["findings"]


def test_findings_is_closed_enum(base_2_parser_output, auras_table):
    """Invariant 23: findings only contains values from v1's closed enum."""
    block = assemble_team_block(base_2_parser_output, auras_table)
    if block["applicable"]:
        valid = {"sharedControlDisabled"}
        for f in block["findings"]:
            assert f in valid, f"finding '{f}' is not in v1 closed enum"
