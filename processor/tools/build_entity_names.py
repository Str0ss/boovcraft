"""Extract processor/entity_names.json from w3gjs's bundled mappings.js.

Runs `node -e` to dump the relevant tables as JSON, then normalizes:
- strips the `i_`/`u_`/`p_`/`b_` category prefix from each value
- for `heroAbilities` (values formatted `"a_<HeroName>:<AbilityName>"`)
  strips the `a_` and hero prefix so the ability's display name is just
  `<AbilityName>`; also derives a hero-id → hero-name mapping via
  `abilityToHero`

Usage:
  python processor/tools/build_entity_names.py        # write the file
  python processor/tools/build_entity_names.py --check  # diff against committed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPINGS_JS = REPO_ROOT / "parser" / "node_modules" / "w3gjs" / "dist" / "cjs" / "mappings.js"
ENTITY_NAMES_JSON = REPO_ROOT / "processor" / "entity_names.json"

PREFIX_BY_TABLE = {
    "items": "i_",
    "units": "u_",
    "buildings": "b_",
    "upgrades": "p_",
}

# Entries observed in real replays but absent from w3gjs's public mapping
# tables. Each addition here is grounded in fixture evidence. Do not extend
# this with speculative ids — if a real fixture produces an unmapped id that
# belongs to standard WC3:TFT content, add it here with a sourced name.
MANUAL_OVERRIDES: dict[str, str] = {
    # Alternate Crypt Lord ability code observed in base_1.w3g (player 2,
    # random race → Undead hero with only a single ability leveled).
    # Matches the id pattern used by WC3 for some Crypt Lord ability ranks.
    "AUa2": "Crypt Lord Ability",
}


def _dump_w3gjs_tables() -> dict:
    script = (
        f"const m = require({json.dumps(str(MAPPINGS_JS))});"
        "process.stdout.write(JSON.stringify({"
        "items:m.items,units:m.units,buildings:m.buildings,"
        "upgrades:m.upgrades,heroAbilities:m.heroAbilities,"
        "abilityToHero:m.abilityToHero"
        "}));"
    )
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"node extraction failed with exit {result.returncode}")
    return json.loads(result.stdout)


def _strip_prefix(value: str, prefix: str) -> str:
    return value[len(prefix):] if value.startswith(prefix) else value


def _build_mapping(tables: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}

    for table_name, prefix in PREFIX_BY_TABLE.items():
        for wc3_id, raw_name in tables[table_name].items():
            mapping[wc3_id] = _strip_prefix(raw_name, prefix)

    hero_abilities: dict[str, str] = tables["heroAbilities"]
    ability_to_hero: dict[str, str] = tables["abilityToHero"]
    hero_names_seen: dict[str, str] = {}

    for ability_id, raw_value in hero_abilities.items():
        val = _strip_prefix(raw_value, "a_")
        if ":" in val:
            hero_name, ability_name = val.split(":", 1)
        else:
            hero_name, ability_name = "", val
        mapping[ability_id] = ability_name.strip()

        hero_id = ability_to_hero.get(ability_id)
        if hero_id and hero_name:
            prior = hero_names_seen.get(hero_id)
            if prior and prior != hero_name:
                sys.stderr.write(
                    f"warn: hero {hero_id} has conflicting names "
                    f"({prior!r} vs {hero_name!r}); keeping first\n"
                )
                continue
            hero_names_seen[hero_id] = hero_name

    for hero_id, hero_name in hero_names_seen.items():
        mapping.setdefault(hero_id, hero_name)

    for wc3_id, display_name in MANUAL_OVERRIDES.items():
        mapping.setdefault(wc3_id, display_name)

    return mapping


def _serialize(mapping: dict[str, str]) -> str:
    return json.dumps(mapping, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="Compare freshly-extracted mapping against the committed file; exit 1 if they differ.",
    )
    args = ap.parse_args(argv)

    if not MAPPINGS_JS.is_file():
        sys.stderr.write(
            f"error: {MAPPINGS_JS} not found. "
            f"Run `(cd parser && npm install)` first.\n"
        )
        return 1

    tables = _dump_w3gjs_tables()
    mapping = _build_mapping(tables)
    serialized = _serialize(mapping)

    if args.check:
        existing = ENTITY_NAMES_JSON.read_text(encoding="utf-8")
        if existing != serialized:
            sys.stderr.write(
                "error: entity_names.json is out of date with w3gjs mappings.\n"
                "run `python processor/tools/build_entity_names.py` and commit the result.\n"
            )
            return 1
        print(f"ok: entity_names.json matches w3gjs (size {len(mapping)} entries)")
        return 0

    ENTITY_NAMES_JSON.write_text(serialized, encoding="utf-8")
    print(f"wrote {ENTITY_NAMES_JSON} ({len(mapping)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
