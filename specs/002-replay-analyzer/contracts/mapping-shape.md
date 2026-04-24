# Contract: Entity-Name Mapping

Structural contract for `processor/entity_names.json`.

## Shape

A flat JSON object. Keys are Warcraft III entity IDs (4-character
ASCII-alphanumeric strings). Values are human-readable English
display names (non-empty strings).

```json
{
  "Nfir": "Firelord",
  "hpea": "Peasant",
  "hkee": "Keep",
  "Rhme": "Swords",
  "bspd": "Boots of Speed",
  "AHbz": "Blizzard"
}
```

## Invariants

1. The JSON document's root MUST be an object (not an array or
   scalar).
2. Every key MUST be a string of exactly 4 ASCII alphanumerics
   (`[A-Za-z0-9]{4}`).
3. Every value MUST be a non-empty string.
4. No two keys may share the same value AND the same category
   (duplication within a category indicates a bug in the mapping
   source extraction). Cross-category name collisions (e.g., an
   ability and a unit named the same) are permitted.
5. The file MUST be valid JSON parseable by `json.load` with no
   extensions (no trailing commas, no comments).

## Coverage policy

The mapping MUST cover:

- **All entity IDs observed in the committed fixtures.** Enforced by
  a test (SC-002): for every hero, non-hero unit, building, upgrade,
  item, and hero ability ID appearing in any committed parser-output
  fixture, the mapping produces a non-placeholder name.
- **All standard WC3:TFT ladder rosters.** The four races' heroes,
  non-hero units, buildings, upgrades, items (ladder shop contents),
  and hero abilities. Verified by a one-time race-roster review
  checklist inside `processor/DATA.md` and re-reviewed whenever the
  mapping is regenerated from a newer `w3gjs`.

The mapping is NOT required to cover:

- Custom-map-specific units, heroes, buildings, or abilities.
- Neutral buildings / mercenary camps beyond the standard ladder
  shops.
- Modded or unofficial content.

When an ID outside the required coverage appears in a real replay,
FR-006's graceful degradation path kicks in (placeholder + stderr
diagnostic).

## Source of truth

Entries are extracted once from `w3gjs`'s
`dist/cjs/mappings.js` tables:

| `w3gjs` table | Contributes | Prefix to strip from values |
|---|---|---|
| `items` | item IDs | `i_` |
| `units` | non-hero unit IDs | `u_` |
| `buildings` | building IDs | `b_` (present sporadically; strip if present) |
| `upgrades` | upgrade IDs | `p_` |
| `heroAbilities` | hero-ability IDs | `a_` and everything up to and including the first `:` (the hero-name prefix) |
| `heroAbilities` + `abilityToHero` | hero IDs | derive by taking the hero-name portion of each `heroAbilities` value and joining to the hero ID that `abilityToHero` maps that ability to |

Any entry that, after extraction, would be missing or ambiguous is
resolved manually against public WC3 references and the discrepancy
noted in the task description.

## Edit policy

`entity_names.json` is a reviewable static artifact. Edits happen:

1. **On mapping regeneration** after a `w3gjs` upgrade. The extraction
   task runs again; the resulting file is diffed against the
   committed version; any changes are reviewed in a pull request.
2. **On diagnostic-driven gap fill** when a real replay produces an
   unmapped-ID diagnostic and the ID belongs to the declared
   coverage scope. The fix is a direct edit to the JSON.

No code change is required for either case (FR-005's editability
requirement).
