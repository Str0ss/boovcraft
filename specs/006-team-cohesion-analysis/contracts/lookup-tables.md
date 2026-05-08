# Contract: Lookup Tables (Auras / Item Attributes / Unit Costs / Rescue Items)

Structural contract for the four committed JSON tables introduced in feature 006. The authoritative field-level documentation lives in `data-model.md` § Inputs; this contract captures the **MUST** invariants that test cases (`processor/tests/test_lookup_table_shape.py`, T074) and PR reviewers rely on.

The four tables are *data*, not code dependencies. Each is committed at the top of `processor/` next to `entity_names.json`, regenerable by a `processor/tools/build_*.py` script, and consumed read-only by `processor/analyze.py`. Adding to a table is a single-line PR; the regenerator scripts are the source of truth for *how* entries are produced, this contract is the source of truth for *what shape* they MUST have.

## File locations

```text
processor/
├── entity_names.json           # unchanged from feature 002
├── auras.json                  # NEW (feature 006)
├── item_attributes.json        # NEW (feature 006)
├── rescue_items.json           # NEW (feature 006, derived from item_attributes.json)
├── unit_costs.json             # NEW (feature 006)
└── tools/
    ├── build_entity_names.py       # unchanged
    ├── build_auras.py              # NEW
    ├── build_item_attributes.py    # NEW
    └── build_unit_costs.py         # NEW
```

`rescue_items.json` does NOT have its own regenerator script — it is produced as a side-effect of `build_item_attributes.py` (the items where `isRescue === true` are written to a sibling array).

## Common shape rules

The following apply to every lookup table:

1. **Top-level type.** Each file is a JSON object (or, for `rescue_items.json` only, a JSON array — see § rescue_items.json below).
2. **Encoding.** UTF-8, no BOM, exactly one trailing newline.
3. **Determinism.** Regenerating the same table from the same `w3gjs` snapshot produces a byte-identical file. Ordering is deterministic — key ordering by lexicographic 4-char id ascending; value ordering inside each entry by the key list documented per-table below.
4. **No dead keys.** Every committed entry MUST be referenced by at least one path in the analyzer code OR by a fixture's data (an entry kept "for completeness" but never used by a test or analyzer call-site MUST be removed).
5. **Manual override discipline.** Each regenerator script may carry a top-of-file `MANUAL_OVERRIDES` dict for entries observed in real fixtures but absent from `w3gjs`'s tables. Overrides in this dict take precedence over `w3gjs`-extracted values. New overrides require an inline `# fixture: <fixture_name>` comment naming the fixture that surfaced the gap.

## `auras.json`

### Shape

```text
{
  "<ability_id>": {
    "radius": <number>,
    "type":   "support" | "damage",
    "owner":  "<hero_id>",
    "name":   "<display_name>"
  },
  ...
}
```

### Invariants

A1. **Top level is an object.** Keys are 4-character WC3 ability ids. Values are objects with the four keys named above.

A2. **Key shape.** Every key MUST be a 4-character ASCII string matching `[A-Za-z0-9]{4}`.

A3. **`radius` valid.** `radius` is a number `>= 0` and finite (no `NaN`, no `Infinity`). Realistic values are in `[100, 1500]`; values outside this band are accepted but a build-time warning is emitted by the regenerator.

A4. **`type` enum.** `type` is exactly one of `"support"` or `"damage"`. (Future feature may extend; v1 has these two only.)

A5. **`owner` shape.** `owner` is a 4-character string referencing a hero id present in `entity_names.json`. The build script asserts this; orphaned `owner` references fail T074.

A6. **`name` non-empty.** `name` is a non-empty UTF-8 string. The display name is in English; localization is out of scope for v1.

A7. **No additional keys.** Each value object has EXACTLY the four documented keys. Adding a fifth key is a breaking change to this contract.

A8. **Coverage floor.** The committed `auras.json` MUST contain at least the seven canonical support / buff auras: Devotion (`AHad`), Brilliance (`AHab`), Endurance (`AEar`-Demon-Hunter), Trueshot (`AEar`-Priestess-of-the-Moon — confirm distinct id during T002), Unholy (`AUau`), Vampiric (`AUav`), Command (`AOcr`). T074 asserts each is present.

A9. **`radius` consistency for canonical support auras.** Each of the seven canonical support auras MUST have `radius === 900`. (This is a WC3 game-engine fact, not an analyzer choice. If `w3gjs` ever ships a different radius, the discrepancy is a `w3gjs` bug to be reported upstream — the table reflects the current canonical value.)

### Consumed by

- `processor/team/centroids.py::active_aura_radius` — picks the maximum-radius active *support* aura for a battle. `type === "damage"` entries are recorded but ignored for split-engagement.
- T024 (`test_aura_lookup.py`) — asserts the default-fallback path when no support aura is active.

### Regenerator

`processor/tools/build_auras.py`. Run modes:

- `python3 processor/tools/build_auras.py` — regenerates the file.
- `python3 processor/tools/build_auras.py --check` — exits 0 iff the committed file matches what the regenerator would produce; non-zero otherwise. Used in CI.

## `item_attributes.json`

### Shape

```text
{
  "<item_id>": {
    "primary":   "int" | "str" | "agi" | "universal" | "none",
    "isRescue":  <boolean>,
    "name":      "<display_name>"
  },
  ...
}
```

### Invariants

I1. **Top level is an object.** Keys are 4-character WC3 item ids. Values are objects with the three keys named above.

I2. **Key shape.** Every key MUST be a 4-character ASCII string matching `[A-Za-z0-9]{4}`.

I3. **`primary` enum.** Exactly one of `"int"`, `"str"`, `"agi"`, `"universal"`, `"none"`.

I4. **`isRescue` boolean.** Exactly `true` or `false` (not a truthy / falsy value of any other type).

I5. **`name` non-empty.** Non-empty UTF-8 string.

I6. **No additional keys.** Each value object has EXACTLY the three documented keys.

I7. **Coverage requirement against fixtures.** Every item id appearing in either committed fixture's `players[].items.summary` MUST be present in `item_attributes.json`. T030 fails if an unmapped item id is encountered during fixture-driven `recipientFitClass` testing AND the item is not present in `item_attributes.json`. (Items mapped here but with `primary === "none"` are fine — they correctly produce `recipientFitClass: "neutral"`.)

I8. **`isRescue` ⇒ `primary === "universal"`.** Every rescue item is universally usable; a rescue item with a strict primary attribute is a contradiction. T074 asserts this implication.

### Consumed by

- `processor/team/support.py::extract_item_transfers` — looks up `primary` and `isRescue` to classify `recipientFitClass`.
- `processor/tools/build_item_attributes.py` — derives `rescue_items.json` from `isRescue === true` entries.
- T030 / T031 / T037 (recipient fit class, missed saves, generosity).

### Regenerator

`processor/tools/build_item_attributes.py`. Same `--check` mode as `build_auras.py`. Side-effect: writes `processor/rescue_items.json` in the same invocation.

## `rescue_items.json`

### Shape

```text
[
  "<item_id>",
  "<item_id>",
  ...
]
```

A flat JSON array of 4-character item ids.

### Invariants

R1. **Top level is an array of strings.**

R2. **Elements are 4-character ASCII ids** matching `[A-Za-z0-9]{4}`.

R3. **No duplicates.** Each id appears at most once. Order is lexicographic ascending.

R4. **Equivalence with `item_attributes.json`.** The set of ids in this array MUST equal `{ id : item_attributes[id].isRescue === true }`. T074 asserts the equivalence on every test run; a mismatch means one of the two files was edited without regenerating the other.

R5. **Coverage floor.** The array MUST contain at least: `stwp` (Staff of Preservation), `shea` (Scroll of Healing), `stwl` (Scroll of Town Portal), `rhe1` (Lesser Healing Potion). T074 asserts each is present.

### Consumed by

- `processor/team/support.py::detect_missed_saves` — fast-path check: is the id in inventory a rescue tool?
- T031 (missed-save detection).

### Regenerator

Side-effect of `processor/tools/build_item_attributes.py`. The file is **derived** — editing it directly is a code-review smell (the change will revert on next regeneration unless `item_attributes.json` is also edited). Reviewers reject PRs that edit `rescue_items.json` without a corresponding edit to `item_attributes.json`.

## `unit_costs.json`

### Shape

```text
{
  "<entity_id>": {
    "gold":   <number>,
    "lumber": <number>,
    "supply": <number>,
    "name":   "<display_name>"
  },
  ...
}
```

Keys are 4-character WC3 unit / building / hero / upgrade ids — the namespace is shared with `entity_names.json`.

### Invariants

U1. **Top level is an object.** Keys are 4-character ids; values are objects with the four keys named above.

U2. **Key shape.** Every key MUST be a 4-character ASCII string.

U3. **`gold` / `lumber` / `supply` non-negative integers.** All three MUST be integers `>= 0`. Floats are rejected by T074.

U4. **`name` non-empty UTF-8.**

U5. **No additional keys.** EXACTLY four keys per entry.

U6. **Heroes carry summon cost.** Hero entries (4-char ids beginning with an uppercase letter, e.g., `Hpal`, `Edem`, `Nfir`) carry the `gold` + `lumber` summon cost — the resource cost the player paid at the altar to first summon this hero, regardless of subsequent revives. (Future feature may extend with revive-cost tracking; v1 uses summon cost as the sole hero value proxy.)

U7. **Buildings carry build cost.** Building ids carry the worker-stamped construction cost.

U8. **Upgrades carry research cost.** Upgrade ids carry the `gold` + `lumber` research cost; `supply === 0` for every upgrade (research uses no food).

U9. **Coverage requirement against fixtures.** Every id appearing in either committed fixture's `players[].{units,buildings,heroes,upgrades}.summary` MUST be present in `unit_costs.json`. T006's regenerator runs a script-local validation pass that reports gaps; T074 enforces the same property at test time.

U10. **No mythical units.** `unit_costs.json` does NOT contain entries for neutral / creep / map-objects (e.g., trees, gold mines, NPCs). Only player-controllable entities. T074 asserts no key matches the known neutral-unit prefix list.

### Consumed by

- `processor/team/tei.py::compute_battle_tei` — `gold + lumber` is the value function for both numerator (enemy units killed) and denominator (own units lost).
- `processor/team/resources.py::compute_generosity` — `Σ gold × count + Σ lumber × count` is the `totalMined` estimate.
- `processor/team/kills.py::estimate_kills` — `victimValue = gold + lumber` is the per-kill value.
- T037 / T045 / T046 / T051 / T052.

### Regenerator

`processor/tools/build_unit_costs.py`. Same `--check` mode. Manual overrides supported at the top of the script with `# fixture: <name>` comments naming the source fixture for audit.

## Cross-table invariants

X1. **Shared id namespace.** `auras.json` ability ids, `item_attributes.json` item ids, `unit_costs.json` entity ids, and `entity_names.json` ids all share the 4-character WC3 id namespace. Different tables MAY contain the same id when its semantic role is multi-faceted (an ability id with a learnable cost would appear in both `auras.json` and a future cost table); but within one table, ids are unique.

X2. **`entity_names.json` reference integrity.** Every `name` field in the four new tables MUST agree with the `entity_names.json` value for the same id when the id appears in both. (i.e., `auras.json["AHad"].name === entity_names.json["AHad"]`.) T074 asserts this for every id present in both files.

X3. **No orphan keys.** Every id in any of the four new tables MUST EITHER be referenced from at least one fixture's analysis output OR be flagged in the regenerator's `MANUAL_OVERRIDES` dict. T074 fails if an entry is unreferenced and unjustified.

## Diagnostics on miss

When `analyze.py` looks up a key in any of these tables and the key is absent, it MUST:

- For `auras.json` miss: fall back to default radius 900 (`splitEngagement.referenceAuraId === "default"`); add `diagnostics.unmappedEntityIds[]` entry with `category: "ability"`.
- For `item_attributes.json` miss on an item: emit `recipientFitClass: "unknown"`; add `diagnostics.itemAttributeGaps[]` entry with `category: "item"`.
- For `item_attributes.json` miss on a hero (recipient hero whose primary attribute is unknown): emit `recipientFitClass: "unknown"`; add `diagnostics.itemAttributeGaps[]` entry with `category: "hero"`.
- For `unit_costs.json` miss on a victim: skip the kill from TEI numerator/denominator (treat its value as 0 — the kill is recorded but not valued); add `diagnostics.unmappedEntityIds[]` entry with `category: "unitCost"`.
- For `unit_costs.json` miss on a player's `production.summary` entry: emit `GenerosityRow.estimatedMined{Gold,Lumber}: null`, `generosityPercent: null`; add `diagnostics.cohesionMetricGaps[]` entry naming `generosity:slot=N` AND `diagnostics.unmappedEntityIds[]` entry with `category: "unitCost"`.

Diagnostic emission is bidirectional with degradation per `output-shape.md` invariant 35 — every gap is named, every named diagnostic refers to a real gap.

## Compatibility

- **Adding a new entry** is non-breaking. Reviewers accept entry-additions backed by a fixture observation OR a regenerator extraction; pure speculation is rejected per `entity_names.json`'s established policy.
- **Adding a new key to an entry's value object** is breaking — invalidates U5 / I6 / A7. Requires bumping this contract's version, updating `data-model.md`, AND updating every consumer call-site.
- **Removing an entry** is breaking — analyzer call-sites that depended on the entry start producing diagnostics. Acceptable only if accompanied by analyzer-side changes that no longer reference the removed id.
- **Changing an entry's value** (e.g., correcting an aura radius from 900 to 850) is non-breaking at the contract level but MAY shift fixture-specific values in `quickstart.md`. The change PR MUST update `quickstart.md` if a fixture's expected counts shift as a result.

## Test coverage

T074 (`processor/tests/test_lookup_table_shape.py`) runs the following on every test invocation:

1. JSON-loads each of the four files; rejects any file that fails to parse.
2. Asserts every invariant A1–A9, I1–I8, R1–R5, U1–U10, X1–X3.
3. Asserts the diagnostics-on-miss pathway via fixture-driven calls — confirms that missing ids produce the documented diagnostic shapes.

Coverage gaps surfaced during T030 / T037 / T051 (each of which exercises real fixture lookups) are blockers — adding the missing id to the relevant table is a same-PR fix, not a follow-up.
