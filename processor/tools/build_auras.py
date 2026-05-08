#!/usr/bin/env python3
"""Build / verify processor/auras.json.

`auras.json` is the lookup table of WC3 hero-aura ability ids → radius +
type + owner-hero. It is consumed by `processor/team/centroids.py` to
pick the active support-aura radius for each battle window (FR-004 /
FR-005 / FR-006).

Source of truth: WC3:TFT canonical game data. The radii are stable game
constants — `w3gjs` does not surface them, so the table is curated in
``MANUAL_OVERRIDES`` below. Adding an aura is a one-line addition; the
``--check`` mode catches drift between the script and the committed
file.

Usage:
    python3 processor/tools/build_auras.py            # regenerate the file
    python3 processor/tools/build_auras.py --check    # exit 0 iff committed file matches
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROCESSOR_DIR = HERE.parent
OUTPUT_PATH = PROCESSOR_DIR / "auras.json"

# Canonical WC3:TFT hero auras. Radii are game constants.
#
# The "support" type marks auras whose effect benefits friendly units
# (Devotion adds armor, Brilliance regenerates mana, Endurance adds
# attack/move speed, Trueshot adds ranged damage, Unholy adds attack/
# move speed, Command adds damage). The "damage" type marks auras whose
# benefit is offensive only (Vampiric returns damage as life, Thorns
# returns damage). Only "support" auras are used as the split-engagement
# threshold — see processor/team/centroids.py::active_aura_radius.
#
# Owner is the 4-char hero id from entity_names.json.
MANUAL_OVERRIDES: dict[str, dict[str, object]] = {
    # Human
    "AHad": {"radius": 900, "type": "support", "owner": "Hpal", "name": "Devotion Aura"},
    "AHab": {"radius": 900, "type": "support", "owner": "Hamg", "name": "Brilliance Aura"},
    # Night Elf
    "AEar": {"radius": 900, "type": "support", "owner": "Emoo", "name": "Trueshot Aura"},
    "AEer": {"radius": 900, "type": "support", "owner": "Edem", "name": "Endurance Aura"},
    # Undead
    "AUau": {"radius": 900, "type": "support", "owner": "Udea", "name": "Unholy Aura"},
    "AUav": {"radius": 900, "type": "damage",  "owner": "Udea", "name": "Vampiric Aura — DK note"},
    # Orc
    "AOcr": {"radius": 900, "type": "support", "owner": "Otch", "name": "Command Aura"},
    "AOar": {"radius": 900, "type": "damage",  "owner": "Obla", "name": "Vampiric Aura — Blademaster note"},
    # Neutral / Tavern
    "ANbr": {"radius": 900, "type": "support", "owner": "Npbm", "name": "Brilliance Aura (Brewmaster)"},
}


def build_auras() -> dict[str, dict[str, object]]:
    """Return the canonical auras dict.

    Sorted by 4-char ability id ascending for deterministic output.
    """
    return {k: MANUAL_OVERRIDES[k] for k in sorted(MANUAL_OVERRIDES)}


def main(argv: list[str]) -> int:
    check_mode = "--check" in argv
    expected = build_auras()
    expected_text = json.dumps(expected, indent=2, ensure_ascii=False) + "\n"

    if check_mode:
        if not OUTPUT_PATH.exists():
            print(f"[build_auras] error: {OUTPUT_PATH} does not exist", file=sys.stderr)
            return 1
        actual_text = OUTPUT_PATH.read_text(encoding="utf-8")
        if actual_text != expected_text:
            print(f"[build_auras] error: {OUTPUT_PATH} is out of date with build_auras.py", file=sys.stderr)
            print(f"[build_auras] regenerate with: python3 {Path(__file__).relative_to(PROCESSOR_DIR.parent)}", file=sys.stderr)
            return 1
        print(f"[build_auras] OK: {OUTPUT_PATH} is up to date ({len(expected)} entries)")
        return 0

    OUTPUT_PATH.write_text(expected_text, encoding="utf-8")
    print(f"[build_auras] wrote {OUTPUT_PATH} ({len(expected)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
