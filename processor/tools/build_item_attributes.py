#!/usr/bin/env python3
"""Build / verify processor/item_attributes.json AND processor/rescue_items.json.

`item_attributes.json` is the lookup table of WC3 item ids → primary
attribute (`int`/`str`/`agi`/`universal`/`none`) and rescue-tool flag.
Consumed by `processor/team/support.py` (FR-007 / FR-009 / FR-010).

`rescue_items.json` is a derived flat array of item ids where
``isRescue === true``. Both files are written in the same invocation
to keep them in lockstep — see contracts/lookup-tables.md § R4.

Source of truth: WC3:TFT canonical game data + the name-pattern
classifier below. Names sourced from `entity_names.json`.

Usage:
    python3 processor/tools/build_item_attributes.py            # regenerate both files
    python3 processor/tools/build_item_attributes.py --check    # exit 0 iff committed files match
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROCESSOR_DIR = HERE.parent
ENTITY_NAMES_PATH = PROCESSOR_DIR / "entity_names.json"
ATTR_OUTPUT_PATH = PROCESSOR_DIR / "item_attributes.json"
RESCUE_OUTPUT_PATH = PROCESSOR_DIR / "rescue_items.json"


# Canonical attribute classification by item id.
#
# These overrides are the source of truth. The name-pattern classifier
# below seeds initial values for tomes / orbs / scrolls; explicit entries
# in MANUAL_OVERRIDES win over the classifier and are required for any
# item whose name does not match a pattern.
#
# isRescue: items that an ally hero can use to save / extract a teammate
# (Staff of Preservation, Scroll of Town Portal, healing scrolls /
# potions). Used by team/support.py to detect missed-save events.
MANUAL_OVERRIDES: dict[str, dict[str, object]] = {
    # Tomes — strict primary attribute
    "tin1": {"primary": "int", "isRescue": False, "name": "Tome of Intelligence"},
    "tst1": {"primary": "str", "isRescue": False, "name": "Tome of Strength"},
    "tdex": {"primary": "agi", "isRescue": False, "name": "Tome of Agility"},
    "texp": {"primary": "universal", "isRescue": False, "name": "Tome of Experience"},
    "tret": {"primary": "universal", "isRescue": False, "name": "Tome of Retraining"},
    "tkno": {"primary": "universal", "isRescue": False, "name": "Tome of Power (Knowledge)"},
    # Strict-attribute artifacts
    "rin1": {"primary": "int", "isRescue": False, "name": "Mantle of Intelligence +3"},
    "rin2": {"primary": "int", "isRescue": False, "name": "Mantle of Intelligence +6"},
    "rst1": {"primary": "str", "isRescue": False, "name": "Gauntlets of Ogre Strength +3"},
    "rst2": {"primary": "str", "isRescue": False, "name": "Gauntlets of Ogre Strength +6"},
    "rag1": {"primary": "agi", "isRescue": False, "name": "Slippers of Agility +3"},
    "rag2": {"primary": "agi", "isRescue": False, "name": "Slippers of Agility +6"},
    # Rescue items
    "spre": {"primary": "universal", "isRescue": True, "name": "Staff of Preservation"},
    "stwp": {"primary": "universal", "isRescue": True, "name": "Scroll of Town Portal"},
    "shea": {"primary": "universal", "isRescue": True, "name": "Scroll of Healing"},
    "phea": {"primary": "universal", "isRescue": True, "name": "Potion of Healing"},
    "pghe": {"primary": "universal", "isRescue": True, "name": "Potion of Greater Healing"},
    "pres": {"primary": "universal", "isRescue": True, "name": "Potion of Restoration"},
    # Orbs — affinity is agi (orbs are universally an agi-attack hero's domain)
    "ofir": {"primary": "agi", "isRescue": False, "name": "Orb of Fire"},
    "ofro": {"primary": "agi", "isRescue": False, "name": "Orb of Frost"},
    "olig": {"primary": "agi", "isRescue": False, "name": "Orb of Lightning"},
    "oli2": {"primary": "agi", "isRescue": False, "name": "Orb of Lightning"},
    "oven": {"primary": "agi", "isRescue": False, "name": "Orb of Venom"},
    "odef": {"primary": "agi", "isRescue": False, "name": "Orb of Darkness"},
    "ocor": {"primary": "agi", "isRescue": False, "name": "Orb of Corruption"},
}


# Name-pattern fallbacks for items not in MANUAL_OVERRIDES. Used by
# build_from_entity_names() to seed coverage; MANUAL_OVERRIDES wins.
NAME_PATTERNS: list[tuple[re.Pattern[str], dict[str, object]]] = [
    (re.compile(r"Tome of Intelligence", re.I), {"primary": "int", "isRescue": False}),
    (re.compile(r"Tome of Strength",     re.I), {"primary": "str", "isRescue": False}),
    (re.compile(r"Tome of Agility",      re.I), {"primary": "agi", "isRescue": False}),
    (re.compile(r"Tome of",              re.I), {"primary": "universal", "isRescue": False}),
    (re.compile(r"^Orb of",              re.I), {"primary": "agi", "isRescue": False}),
    (re.compile(r"Scroll of (Healing|Town Portal|Restoration)", re.I), {"primary": "universal", "isRescue": True}),
    (re.compile(r"Potion of (Healing|Greater Healing|Restoration)", re.I), {"primary": "universal", "isRescue": True}),
    (re.compile(r"Staff of Preservation", re.I), {"primary": "universal", "isRescue": True}),
    (re.compile(r"^Mantle of Intelligence", re.I), {"primary": "int", "isRescue": False}),
    (re.compile(r"^Gauntlets of Ogre",    re.I), {"primary": "str", "isRescue": False}),
    (re.compile(r"^Slippers of Agility",  re.I), {"primary": "agi", "isRescue": False}),
]


def _is_item_id(entity_id: str, name: str) -> bool:
    """Heuristic: does this 4-char id name an item?

    Items in entity_names.json are not flagged structurally. Two-stage
    filter:

    1. Items in WC3 use lowercase 4-char ids (e.g., "amrc", "spre",
       "stwp"). Abilities ("AHad"), upgrades ("Rhme"), neutral entities
       ("Nfir") use uppercase first character. Filter by case.
    2. Item names match a word-boundary check against an item-vocabulary
       list. Substring matching false-positives on "ring" inside
       "Searing", etc.; word-boundary matching avoids that.
    """
    if len(entity_id) != 4:
        return False
    if not entity_id[0].islower():
        return False
    item_words = (
        "tome", "scroll", "potion", "orb", "staff", "ring", "mantle",
        "gauntlets", "slippers", "boots", "claws", "ankh", "amulet",
        "belt", "cloak", "crown", "crystal", "dagger", "gem", "glyph",
        # additional vocabulary observed in committed fixtures
        "wand", "hood", "rod", "salve", "dust", "skull",
        # building-summoning trinkets (materialize a structure)
        "ivory", "great",
    )
    name_words = re.findall(r"\b\w+\b", name.lower())
    return any(word in item_words for word in name_words)


def build_from_entity_names() -> dict[str, dict[str, object]]:
    """Seed item_attributes from entity_names.json + classifier + overrides."""
    if not ENTITY_NAMES_PATH.exists():
        raise FileNotFoundError(f"{ENTITY_NAMES_PATH} not found")
    with ENTITY_NAMES_PATH.open(encoding="utf-8") as f:
        entity_names = json.load(f)

    out: dict[str, dict[str, object]] = {}

    # Pass 1: name-pattern classifier across all entity_names entries
    # that look like items.
    for entity_id, name in entity_names.items():
        if not _is_item_id(entity_id, name):
            continue
        # Walk patterns; first match wins.
        primary, is_rescue = "none", False
        for pat, fields in NAME_PATTERNS:
            if pat.search(name):
                primary = fields["primary"]
                is_rescue = fields["isRescue"]
                break
        out[entity_id] = {"primary": primary, "isRescue": is_rescue, "name": name}

    # Pass 2: MANUAL_OVERRIDES win.
    for entity_id, override in MANUAL_OVERRIDES.items():
        out[entity_id] = dict(override)
        # If entity_names has a name and the override didn't pick one
        # explicitly, prefer entity_names.
        if entity_id in entity_names and "name" not in override:
            out[entity_id]["name"] = entity_names[entity_id]

    # Sort keys for deterministic output.
    return {k: out[k] for k in sorted(out)}


def derive_rescue_items(item_attrs: dict[str, dict[str, object]]) -> list[str]:
    return sorted(item_id for item_id, fields in item_attrs.items() if fields.get("isRescue"))


def main(argv: list[str]) -> int:
    check_mode = "--check" in argv

    expected_attrs = build_from_entity_names()
    expected_attrs_text = json.dumps(expected_attrs, indent=2, ensure_ascii=False) + "\n"

    expected_rescue = derive_rescue_items(expected_attrs)
    expected_rescue_text = json.dumps(expected_rescue, indent=2, ensure_ascii=False) + "\n"

    if check_mode:
        for path, expected in (
            (ATTR_OUTPUT_PATH, expected_attrs_text),
            (RESCUE_OUTPUT_PATH, expected_rescue_text),
        ):
            if not path.exists():
                print(f"[build_item_attributes] error: {path} does not exist", file=sys.stderr)
                return 1
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                print(f"[build_item_attributes] error: {path} is out of date", file=sys.stderr)
                return 1
        print(f"[build_item_attributes] OK: both files up to date "
              f"({len(expected_attrs)} item attrs, {len(expected_rescue)} rescue items)")
        return 0

    ATTR_OUTPUT_PATH.write_text(expected_attrs_text, encoding="utf-8")
    RESCUE_OUTPUT_PATH.write_text(expected_rescue_text, encoding="utf-8")
    print(f"[build_item_attributes] wrote {ATTR_OUTPUT_PATH} ({len(expected_attrs)} entries) "
          f"and {RESCUE_OUTPUT_PATH} ({len(expected_rescue)} rescue items)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
