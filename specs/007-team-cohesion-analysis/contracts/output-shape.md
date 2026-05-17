# Contract: Analysis Output Shape — Team Cohesion Extension

Structural contract for the new `team` top-level key on the analysis JSON document, plus the two new arrays under `diagnostics`. The authoritative field-level documentation lives in `data-model.md`; this contract captures the **MUST** invariants that tests and downstream consumers (the Visualizer's Team tab, future analytics tooling) rely on.

This contract **extends** `specs/002-replay-analyzer/contracts/output-shape.md` rather than replacing it. Every invariant in the feature-002 contract continues to hold without modification. The invariants below are additive: they describe shapes that did not exist before this feature.

## Top-level keys (extended)

The root is a JSON object with EXACTLY these eight keys (one new — `team`):

```text
{
  "match":       { ... },     // unchanged from feature 002
  "settings":    { ... },     // unchanged from feature 002
  "map":         { ... },     // unchanged from feature 002
  "players":     [ ... ],     // unchanged from feature 002
  "observers":   [ ... ],     // unchanged from feature 002
  "chat":        [ ... ],     // unchanged from feature 002
  "diagnostics": { ... },     // extended (two new sub-arrays — see §Diagnostics extensions below)
  "team":        { ... }      // NEW
}
```

Adding or removing a top-level key from this set is a breaking change requiring concurrent updates to `processor/DATA.md`, `data-model.md`, both contract files, and the Visualizer.

## The `team` block — two valid shapes

The value of `team` MUST be one of exactly two shapes. No other shape, partial shape, or `null` is permitted.

### Shape A — empty state

When the replay does not support team-cohesion analysis, the `team` block has EXACTLY two keys:

```text
"team": {
  "applicable": false,
  "reason":     "noAllies" | "ffa" | "noBattlesDetected"
}
```

`reason` MUST be one of the three string values above. The fourth value `"preFeature007File"` is reserved for the Visualizer-side fallback when the entire `team` key is absent from the document; the analyzer MUST NOT emit it.

### Shape B — populated state

When team-cohesion analysis applies, the `team` block has EXACTLY these eight keys:

```text
"team": {
  "applicable":          true,
  "sharedControl":       { "enabled": boolean },
  "findings":            [ string, ... ],
  "battles":             [ Battle, ... ],
  "itemTransfers":       [ ItemTransfer, ... ],
  "supportEvents":       [ SupportEvent, ... ],
  "resourceCooperation": { "transfers": [...], "generosity": [...] },
  "players":             [ TeamPlayer, ... ],
  "battleSummary":       { "tei": [...], "attributions": [...], "executive": [...] }
}
```

No additional keys are permitted on the populated `team` object.

## Structural invariants

The following MUST hold for every analysis document, regardless of replay content:

1. **Exactly one `team` shape.** Either Shape A (with `applicable: false`) or Shape B (with `applicable: true`). The two shapes are mutually exclusive — `applicable` is the discriminator.
2. **Empty-state minimality.** When `team.applicable === false`, the only other key on `team` is `reason`. No `findings`, no `battles`, no `players`, no `sharedControl`. (Empty arrays / objects for those fields are NOT a substitute — the keys themselves MUST be absent.)
3. **Populated-state completeness.** When `team.applicable === true`, all eight keys listed in Shape B are present. Empty arrays `[]` are permitted (a match with no detected pings emits `team.battles[i].pings: []`); missing keys are not.
4. **Sides are disjoint and non-empty.** For every `Battle`, `sides.teamA.length >= 1`, `sides.teamB.length >= 1`, and `sides.teamA ∩ sides.teamB === ∅`. The label `"teamA"` / `"teamB"` is arbitrary (not tied to lobby `teamId`); within one analyzer run the assignment is deterministic by lowest-slot-id ordering.
5. **Battle indices are contiguous.** `team.battles[i].index === i` for every `i`. Sorted by `startMs` ascending. No gaps, no duplicates.
6. **Battle time bounds.** For every `Battle`: `0 <= startMs < endMs <= match.durationMs`. Battle windows do NOT overlap: for `i < j`, `team.battles[i].endMs <= team.battles[j].startMs`.
7. **Centroid coordinate consistency.** For every `Centroid`: `x === null ⇔ y === null ⇔ source === "missing"`. Numeric coordinates are finite (no `NaN`, no `Infinity`).
8. **Allied distance pair canonicalization.** For every `AlliedDistance`: `fromSlot < toSlot` (strict). One entry per unordered pair of allies on the same side; cross-side pairs are NOT emitted. `distance >= 0` and finite.
9. **Split-engagement biconditional.** For every battle: `splitEngagement.flagged === true` ⇔ `splitEngagement.flaggedSlots.length === 2` ⇔ `splitEngagement.distance > splitEngagement.referenceAura.radius`. When `flagged === false`, `flaggedSlots === []`.
10. **Aura reference resolved.** `splitEngagement.referenceAuraId` is either a 4-character WC3 ability id (resolvable via `auras.json`) OR the literal string `"default"`. When `"default"`, `referenceAuraName === "default 900u"` and the threshold value 900 is implied.
11. **Focus-fire null-or-complete.** For every battle, `focusFire` is either `null` (with a corresponding `diagnostics.cohesionMetricGaps[]` entry naming `focusFire:battle=<index>`) or a fully-populated object with all four keys (`dominantTargetSlot`, `dominantTargetEntity`, `cohesionPercent`, `contributingPlayers`). Partial focus-fire objects are forbidden.
12. **Cohesion percent range.** When `focusFire !== null`, `0 <= cohesionPercent <= 100`. Floating-point.
13. **Ping membership disjointness.** For every `Ping`: `respondedBySlot ∩ engagedElsewhereSlot === ∅`. A slot cannot simultaneously be classified as having responded AND being already engaged.
14. **Ping origin is a teammate.** `Ping.fromSlot` is on the same side as the battle the ping was emitted into (`team.battles[i].pings[].fromSlot ∈ battles[i].sides.{teamA | teamB}`). Pings from non-participants of the battle are NOT emitted under that battle.
15. **Kill credit fractions sum to 1.** For every `KillEstimate.credits`: `Σ credits[].fraction === 1.0` ± `1e-6` (float tolerance). Each fraction `> 0`. The `credits` array is non-empty (kills with no attributable team coverage are not emitted at all — see invariant 25).
16. **Item-transfer mirror.** For every `0x13` (give-item) action in `ParserOutput.events[]`, `team.itemTransfers[]` contains exactly one entry with the matching `timeMs`. Conversely, every `team.itemTransfers[]` entry corresponds to exactly one `0x13` action. Bijection.
17. **Resource-transfer mirror.** For every entry in `players[].resourceTransfers[]`, `team.resourceCooperation.transfers[]` contains exactly one corresponding `AnnotatedTransfer` with the same `fromSlot`, `toPlayerId`, `gold`, `lumber`, `timeMs`. The `purposeHint` field is the only addition. Bijection.
18. **Recipient-fit-class enum.** Every `ItemTransfer.recipientFitClass` is one of: `"good"`, `"wrong"`, `"neutral"`, `"unknown"`. `"unknown"` ⇒ a corresponding `diagnostics.itemAttributeGaps[]` entry exists for either the item id or the recipient hero id.
19. **Support-event type enum.** Every `SupportEvent.type` is one of: `"missedSave"`, `"supportSpellCast"`. The `"supportSpellCast"` variant is emitted only when the Phase 0 `0x14` probe succeeded; otherwise NO `supportSpellCast` rows appear and a single `diagnostics.cohesionMetricGaps[]` entry names `supportSpellCast` with `reason: "phase0ProbeFailed"`.
20. **Missed-save ranges.** For every `SupportEvent` with `type === "missedSave"`: `distanceAtDeath <= 800` (the rescue-eligible range) and `holderSlot !== deceasedSlot` (a hero cannot save itself).
21. **Purpose-hint enum.** Every `AnnotatedTransfer.purposeHint` is one of: `"tierUpAssist"`, `"baseDefense"`, `"lateGameTopUp"`, `"none"`.
22. **Generosity null-pair coupling.** Within one `GenerosityRow`: `generosityPercent === null ⇔ (estimatedMinedGold === null OR estimatedMinedLumber === null)`. Numeric `generosityPercent >= 0` (float; not capped at 100).
23. **Findings closed enum.** Every entry in `team.findings[]` is one of the closed v1 enum: `"sharedControlDisabled"`. (Future features extend this enum additively; v1 has exactly one possible value.)
24. **TEI sentinel and bounds.** Every `BattleTEI.teamSideTei.{teamA,teamB}` and every `perPlayerTei[].tei` is either `null` (with a corresponding `diagnostics.cohesionMetricGaps[]` entry) OR a finite number `>= 0`. The value `99.0` is the zero-loss sentinel cap and is permitted as a regular numeric value (not `null`, not `Infinity`). Per-player TEI is computed with the `max(player_value_lost, 1)` normalization documented in `plan.md`.
25. **Kill emission gating.** A kill that has zero team attack-action coverage in the 5-second pre-death window is NOT emitted to `KillEstimate[]`. If the analyzer detects unattributed kills, it emits ONE match-level entry to `diagnostics.cohesionMetricGaps[]` of the form `{ metric: "killParticipation", reason: "N kills had no attack-action coverage" }`, where `N >= 1`.
26. **Attribution validity.** Every `Attribution`: `0 <= battleIndex < team.battles.length`, `playerSlot` is in `team.battles[battleIndex].sides.{teamA | teamB}`, `reason` ∈ closed v1 enum: `"splitEngagement"`. The corresponding `team.battles[battleIndex].splitEngagement.flagged === true`.
27. **Executive ordering and length.** `team.battleSummary.executive` has length `0..3`. When non-empty, sorted by `weightedSeverity` desc; ties broken by `battleIndex` asc (for findings with `battleIndex !== null`). `rank` field is `1, 2, ..., length` with no gaps.
28. **Executive evidence resolves.** Every `ExecutiveFinding.evidenceRef` resolves to a real index / name in the document: `kind: "battle"` ⇒ `0 <= battleIndex < team.battles.length`; `kind: "supportEvent"` ⇒ `0 <= index < team.supportEvents.length`; `kind: "itemTransfer"` ⇒ `0 <= index < team.itemTransfers.length`; `kind: "globalFlag"` ⇒ `name ∈ team.findings`.
29. **Entity reference resolution.** Every `EntityRef` (`item`, `dominantTargetEntity`, `victimEntity`, `recipientHero`, etc.) has shape `{ id: string of length 4, name: string non-empty, unknown: boolean }`. When `unknown === true`, `name === id`, AND a corresponding entry exists in `diagnostics.unmappedEntityIds[]` or `diagnostics.itemAttributeGaps[]`.
30. **Player-slot consistency.** Every `slot` value (in `centroids[].slot`, `Attribution.playerSlot`, `Ping.fromSlot`, etc.) MUST be the `id` of an entry in the document's `players[]` array (i.e., a real player slot present in the replay). Slots `12` and `15` (neutral / creep) MUST NOT appear in `team.*` slot fields.
31. **Time fields are non-negative integers in milliseconds.** Every field whose name ends with `Ms` or `TimeMs` (e.g., `startMs`, `endMs`, `timeMs`, `killTimeMs`, `deathTimeMs`) is a non-negative integer.

## Diagnostics extensions

Two new arrays appear under the existing `diagnostics` object. Both follow the same shape rules feature 002's `unmappedEntityIds` follows: deduplicated, empty when nothing degraded, additive only.

```text
"diagnostics": {
  "parserId":           "...",                   // unchanged from feature 002
  "parserParseTimeMs":  number,                  // unchanged from feature 002
  "unmappedEntityIds":  [ ... ],                 // unchanged from feature 002 — see invariant 32
  "analyzerVersion":    "...",                   // unchanged from feature 002
  "cohesionMetricGaps": [                        // NEW
    { "metric": string, "reason": string },
    ...
  ],
  "itemAttributeGaps":  [                        // NEW
    { "id": string, "category": "item" | "hero" },
    ...
  ]
}
```

Diagnostic invariants:

32. **`unmappedEntityIds` extended categories.** The `category` field of `unmappedEntityIds[]` entries MAY take new values beyond feature 002's set: `"ability"` (auras), `"unitCost"` (unit_costs gaps). Existing categories (`"hero"`, `"unit"`, `"building"`, `"upgrade"`, `"item"`) continue to apply. Deduplicated by `(category, id)`.
33. **`cohesionMetricGaps` shape.** Every entry has exactly two string keys: `metric` and `reason`. Deduplicated by `(metric, reason)`. The `metric` field uses a `<name>` or `<name>:battle=<index>` form; the `reason` field is human-readable English.
34. **`itemAttributeGaps` shape.** Every entry has exactly two keys: `id` (4-character string), `category` ∈ `{ "item", "hero" }`. Deduplicated by `(category, id)`.
35. **Diagnostics ⇔ degradation.** Every numeric field that is `null` in `team.*` (when `applicable === true`) has a corresponding diagnostics entry naming it. Every diagnostics entry refers to a real degradation in the output. Bidirectional.

## Cross-cutting invariants

Apply across the whole document (parser-output AND analysis-output considered together):

36. **Content determinism.** Re-running the analyzer on the same parser-output JSON, with identical `entity_names.json`, `auras.json`, `item_attributes.json`, `unit_costs.json`, and `rescue_items.json`, produces a byte-identical analysis JSON EXCEPT for `diagnostics.parserParseTimeMs` (forwarded volatile parser value, per feature 002 invariant 7). All fields under `team.*` are deterministic.
37. **Strict superset.** Comparing the analysis output before this feature shipped (the feature-005 baseline) to the analysis output after, the diff is a strict superset: every key under `match`, `settings`, `map`, `players`, `observers`, `chat`, and `diagnostics` (except the two new arrays under `diagnostics`) appears with the same value. The only additions are the new top-level `team` key, `diagnostics.cohesionMetricGaps`, and `diagnostics.itemAttributeGaps`.
38. **No re-derivation.** No field within `team.*` duplicates information already present elsewhere in the document. (The `AnnotatedTransfer` mirror of `players[].resourceTransfers` is the deliberate exception for one-stop access; the `purposeHint` is the new information that justifies the duplication.)

## Non-invariants (explicit)

The following are NOT guaranteed and consumers MUST NOT rely on them:

- **Field order within an object.** JSON objects are unordered; the analyzer emits keys in a stable but unspecified order.
- **Order of `findings[]` entries.** Logically a set; emitted as an array for JSON-natural rendering. Consumers MUST treat it as a set.
- **Order of `respondedBySlot[]` / `engagedElsewhereSlot[]` entries.** Sets, emitted as arrays.
- **Order of `Battle.kills[]` entries when multiple kills share a `killTimeMs`.** Stable within a run, unspecified across implementations.
- **The exact value of heuristic constants** (`MIN_RESPONSE_DELTA`, the 60-s centroid lookback, the 5-s pre-death window for kill credit, the 15-s ping reaction window). These live in `processor/team/*.py` and may be tuned without breaking the contract — consumers MUST NOT depend on their specific values, only on the invariants above.
- **The exact battle count, transfer count, ping count on any specific replay.** These are fixture-dependent acceptance values recorded in `quickstart.md`, not contract invariants.
- **The exact wording of `ExecutiveFinding.summary` strings.** Coach-style display text; the structure (top-3, sorted, ranked) is the contract — the prose is not.
- **Trailing newline in the output file.** Same as feature 002 — `json.dump` + one trailing `\n`; consumers parse the whole file.
- **The non-volatile fields' string-byte equivalence across analyzer versions.** A patch-level analyzer release MAY reformat numeric output (e.g., `1.0` vs `1`) without violating contract — only logical equivalence is guaranteed across versions.

## Compatibility

- **Additive extensions to `team.*`** (new sub-keys on `Battle`, new event types under `SupportEvent`, new attribution reasons, new finding kinds) are NOT breaking and require updating `data-model.md` plus this contract in the same change.
- **Adding new closed-enum values** to `findings[]`, `recipientFitClass`, `purposeHint`, `Attribution.reason`, `ExecutiveFinding.kind`, or `EvidenceRef.kind` is NOT breaking — consumers MUST handle unknown enum values gracefully (fallback rendering, not a crash). The Visualizer's contract for handling unknown enum values lives in `contracts/ui-contract.md` (not in this file).
- **Renaming or removing a key**, **changing the discriminator semantics** (e.g., redefining `applicable`), or **breaking a mirror invariant** (one-to-one relationship between events and `team.*` arrays) IS breaking and requires a feature spec amendment with explicit migration plan.
- **Changing a heuristic constant** is NOT breaking (per non-invariants above) but the change MUST be reflected in `quickstart.md` if the change shifts a fixture's acceptance values.

## Test coverage map

The Phase 1–6 pytest suite MUST include at least one test per invariant 1–35 above. Cross-cutting invariants 36–38 each have a dedicated test in `processor/tests/test_existing_fields_unchanged.py` and `processor/tests/test_team_block_shape.py`. The mapping from invariant number to test file is recorded in `tasks.md`.
