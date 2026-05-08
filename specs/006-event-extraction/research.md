# Phase 0 Research: Event Extraction

This document resolves the eleven open questions raised in the Plan's
Phase 0 outline. Each entry uses the **Decision / Rationale /
Alternatives considered** form. Where a decision depends on a catalog
that lives in `processor/entity_names.json`, the catalog itself is
finalized in code (and listed exhaustively in `processor/EVENTS.md`)
rather than enumerated here.

## R1. Which w3gjs action types carry coordinates, and where?

**Decision**. The Processor's coord-retention change reads positions
from these w3gjs action ids in the parser-output stream:

| Action id (w3gjs) | Name (w3gjs internal) | Position field |
|---|---|---|
| `0x11` | UnitBuildingAbilityActionTargetPosition | `position` (object with `x`, `y`) |
| `0x12` | UnitBuildingAbilityActionTargetPositionTargetObjectId | `position` |
| `0x13` | GiveItemToUnitAction | `position` |
| `0x14` | UnitBuildingAbilityTwoTargetPositions | `position` (and `position2` — see below) |

`0x14` is a two-target action. We retain only the **first** position
on the timed-action entry. The second position is dropped. (None of
the v1 event kinds need it; if a future kind does, the plan can
revisit.)

All other action ids — `0x10` (no-position ability), `0x16`
(selection), `0x17`/`0x18`/`0x19`/`0x1A`/`0x1B` (group/hotkey
operations), `0x21`/`0x22` (basic), `0x50` (ally options), `0x51`
(transfer resources), and the chat/leave-game blocks — do not carry a
spatial position and are emitted on the analyzer output without `x`/`y`
fields.

For **production-order entries**, the same position-source rule
applies: the entry inherits the position of the underlying replay
action (`0x11`/`0x12` for a building placement; the unit-train and
research actions are typically `0x10` without position, so train and
research entries will *not* carry coordinates — this is the correct
behavior, since "trained inside this barracks" is not a spatial
event).

**Coordinate units** are w3gjs's raw `position.x` / `position.y`
values: signed integers in WC3 map units. We do not transform them.
Per-replay thresholds (R2–R4) absorb the unit choice.

**Rationale**. Forwarding w3gjs's existing position fields verbatim is
the smallest possible coord-retention change and respects Principle II
(no parallel reinterpretation of replay bytes).

**Alternatives considered**. (a) Convert coordinates to a normalized
`[0, 1]` range against a per-replay bounding box. Rejected: the
analyzer would have to compute the bounding box, which is plan-stage
spatial work. The per-replay-threshold approach in the events stage
absorbs the same need without changing the analyzer's contract. (b)
Retain the second position from `0x14` actions as `x2`/`y2`. Rejected
under YAGNI: no v1 event kind needs it.

## R2. Per-replay home derivation

**Decision**. For each player, the home location is the unweighted
centroid of all coordinate-bearing **building placements** issued by
that player within the first **120 seconds** of in-game time.
Specifically:

```python
candidates = [
    (e.x, e.y)
    for e in player.production.buildings.order
    if e.timeMs <= 120_000 and "x" in e and "y" in e
]
home = (mean(c[0] for c in candidates), mean(c[1] for c in candidates))
```

**Fallback (FR-028)**. If a player issued zero coordinate-bearing
building placements in the first 120 seconds, the home is the
unweighted centroid of that player's first 25 coordinate-bearing
timed actions (any category). The choice of fallback is recorded on
the diagnostics block under
`diagnostics.players[<id>].homeDerivation` as either
`"primary"` or `"fallback:firstActions"`.

**Rationale**. Building placements are the most reliable spatial
signal: workers right-click around the starting mine cluster which
is itself adjacent to the starting hall, but right-clicks include
"send a worker to gather lumber 2000 units away" noise; building
placements are explicit player intent at a specific coordinate. The
120 s window covers any opener that delays construction (Random race
identification, scout-first, etc.) without including mid-game
expansion placements.

**Alternatives considered**. (a) The first main-hall (`htow`/`ogre`/
`unpl`/`etol`) placement coordinate. Rejected: the *starting* hall
predates the replay's action stream and isn't placed by the player;
later main-hall placements are expos, not home. (b) Centroid of the
first 30 s of right-click actions. Rejected: rightclick targets
include movement intentions to non-home locations and are noisier
than building placements.

## R3. Per-replay home-radius derivation

**Decision**. For each player, the home radius is `max(d)` over the
distances `d` from that player's home (R2) to each of that player's
coordinate-bearing **building placements within the first 180
seconds**, with a per-replay floor of `0.10 × map_active_diagonal`,
where:

```python
map_active_diagonal = sqrt(
    (max_x - min_x)**2 + (max_y - min_y)**2
)
```

with `max_x`, `min_x`, `max_y`, `min_y` taken over all
coordinate-bearing actions across **all players** in the replay.

**Fallback (FR-028)**. If the player has fewer than 3 building
placements in the first 180 s (typical for a heavily-harassed early
game, or a quick disconnect), the radius is set directly to
`0.10 × map_active_diagonal`. The choice is recorded under
`diagnostics.players[<id>].homeRadiusDerivation`.

**Rationale**. The first 180 s is wider than R2's 120 s on purpose:
the radius needs to contain the player's whole base footprint
(altar, blacksmith, supply, towers), not just the early eco
buildings. The `0.10 × map_active_diagonal` floor ensures a tight
opening (e.g., 2 farms next to the hall) doesn't produce a tiny home
radius that would falsely flag every move outside the inner base as
a "creeping departure". The 0.10 multiplier is a per-replay relative
quantity, not a hardcoded map-unit constant — FR-027 compliant.

**Alternatives considered**. (a) 90th percentile of the distance
distribution. Rejected: tighter than `max` and less robust to a
single far-out tower placement; the `max` + per-replay floor pair is
simpler and covers the same edge cases. (b) Hardcoded `2000` map
units floor. Rejected: violates FR-027.

## R4. Engagement-cluster radius and time scale

**Decision**. Joint engagements (FR-018) are detected with
`sklearn.cluster.DBSCAN` over points in **3-D normalized space**:

```text
point = (x, y, t * SCALE)
SCALE = engagement_radius / engagement_time_window_seconds
```

where `engagement_radius = 0.05 × map_active_diagonal` (R3) and
`engagement_time_window_seconds = 5`.

DBSCAN parameters:
- `eps = engagement_radius`
- `min_samples = 4` (a cluster needs at least 4 actions; with our
  participant rule below, that means at least one teammate
  contributed two actions).

After clustering, a cluster is kept as a "joint engagement" event
only if it spans **two or more distinct teammate `playerId`s**.
Single-player clusters are discarded (they are creep-camp clusters,
relevant to FR-014 instead).

**Rationale**. The `0.05` multiplier on `map_active_diagonal` sets
the spatial radius at roughly the size of a single skirmish (siege
tank range, hero ability radius); the 5-second time window matches
the cadence of real fights. Scaling time by `radius / time_window`
ensures the 3-D ε ball is effectively a cylinder of radius
`engagement_radius` and height `engagement_time_window`.

**Alternatives considered**. (a) HDBSCAN (variable density). Rejected
under YAGNI — joint-engagement clusters are not pathologically
varying in density, and HDBSCAN is a heavier dependency surface. (b)
Pure spatial clustering followed by temporal filtering. Rejected:
cleaner with a single 3-D pass; same result.

## R5. Idle-period and production-stall thresholds

**Decision**.
- **Idle period (FR-010)**: minimum gap of **15 seconds** with zero
  timed actions for the player.
- **Production stall (FR-020)**: minimum gap of **45 seconds** with
  zero `production.*.order[]` entries while the player continues to
  issue any timed actions (i.e., not idle).

**Rationale**. 15 s is roughly 5× the cadence of an active player
(WC3 pros sustain 200+ APM = one action per 0.3 s; 15 s of silence is
a clear behavioral break). 45 s is approximately the build time of a
mid-tier unit; a stall longer than one production cycle while still
clicking implies the player is doing something other than queuing
production (harass, micro, retreat).

These are absolute time constants, not spatial thresholds — FR-027's
"no hardcoded map units" rule does not apply.

**Alternatives considered**. (a) Per-player APM-derived idle gap.
Rejected: it makes the threshold drift with player skill, which is
the wrong semantics — we want "idle" to mean the same thing for a
500-APM Korean as for a 50-APM novice. (b) 30 s idle minimum. Too
coarse — fast retreats and re-engagements get conflated.

## R6. Transfer-burst inter-transfer-gap threshold

**Decision**. **30 seconds** between consecutive same-pair (sender,
receiver) transfers. Transfers separated by ≤ 30 s are clustered
into a single "transfer burst" event (FR-022); larger gaps split the
sequence.

**Rationale**. A burst of resource transfers is almost always
shift-clicked or rapid-clicked within a single APM burst; 30 s
separates intentional bursts from coincidentally-adjacent transfers.

**Alternatives considered**. (a) 10 s. Rejected: a single burst can
include a 15 s pause to gather more lumber before sending again, and
splitting that into two events is noisy. (b) 60 s. Rejected: too
permissive — distinct narrative beats merge into one.

## R7. Tower entity-id catalog (per race)

**Decision**. The towers-of-record set is finalized in code by
filtering `processor/entity_names.json` for the building ids whose
human-readable names contain "Tower" (case-insensitive) and whose
race attribution matches one of H/O/U/N. The exhaustive list lands in
`processor/EVENTS.md` under the FR-015 section.

The seed list (used to validate the filter and as a known-good
sanity set) for the v1 implementation:

| Race | Entity ids |
|---|---|
| Human | `hgtw` (Guard Tower), `hctw` (Cannon Tower), `hatw` (Arcane Tower), `hwtw` (Scout Tower) |
| Orc | `otto` (Watch Tower) — Orc has limited pure-tower buildings |
| Undead | `unpl` excluded (it's the hall), `uzig` excluded (ziggurat is supply); `usep` (Spirit Tower), `unzc` (Nerubian Tower upgrade) |
| Night Elf | `eate` (Ancient of War — wartime tower), `eaom` (Ancient of Lore) excluded; effective NE towers are limited to base-anchored ancients |

Edge case: Orc's `oalt` (Watchtower-like) and Undead's `usep` are
the only pure-defense towers in their races. The FR-015 candidate
inference accepts a tower placement *anywhere* far from the placer's
home and closer to an opponent's home — race-asymmetry doesn't change
the rule, only the candidate set.

**Rationale**. Filtering by the static names in `entity_names.json`
makes the catalog auditable in source control and lets the catalog
extend automatically when new towers are added to that file (e.g.,
custom-map content) — Principle III's "concrete code for the case in
front of us" without preempting a future where the towers list
changes.

**Alternatives considered**. (a) Hardcode the 10–15 ids in
`extract_events.py`. Rejected: brittle to renames in
`entity_names.json`. (b) Mark towers in `entity_names.json` itself
with a `category: "tower"` annotation. Rejected: changes the
mapping-file shape (cross-cuts feature 002's contract).

## R8. Tech-milestone entity-id catalog

**Decision**. The catalog is committed in `processor/EVENTS.md` and
covers exactly:

| Milestone label | Entity ids (one per race) |
|---|---|
| `tier2Hall` | `hkee` (Keep), `ostr` (Stronghold), `unp1` (Halls of the Dead), `etoa` (Tree of Ages) |
| `tier3Hall` | `hcas` (Castle), `ofrt` (Fortress), `unp2` (Black Citadel), `etoe` (Tree of Eternity) |
| `altar` | `halt`, `oalt`, `uaod` (Altar of Darkness), `eate` (Altar of Elders — actually `eaoe`) — finalized at impl |
| `keyTechBuilding` | per race, the canonical T2-gating production building (Lumber Mill `hlum`, War Mill `ogre`/`ogru`, Slaughterhouse `usep`, Ancient of Lore `eaom`) |
| `majorUpgradeStart` | the `production.upgrades.order[]` timestamp of the first started upgrade per player (hero-relevant or eco-relevant — we surface the first *one*; the rest are queryable directly from analyzer output) |

Final entity-id resolution happens in code against
`processor/entity_names.json`. The list above is the seed set; any
gaps surface as `unknown=true` per the existing entity-reference
shape and are still emitted as milestones with the raw id.

**Rationale**. A first-occurrence-per-player marker is a stable
narrative beat (LLM can say "12:30 — Player A reached Tier 2"). The
five labels cover the strategic phase changes a viewer cares about
without exploding into per-research-id noise.

**Alternatives considered**. (a) Surface every research start as a
milestone. Rejected: that's just `production.upgrades.order` again —
duplicating the analyzer's content into the events doc violates the
spirit of FR-008 (separate artifact, not a re-emission). (b) Drop
the `keyTechBuilding` label and rely on tier-2 as the only tech
beat. Rejected: races differ in what tier-2 unlocks; the key-tech
building is the more semantically loaded marker for several openers.

## R9. Hero teleport item-id catalog

**Decision**. v1 set:

| Item id | Item name | Notes |
|---|---|---|
| `stwp` | Scroll of Town Portal | The canonical TP. |
| `gtel` | Goblin Land Mines (NOT a TP) | EXCLUDED — flagged here as a known false-positive of name-based filtering. |
| `stel` | Staff of Teleportation | Teleports the holder + nearby allied units. |
| `mtel` | Mass Teleport Scroll | (If present in `entity_names.json`; otherwise omitted.) |

Final list is committed in `processor/EVENTS.md`. The detection
condition: a `0x10`/`0x12` ability-action whose `itemId` matches one
of the catalog ids, classified into the `item` category by the
existing analyzer, and emitted as an FR-019 event.

**Hero attribution**. We attribute the TP to the hero only when the
underlying replay action's selection-state implies a single hero was
selected at the time. When attribution is ambiguous, the event omits
the hero and notes the gap on the event's `attributionNote` field.

**Rationale**. TP usage is a high-narrative-density signal (retreats,
re-engagements). The catalog is explicit because there are
exactly 3–4 items in WC3:TFT that match the "instant-relocation"
semantics and they are race- and item-specific.

**Alternatives considered**. (a) Detect TPs by ability-effect
pattern (huge position delta in subsequent rightclicks). Rejected:
fragile and indirect. (b) Include "Boots of Speed" and similar
movement items. Rejected: not teleportation; would dilute the
narrative meaning.

## R10. Intensity-peak detection

**Decision**. Compute a per-second timeseries `s(t)` of total timed
actions across all players. Apply a 30-second rolling sum to produce
`R(t)`. Detect peaks where:

1. `R(t)` is a local maximum within a ±15 s neighborhood, AND
2. `R(t) > mean(R) + 2 × std(R)` over the entire game.

For per-team variants (FR-021 allows team-scoped peaks), apply the
same procedure to a team-restricted sum.

The chosen threshold of `2σ` keeps peaks rare and salient (typically
~5–15 per replay for a 30-minute game).

**Rationale**. The combination of "local maximum" and ">mean+2σ"
filters out routine APM noise and surfaces only the moments a
narrator would actually mention. The 30 s rolling window matches
real-fight cadences (bigger than skirmish micro, smaller than entire
phases).

**Alternatives considered**. (a) Find-peaks via
`scipy.signal.find_peaks`. Rejected: pulls in scipy as a third
dependency for one function. The hand-written 2-line rolling
local-maximum check is fine here (Principle III's YAGNI direction:
30 lines of clear code beat a transient one-line scipy call). (b)
Pure top-K peak picking with no σ threshold. Rejected: gives N peaks
for any replay regardless of whether the action curve is actually
bumpy; bad signal.

**Implementation note**. This is the one place in the events stage
where `pandas.Series.rolling(...).sum()` does work that would be
clumsy in raw lists. The `pandas` dependency is already justified by
R4's clustering needs; this is a free reuse.

## R11. Stable event-id derivation

**Decision**. Each event's `id` is computed as:

```python
import hashlib

canonical = "|".join([
    event.kind,
    str(event.start_time_ms),
    ",".join(sorted(str(p) for p in event.participants)),
    event.disambiguator,  # kind-specific; see EVENTS.md
])
event.id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

The 16-hex-character truncation gives 64 bits of collision resistance
— vastly more than needed for ~hundreds of events per replay.

**Per-kind disambiguator**. Most kinds need none (the `kind +
start_time + participants` triple is unique), but a few do:
- `productionStall` and `idlePeriod`: `disambiguator = str(end_time_ms)`
  (a player can have multiple idle periods of the same start time
  only via a clock collision, but include end time for safety).
- `buildingRebuild`: `disambiguator = entity_id + "@" + bucket_x + "," + bucket_y`.
- `techMilestone`: `disambiguator = milestone_label`.
- All other kinds: `disambiguator = ""`.

The disambiguator field set is committed in `processor/EVENTS.md`
per FR-009.

**Rationale**. SHA-256 is the standard hash for non-cryptographic
content addressing in Python (always available in stdlib, no
dependency). Truncating to 16 chars gives ids that are short enough
to read and cite ("see event `8a3f2b1c9d4e5f60`"). The canonical
string is built deterministically from in-spec fields, so the id is
stable across re-runs (FR-035) and across non-breaking spec
revisions.

**Alternatives considered**. (a) UUIDv4. Rejected: not deterministic.
(b) Sequential numeric ids. Rejected: unstable to re-orderings — see
the Q3 clarification rationale. (c) Full SHA-256 (64 hex chars).
Rejected: visual noise without security benefit at this scale.
