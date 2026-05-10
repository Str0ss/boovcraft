# Research — Team Cohesion Analysis

This document records decisions taken during Phase 0 of feature 007: where data comes from, why heuristic constants are set the way they are, and which third-party libraries were considered (and rejected). Where a decision depends on data we have not yet observed at the time the plan was written, the placeholder `[Phase 0 probe — to be filled in by T008 / T009]` is used; these placeholders are resolved in the same PR that lands the probe.

This document is *not* a contract — it captures the reasoning behind decisions that the spec / plan / data-model / contracts encode normatively. When research and one of those documents disagree, the normative document wins; an inconsistency is a bug to be filed against this file, not against the contract.

## R1. Phase 0 probe — `0x14` action shape (cooperative spell-cast feasibility)

**Question.** Does the parser-output's `0x14` action carry enough information to distinguish a spell cast targeting an ally unit from a self-targeted or enemy-targeted cast?

**What `0x14` looks like (observed in `base_2`).** From the Phase-0 dump (`processor/tools/probe_spell_target.py` against both fixtures), each `0x14` action has the shape:

```text
{
  "id":          20,
  "abilityFlags": <uint32>,
  "orderId1":    [<4 bytes>],   // primary order (often the ability id when reversed)
  "orderId2":    [<4 bytes>],   // secondary order (often a target type)
  "targetA":     [<float>, <float>],
  "targetB":     [<float>, <float>],
  "owner":       <uint32>,
  "category":    <uint32>,
  "flags":       <uint32>
}
```

The `targetA` / `targetB` fields are coordinates (WC3 map units). The `owner` field is the player slot of the targeted unit *when the target is a unit*; the value `0xFF` (255) appears in some samples and corresponds to a non-unit / ground target.

**Decision (T008 outcome — 2026-05-08): NO — drop `supportSpellCast` emission for v1.**

The probe (`processor/tools/probe_spell_target.py`) extracted every `0x14` action from both committed fixtures. Aggregate findings:

- `base_1.w3g.json`: 111 occurrences. `base_2.w3g.json`: 19 occurrences. Total: 130.
- The dominant `(orderId1, orderId2)` pairs are **building placements**, not spell casts:
  - `(0x0300_0d00, "htow")` × 23 — Town Hall placement
  - `(0x0300_0d00, "ngol")` × 20 — gold mine placement
  - `(0x0300_0d00, "WTtw")` × 16 — watchtower placement
  - `(0x0300_0d00, "YTct")` × 15 — building-shadow during placement
  - `(0x0300_0d00, "hcas"|"hlum"|"emow"|"owtw"|"hgtw"|"ntav"|"ngme")` — Castle, Lumber Mill, Moon Well, Watchtower, Guard Tower, Tavern, Goblin Merchant
  - `("ugol", "ngol")` × 3 — Haunted Gold Mine on a goldmine
- The `owner` field varies between real player slot ids (0–7) and sentinel values (27, 255 = `0xFF`) on the SAME building-placement events. It does not reliably name a "target unit's owning slot."
- The `category` field has 5 distinct values; none of them distinguishes ally-target from self-target from enemy-target consistently.

**Conclusion.** `0x14` in these fixtures is overwhelmingly a *position-and-building-id* action used for building placement — not the discriminator for ally-targeted spells we hoped for. Cooperative spell casts (Spirit Link, Inner Fire, Heal, Bloodlust, Roar on an ally) likely flow through `0x12` (TARGET_POSITION_AND_UNIT) with the target unit being the ally — but distinguishing those casts from a vanilla right-click on an ally requires per-hero ability-state tracking that is materially more complex and out of scope for v1.

**Action taken.**

- `team.supportEvents[]` does NOT include any `"supportSpellCast"` entries in v1. The discriminated-union shape from `data-model.md § SupportEvent` keeps the variant for forward compatibility, but no code paths emit it.
- `processor/analyze.py` MUST emit one match-level entry into `diagnostics.cohesionMetricGaps[]` of the form:
  ```json
  { "metric": "supportSpellCast", "reason": "phase0ProbeFailed: 0x14 is dominated by building-placement actions; reliable ally-vs-self target discrimination not feasible without per-hero ability-state tracking" }
  ```
- T028 in `tasks.md` is dropped from the implementation set; `team/support.py` only implements `extract_item_transfers` and `detect_missed_saves`.
- A follow-up feature (provisionally feature 009) will re-investigate ally-targeted spell detection via `0x12` + ability-state tracking. Out of scope for 006.

This decision is consistent with FR-029 graceful degradation and US2's "stretch goal" status. The rest of US2 (item gives + missed saves) ships unaffected.

## R2. Lookup-table sources

### `processor/auras.json`

**Source.** `w3gjs`'s ability-data tables. At the time of writing, the `w3gjs@4.0.0` package ships ability metadata under `node_modules/w3gjs/dist/lib/mappings/abilities.js` (path verified during T002 implementation; if `w3gjs` upgrades the path, T002's regenerator script is updated in the same PR).

**Initial coverage** (validated against `base_1` and `base_2` heroes seen in `players[].heroes`):

| Aura | Ability id | Owner hero | Radius | Type |
|---|---|---|---|---|
| Devotion Aura | `AHad` | `Hpal` (Paladin) | 900 | support |
| Brilliance Aura | `AHab` | `Hamg` (Archmage) | 900 | support |
| Endurance Aura | `AEar` | `Edem` (Demon Hunter) | 900 | support |
| Trueshot Aura | `AEar` (confirm — distinct id may apply) | `Emoo` (Priestess of the Moon) | 900 | support |
| Unholy Aura | `AUau` | `Udea` (Death Knight) | 900 | support |
| Vampiric Aura | `AUav` | `Ushd` (Shadow Hunter) — actually Orc Shaman class hero; `Oshd` confirm | 900 | damage |
| Command Aura | `AOcr` | `Obla` (Blademaster) | 900 | support |

The Trueshot / Vampiric ability-id values above are placeholders pending T002's actual extraction; the regenerator script names the canonical ids. If T002 surfaces additional auras present in the committed fixtures, they are appended without amending this section's count (the table is data, the rationale is the principle).

**Manual overrides.** Per the convention established by `entity_names.json`, `processor/tools/build_auras.py` carries a `MANUAL_OVERRIDES` dict at the top for auras observed in real fixtures but absent from `w3gjs`'s tables. Initial value: empty. Entries added only when a fixture surfaces them.

### `processor/item_attributes.json`

**Source.** The `entity_names.json` item entries, plus an inline name-pattern classifier in `processor/tools/build_item_attributes.py`. The classifier:

- Items whose name contains `"Tome of Intelligence"` → `primary: "int"`.
- `"Tome of Strength"` → `primary: "str"`.
- `"Tome of Agility"` → `primary: "agi"`.
- `"Tome of Power"`, `"Tome of Experience"`, `"Tome of Retraining"` → `primary: "universal"` (no attribute affinity).
- Items whose name starts with `"Orb of "` → `primary: "agi"` (orbs are universally an agility-attack hero's domain in WC3 ladder).
- Items whose name contains `"Staff of"` → `primary: "universal"`. The single rescue item `"Staff of Preservation"` (`stwp`) gets `isRescue: true`.
- Items whose name contains `"Scroll of Healing"`, `"Scroll of Town Portal"`, `"Healing Potion"` → `primary: "universal"`, `isRescue: true`.
- Everything else → `primary: "none"`, `isRescue: false`.

**Initial coverage.** Every item id appearing in either committed fixture's `players[].items.summary` MUST resolve to a non-`"unknown"` recipientFitClass after T030's tests run. Gaps observed during T004 implementation are filled inline before commit.

### `processor/unit_costs.json`

**Source.** `w3gjs`'s unit-data tables (`node_modules/w3gjs/dist/lib/mappings/units.js`). For each unit / building / hero id, extract the `goldcost`, `lumbercost`, and `foodused` fields.

**Initial coverage.** Every entity id appearing in either committed fixture's `players[].{units,buildings,heroes}.summary` MUST be present in `unit_costs.json`. T006 implements a script-local validation pass that walks both `*.analysis.json` files (regenerated against the current entity names map) and reports missing ids. Missing ids are added to the regenerator's `MANUAL_OVERRIDES` dict at the top of the script.

### `processor/rescue_items.json`

**Source.** Derived array filtered from `item_attributes.json` where `isRescue === true`. Computed by `processor/tools/build_item_attributes.py` and committed for audit; `analyze.py` reads either file (whichever is more convenient at a given call-site), and T074 asserts they agree.

## R3. Heuristic constants — rationale

Each constant chosen in `plan.md` § Heuristic decisions has a brief rationale below. Constants are stored at the top of their owning module (`processor/team/<module>.py`) and tunable in `tasks.md` after first pytest run; the rationale here records *why* the initial value was chosen, not *what* it is (the value is in code).

### Battle window detection (`processor/team/battles.py`)

- **Bucket size — 5 seconds.** Short enough to detect a quick skirmish (a 15-second fight in 3 buckets), long enough that single-shot harass on a peon doesn't open a window. WC3's combat rhythm at the unit-engagement level operates in ~5–15 second exchanges; sub-5s buckets create false positives on creep aggro that the run-length floor would otherwise have to absorb.
- **Run-length floor — 3 buckets (15 s).** A real team fight is at minimum a hero engagement plus a follow-up cycle; below 15 seconds is almost always harass. Manual review of `base_1` and `base_2` will validate this against the SC-001 zero-error bar; if a true fight in either fixture is shorter, the floor drops to 2.
- **Gap tolerance — 2 buckets (10 s).** Combatants kite, retreat to heal, reposition for the second engagement. A ~10-second disengagement is part of one fight, not the boundary between two. Above 10 s the second fight is a separate decision and gets its own window.

### Centroid lookback (`processor/team/centroids.py`)

- **Lookback window — 60 seconds.** At a typical APM (~120) a player issues ~120 commands per minute, so 60 s gives ~120 target points for averaging — well above noise. Shorter windows (e.g., 30 s) underweight passive defenders who command rarely. Longer windows (e.g., 120 s) over-anchor on stale positions across map rotations.
- **Single-handle fallback — 1 commanded position.** When fewer than 3 handles have been commanded in the lookback window, fall back to the single most-recent commanded position. This is the "passive defender" path Tier 2 was specifically designed to address.

### Ping reaction (`processor/team/cohesion.py`)

- **`MIN_RESPONSE_DELTA = 200` map units.** A typical melee unit's collision radius is 32 units; 200 units is roughly a 6-unit walk distance, well above noise from issuing one or two commands in the wrong direction. Below 100 a player who happened to right-click in the general direction of the ping would falsely register as responding; above 400 a player who responded by sending a small force toward the ping (rather than the full army) would falsely register as ignoring.
- **`RESPONSE_WINDOW_MS = 15_000` (15 s).** Unit ground-speed in WC3 is ~270 units/s for fast units (≈ 4000 units in 15 s — across half the map). Below 10 s a player who saw the ping but had to disengage from another fight first would falsely register as ignoring. Above 30 s the response is too late to matter — the original threat has already resolved.

### Kill credit (`processor/team/kills.py`)

- **Pre-death window — 5 seconds.** Same as the battle bucket, deliberately for consistency. A unit's death is preceded by ~5–10 seconds of focused damage from multiple attackers; 5 s captures enough attackers without admitting actions from a different fight.
- **Disappearance threshold — 30 seconds without re-selection.** A handle dropped from selection for 30 s is almost certainly dead (revival fully respawns to a new handle in WC3). Below 10 s a player just clicked elsewhere; above 60 s the kill is recorded too late to be useful for TEI in the original battle window.

### TEI (`processor/team/tei.py`)

- **Value function — gold + lumber, supply ignored.** Per the user's "Gold + lumber (supply optional)" decision in plan-level Q&A. Supply is recorded in `unit_costs.json` for future use (e.g., army-size ratio metrics) but does not enter v1 TEI.
- **Zero-loss sentinel — `99.0`.** Numeric, sortable, finite. Visualizer renders it as `"≥ 99"`. Realistic TEI values in observed `base_1` battles peak around 3–5; 99 is comfortably above any realistic finite value while remaining a valid float.
- **Per-player divisor floor — `max(player_value_lost, 1)`.** Prevents division-by-zero when a player contributed attack damage but lost no units. The `1` is a unit gold-equivalent and is consistent with the cap-at-99 sentinel — a player with one Footman lost while contributing 50% of a 915-gold trade will read as `0.5 × 915 / 135 ≈ 3.39` (the worked example in spec.md), and a player with zero Footmen lost reads as `0.5 × 915 / 1 = 457.5 → cap at 99.0`.

### Attribution (`processor/team/attribution.py`)

- **TEI threshold — `< 1.0`.** A team-side TEI < 1.0 means the team lost the value trade in that battle. Above 1.0 a split engagement may have occurred but the team still won, so no blame is warranted (someone else carried the fight).
- **Outlier multiplier — `1.5 × mean_pairwise_distance`.** A geometric heuristic: a player whose distance to the team-centroid is more than 1.5× the typical inter-ally distance is materially "out on their own." Tighter (1.2×) over-flags; looser (2.0×) under-flags. Manual review on `base_1`'s flagged battles validates the constant against perceived blame.

### Severity weights (`processor/team/attribution.py`)

Weights are calibrated against `base_1` and `base_2` such that the executive top-3 visibly reflects what a coach watching the replay would call out. Initial values:

| Finding kind | Base weight | Rationale |
|---|---|---|
| `splitEngagement` | 3.0 | The user's #1 cited failure mode (per the original requirements). |
| `missedSave` | 2.0 | Specific, actionable, hero-level — reads as a clear coaching moment. |
| `lowTei` (no other findings) | 1.5 | Still a battle the team lost, even without an obvious cause. |
| `ignoredPing` | 1.2 | Communication failure — cheap to call out, real impact. |
| `sharedControlDisabled` | 1.0 | Match-level, single occurrence; informational. |
| `wrongItemTransfer` | 0.8 | Specific but minor compared to a fight loss. |

Multiplier `× min(battle_duration / 60, 3.0)` — longer fights matter more, capped at 3× for fights past 3 minutes. The cap prevents a 10-minute slow burn from monopolizing the top-3.

## R4. Princ. VI evaluation — third-party libraries

Principle VI requires a structured evaluation against four criteria (active maintenance ≤ 12 mo, broad adoption, permissive license, API stability) for any new external dependency. Feature 007 introduces **no new dependencies** — Python stdlib (`json`, `math`, `statistics`) covers all algorithmic needs on the Processor side; the Visualizer reuses React + ECharts + Vite from feature 005.

The evaluation table below records the libraries that were *considered and rejected*, so a future contributor proposing them does not re-derive the same conclusion.

| Candidate | Domain | Decision | Rationale |
|---|---|---|---|
| `numpy` | Vector / matrix math (centroids, distances) | **Reject** | One Euclidean-distance call site and one mean-of-coordinates call site. Both are 2–3 lines of inline Python. Adding a numpy dependency violates the analyzer's "stdlib-only at runtime" posture from feature 002. Princ. VI YAGNI escape hatch applies. |
| `scipy.spatial` | Geometry (centroid, convex hull, etc.) | **Reject** | Same reason as numpy, plus `scipy` is a much larger transitive surface. A future feature that needs convex hulls might justify the dependency; v1 of cohesion analysis does not. |
| `pandas` | Tabular aggregation (transfers, KP%) | **Reject** | The aggregations are over `O(events)` size data already loaded as Python dicts. `pandas` overhead exceeds the benefit by an order of magnitude. Stdlib `collections.defaultdict` + `sum()` is simpler and faster at this scale. |
| `pydantic` | Runtime schema validation of lookup tables | **Reject** | The four lookup tables have ~10 fields each. A `_validate_aura_table` function in `team/__init__.py` is ~30 lines; adding pydantic for that is over-engineering. (Princ. III + VI YAGNI agree.) |
| `shapely` | Map geometry | **Reject** | We do not actually intersect polygons or compute convex hulls in v1. Centroids and Euclidean distances do not need a geometry engine. |
| `chart.js` (Visualizer) | Per-battle TEI bar chart | **Reject** | ECharts is already in the bundle from feature 005. Adding a second chart library doubles the bundle size and creates two visual languages in the same tab. |
| A custom DSL for severity-weight rules | Configurability of executive ranking | **Reject** | Princ. III explicitly forbids "just-in-case" rule engines. The six-row table in `team/attribution.py` is the single place severity is defined; tuning it is a one-line edit. |

If a future feature adds a real need for one of these libraries — multi-replay aggregation might justify pandas, on-map geometric analysis might justify shapely — the evaluation re-runs at that time against fresh evidence. The rejections above are scoped to feature 007's needs.

## R5. Constants tuning protocol

Constants live in code, not in committed JSON; tuning them is a one-line edit, not a schema migration. The protocol for tuning:

1. After Phase 1b's first pytest run, run `python3 processor/analyze.py sample_replays/base_1.w3g.json` and inspect `team.battles[]` against the recorded fights in the replay (manual review via the Visualizer's existing tabs gives a sense of where the fights are).
2. If a fight that a human would call "a fight" was not detected as a battle window, drop the run-length floor from 3 to 2 and re-run. If creep aggro is creating false-positive battle windows, raise it to 4.
3. Repeat for the gap tolerance, the centroid lookback, the ping `MIN_RESPONSE_DELTA`, and the attribution outlier multiplier.
4. Once the SC-001 zero-error bar is met on both fixtures, freeze the constants in code and update `quickstart.md` with the calibrated values + the resulting fixture-specific expected counts.
5. Any subsequent change to a constant requires re-running the SC-001 check and updating `quickstart.md`.

The protocol is recorded here, not in `plan.md`, because tuning is research, not architecture.

## R6. Open questions deferred to follow-up features

Decisions that came up during research but are explicitly out of scope for feature 007:

- **Movement-aware position interpolation (Tier 3).** Would replace the "last commanded position" approximation with a real walk-the-pathfinder simulation. Rejected for v1 — exceeds Principle III's "no partial WC3 engine" boundary.
- **Multi-replay cohesion aggregation.** Rolling up cohesion findings across many replays for a team's training journal. Out of scope; per-replay only in v1.
- **In-tab map rendering.** Drawing centroids on the actual map tile is a Map-tab feature; the data is in the JSON but the rendering is feature 003-style placeholder for now.
- **Coaching-prose generation.** Translating findings into "you should have done X" advice. The Analysis tab's eventual LLM-ready text export will be the home for this; the Team tab in v1 surfaces *findings*, not advice.
- **Per-team-chat sentiment analysis.** Already-surfaced chat is in the Summary tab; analyzing whether the team coordinated verbally is its own feature.
- **Hero-level KP (kill participation) by hero archetype.** Whether the Paladin or the Mortar Team carried more is a follow-up; v1 is per-player, not per-hero.

These are recorded so a future PR proposing them does not re-derive that they are out of scope here.
