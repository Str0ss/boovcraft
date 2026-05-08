#!/usr/bin/env python3
"""Build / verify processor/unit_costs.json.

`unit_costs.json` is the lookup table of WC3 entity ids → gold + lumber
+ supply cost. Used by `processor/team/tei.py` (TEI numerator/denominator
in gold + lumber), `processor/team/resources.py` (totalMined estimate
for generosity), and `processor/team/kills.py` (per-kill value).

Source of truth: WC3:TFT canonical ladder costs. Costs are stable game
constants. Heroes carry the level-1 summon cost (~425g/100l/5f for the
first three heroes); upgrades carry the level-1 research cost (used as
an approximation for total spent — see research.md § R3). Where a unit
exists in multiple variants in `entity_names.json` (e.g., the various
Troll Headhunter/Berserker ids), each is listed.

Coverage requirement: every entity id appearing in either committed
fixture's `players[].{units,buildings,heroes,upgrades}.summary` MUST be
in this table. The script reports gaps at build-time.

Usage:
    python3 processor/tools/build_unit_costs.py            # regenerate the file
    python3 processor/tools/build_unit_costs.py --check    # exit 0 iff committed file matches
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROCESSOR_DIR = HERE.parent
ENTITY_NAMES_PATH = PROCESSOR_DIR / "entity_names.json"
OUTPUT_PATH = PROCESSOR_DIR / "unit_costs.json"


# Curated WC3:TFT ladder costs. Tuples are (gold, lumber, supply).
# Heroes use level-1 summon cost (5 supply per WC3 ladder).
_COSTS: dict[str, tuple[int, int, int]] = {
    # =========================================================
    # Heroes (universal recruitment cost — first three heroes)
    # =========================================================
    "Hpal": (425, 100, 5), "Hamg": (425, 100, 5), "Hmkg": (425, 100, 5), "Hblm": (425, 100, 5),
    "Obla": (425, 100, 5), "Ofar": (425, 100, 5), "Otch": (425, 100, 5), "Oshd": (425, 100, 5),
    "Udea": (425, 100, 5), "Ucrl": (425, 100, 5), "Udre": (425, 100, 5), "Ulic": (425, 100, 5),
    "Edem": (425, 100, 5), "Emoo": (425, 100, 5), "Ekee": (425, 100, 5), "Ewar": (425, 100, 5),
    # Tavern heroes
    "Nfir": (425, 135, 5), "Nbrn": (425, 135, 5), "Npbm": (425, 135, 5), "Nbst": (425, 135, 5),
    "Nngs": (425, 135, 5), "Nalc": (425, 135, 5), "Ntin": (425, 135, 5), "Nplh": (425, 135, 5),

    # =========================================================
    # HUMAN
    # =========================================================
    # Units
    "hpea": (75, 0, 1), "hfoo": (135, 0, 2), "hrif": (205, 30, 3), "hmpr": (135, 20, 2),
    "hsor": (155, 20, 2), "hkni": (245, 60, 4), "hmtm": (180, 70, 3), "hrtt": (195, 60, 4),
    "hgry": (280, 70, 5), "hgyr": (90, 30, 1), "hspt": (215, 30, 3),
    # Buildings
    "htow": (385, 205, 0), "hkee": (320, 210, 0), "hcas": (360, 210, 0), "halt": (180, 50, 0),
    "hbar": (160, 60, 0), "hhou": (80, 20, 0), "hlum": (120, 20, 0), "hbla": (140, 60, 0),
    "harm": (140, 80, 0), "hars": (150, 130, 0), "hgra": (140, 100, 0), "hvlt": (130, 30, 0),
    "hwtw": (30, 20, 0), "hgtw": (70, 60, 0), "hatw": (70, 100, 0),

    # =========================================================
    # ORC
    # =========================================================
    # Units
    "opeo": (75, 0, 1), "ogru": (200, 0, 3), "ohun": (135, 20, 2), "oshm": (155, 25, 2),
    "odoc": (145, 20, 2), "orai": (180, 50, 3), "okod": (255, 60, 4), "otau": (280, 80, 5),
    "owyv": (245, 40, 4), "otbk": (135, 20, 2),
    # Buildings
    "ogre": (385, 185, 0), "ostr": (320, 190, 0), "ofrt": (360, 190, 0), "oalt": (180, 50, 0),
    "obar": (180, 60, 0), "otrb": (160, 40, 0), "ovln": (80, 30, 0), "ofor": (165, 65, 0),
    "obea": (145, 140, 0), "osld": (145, 110, 0), "otto": (145, 130, 0), "owtw": (110, 60, 0),

    # =========================================================
    # UNDEAD
    # =========================================================
    # Units
    "uaco": (75, 0, 1), "ugho": (120, 20, 2), "ucry": (215, 40, 3), "uabo": (240, 70, 4),
    "uobs": (245, 50, 4), "ufro": (385, 100, 7),
    # Buildings
    "unpl": (200, 0, 0), "unp1": (165, 0, 0), "unp2": (255, 0, 0), "uaod": (180, 50, 0),
    "usep": (165, 50, 0), "ugrv": (215, 0, 0), "uslh": (145, 140, 0), "utom": (130, 0, 0),
    "ubon": (145, 100, 0), "uzig": (120, 25, 0), "uzg1": (30, 75, 0), "uzg2": (30, 75, 0),
    "ugol": (385, 0, 0),  # Haunted Gold Mine — used by parser, no real "build" cost

    # =========================================================
    # NIGHT ELF
    # =========================================================
    # Units
    "ewsp": (60, 0, 1), "earc": (130, 10, 2), "esen": (195, 30, 3), "edry": (145, 60, 3),
    "edoc": (235, 75, 4), "echm": (360, 80, 7), "emtg": (300, 100, 5),
    # Buildings
    "etol": (215, 60, 0), "etoa": (115, 50, 0), "etoe": (165, 80, 0), "eate": (180, 50, 0),
    "eaom": (150, 60, 0), "eaoe": (130, 80, 0), "edob": (210, 100, 0), "edos": (140, 190, 0),
    "emow": (180, 40, 0), "eden": (130, 0, 0),

    # =========================================================
    # NEUTRAL / GOBLIN / SPECIAL
    # =========================================================
    "ngsp": (215, 50, 4),   # Goblin Sapper
    "ngir": (90, 50, 1),    # Goblin Shredder
    "nzep": (110, 80, 0),   # Goblin Zeppelin
    "nfsh": (155, 25, 2),   # Forest Troll High Priest (mercenary)
    "tgrh": (300, 100, 0),  # Tiny Great Hall (item that materializes a building — value as building)

    # =========================================================
    # UPGRADES — level-1 research cost as the value proxy
    # =========================================================
    # Human upgrades
    "Rhac": (100, 100, 0),  # Masonry
    "Rhan": (50, 100, 0),   # Animal War Training
    "Rhar": (75, 75, 0),    # Plating
    "Rhfl": (50, 75, 0),    # Flare
    "Rhfs": (50, 75, 0),    # Fragmentation Shards
    "Rhgb": (50, 75, 0),    # Flying Machine Bombs
    "Rhhb": (75, 75, 0),    # Storm Hammers
    "Rhla": (100, 75, 0),   # Armor
    "Rhlh": (100, 50, 0),   # Lumber Harvesting
    "Rhme": (100, 50, 0),   # Swords
    "Rhpt": (50, 75, 0),    # Priest Training
    "Rhra": (75, 75, 0),    # Gunpowder
    "Rhri": (75, 75, 0),    # Long Rifles
    "Rhrt": (50, 75, 0),    # Barrage
    "Rhse": (50, 0, 0),     # Magic Sentry
    "Rhst": (50, 75, 0),    # Sorceress Training

    # Orc upgrades
    "Roar": (125, 75, 0),   # Armor (Orc)
    "Robf": (75, 50, 0),    # Burning Oil
    "Robk": (200, 100, 0),  # Berserker Upgrade
    "Robs": (50, 50, 0),    # Berserker Strength
    "Roen": (75, 50, 0),    # Ensnare
    "Rome": (100, 50, 0),   # Melee Weapons
    "Ropg": (50, 75, 0),    # Pillage
    "Rora": (100, 50, 0),   # Ranged Weapons
    "Rorb": (50, 75, 0),    # Reinforced Defenses
    "Rosp": (75, 25, 0),    # Spiked Barricades
    "Rost": (50, 75, 0),    # Shaman Training
    "Rotr": (50, 75, 0),    # Troll Regeneration
    "Rovs": (75, 75, 0),    # Envenomed Spears
    "Rowd": (50, 75, 0),    # Witch Doctor Training
    "Rwdm": (100, 100, 0),  # War Drums Damage Increase

    # Undead upgrades
    "Ruar": (100, 100, 0),  # Unholy Armor
    "Rubu": (75, 0, 0),     # Burrow
    "Rucr": (100, 100, 0),  # Creature Carapace
    "Rugf": (100, 50, 0),   # Ghoul Frenzy
    "Rume": (100, 100, 0),  # Unholy Strength
    "Rupc": (75, 75, 0),    # Disease Cloud
    "Rura": (100, 100, 0),  # Creature Attack
    "Rusp": (200, 100, 0),  # Destroyer Form
    "Ruwb": (50, 75, 0),    # Web

    # Night Elf upgrades
    "Recb": (100, 100, 0),  # Corrosive Breath
    "Redc": (50, 75, 0),    # Druid of the Claw Training
    "Reeb": (50, 50, 0),    # Mark of the Claw
    "Reib": (75, 75, 0),    # Improved Bows
    "Rema": (100, 75, 0),   # Moon Armor
    "Remk": (100, 100, 0),  # Marksmanship
    "Renb": (200, 200, 0),  # Nature's Blessing
    "Rerh": (75, 50, 0),    # Reinforced Hides
    "Resc": (50, 75, 0),    # Sentinel
    "Resm": (75, 75, 0),    # Strength of the Moon
    "Resw": (75, 75, 0),    # Strength of the Wild
}


def build_unit_costs(entity_names: dict[str, str]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for entity_id, (gold, lumber, supply) in _COSTS.items():
        name = entity_names.get(entity_id, entity_id)
        out[entity_id] = {"gold": gold, "lumber": lumber, "supply": supply, "name": name}
    return {k: out[k] for k in sorted(out)}


def coverage_check(unit_costs: dict[str, dict[str, object]], fixtures: list[Path]) -> tuple[set[str], int]:
    """Return (missing_ids, total_required_ids) across the given fixtures."""
    required: set[str] = set()
    for fixture in fixtures:
        if not fixture.exists():
            continue
        with fixture.open(encoding="utf-8") as f:
            data = json.load(f)
        for p in data.get("players", []):
            prod = p.get("production", {})
            for cat in ("units", "buildings", "upgrades"):
                required.update(prod.get(cat, {}).get("summary", {}).keys())
            for h in p.get("heroes", []):
                hid = h.get("id")
                if hid:
                    required.add(hid)
    # Drop the UNKN sentinel — that's a parser-side unmapped id, not a real cost target.
    required.discard("UNKN")
    missing = required - set(unit_costs.keys())
    return missing, len(required)


def main(argv: list[str]) -> int:
    check_mode = "--check" in argv

    if not ENTITY_NAMES_PATH.exists():
        print(f"[build_unit_costs] error: {ENTITY_NAMES_PATH} not found", file=sys.stderr)
        return 1
    with ENTITY_NAMES_PATH.open(encoding="utf-8") as f:
        entity_names = json.load(f)

    expected = build_unit_costs(entity_names)
    expected_text = json.dumps(expected, indent=2, ensure_ascii=False) + "\n"

    fixtures = [
        PROCESSOR_DIR.parent / "sample_replays" / "base_1.w3g.analysis.json",
        PROCESSOR_DIR.parent / "sample_replays" / "base_2.w3g.analysis.json",
    ]
    missing, required_count = coverage_check(expected, fixtures)
    if missing:
        print(f"[build_unit_costs] warning: {len(missing)} ids in fixtures are missing from unit_costs:", file=sys.stderr)
        for mid in sorted(missing):
            print(f"  {mid}: {entity_names.get(mid, '<unmapped>')}", file=sys.stderr)
    else:
        print(f"[build_unit_costs] coverage OK: {required_count} required ids, all present")

    if check_mode:
        if not OUTPUT_PATH.exists():
            print(f"[build_unit_costs] error: {OUTPUT_PATH} does not exist", file=sys.stderr)
            return 1
        actual = OUTPUT_PATH.read_text(encoding="utf-8")
        if actual != expected_text:
            print(f"[build_unit_costs] error: {OUTPUT_PATH} is out of date with build_unit_costs.py", file=sys.stderr)
            return 1
        print(f"[build_unit_costs] OK: {OUTPUT_PATH} is up to date ({len(expected)} entries)")
        return 0 if not missing else 1

    OUTPUT_PATH.write_text(expected_text, encoding="utf-8")
    print(f"[build_unit_costs] wrote {OUTPUT_PATH} ({len(expected)} entries)")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
