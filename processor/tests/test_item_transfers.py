"""Phase 2 — item transfers (0x13) mirror invariant.

Covers FR-007 and output-shape invariant 16 (bijection).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from processor.team.events import ACT_GIVE_ITEM, iter_command_actions
from processor.team.ownership import build_ownership_map
from processor.team.support import extract_item_transfers

PROCESSOR_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def item_attrs():
    with (PROCESSOR_DIR / "item_attributes.json").open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def entity_names():
    with (PROCESSOR_DIR / "entity_names.json").open() as f:
        return json.load(f)


def _count_0x13(parser_output):
    return sum(1 for _t, _p, a in iter_command_actions(parser_output) if a.get("id") == ACT_GIVE_ITEM)


def test_mirror_invariant_base_2(base_2_parser_output, item_attrs, entity_names):
    """Invariant 16: every 0x13 produces exactly one team.itemTransfers[] entry."""
    ownership = build_ownership_map(base_2_parser_output)
    gaps = []
    transfers = extract_item_transfers(
        base_2_parser_output, ownership, item_attrs, entity_names, gaps
    )
    assert len(transfers) == _count_0x13(base_2_parser_output)


def test_mirror_invariant_base_1(base_1_parser_output, item_attrs, entity_names):
    ownership = build_ownership_map(base_1_parser_output)
    gaps = []
    transfers = extract_item_transfers(
        base_1_parser_output, ownership, item_attrs, entity_names, gaps
    )
    assert len(transfers) == _count_0x13(base_1_parser_output)


def test_recipient_fit_class_enum(base_2_parser_output, item_attrs, entity_names):
    """Invariant 18: recipientFitClass ∈ closed enum."""
    ownership = build_ownership_map(base_2_parser_output)
    gaps = []
    transfers = extract_item_transfers(
        base_2_parser_output, ownership, item_attrs, entity_names, gaps
    )
    valid = {"good", "wrong", "neutral", "unknown"}
    for t in transfers:
        assert t["recipientFitClass"] in valid, t["recipientFitClass"]


def test_entity_ref_shape(base_2_parser_output, item_attrs, entity_names):
    """Invariant 29: every EntityRef has {id, name, unknown}."""
    ownership = build_ownership_map(base_2_parser_output)
    gaps = []
    transfers = extract_item_transfers(
        base_2_parser_output, ownership, item_attrs, entity_names, gaps
    )
    for t in transfers:
        for key in ("item", "recipientHero"):
            ref = t[key]
            assert set(ref.keys()) == {"id", "name", "unknown"}
            assert isinstance(ref["id"], str) and len(ref["id"]) == 4
            assert isinstance(ref["unknown"], bool)
            if ref["unknown"]:
                assert ref["name"] == ref["id"]
