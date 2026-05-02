# Research: Visualizer Tabs (Feature 004)

Phase 0 of `/specs/004-visualizer-tabs/plan.md`. Resolves the open
questions raised by the Technical Context and the user's "consider
React" hint, and grounds them with concrete findings from the
existing codebase and committed fixtures.

## R1. Where do per-event timestamped minor-action records come from?

**Decision**: The **Processor** layer is extended in this feature
to walk the existing parser-output `events[]` stream, accumulate
the running in-game time from `timeIncrement`, and emit a
per-player `actions.timedActions` array of `{timeMs, category}`
records in `*.analysis.json`. The **Parser** is not changed.

**Rationale**:
- The parser already emits `events[]` containing every
  `commandBlock` issued by every player, with the originating
  `playerId` and an `actions[]` array of `{id, ...}` entries (each
  `id` is a w3gjs-classified action opcode). It also already emits
  per-player action totals — those totals are accumulated by
  walking the same event stream on the Node side.
- The Processor already iterates this same data shape to compute
  hero ability-learns, production entries, and resource transfers.
  Adding one more pass — or, more efficiently, folding the new
  extraction into the existing pass — is a localized change.
- Keeping the change in the Processor preserves Principle II
  (no Parser modifications, `w3gjs` remains the canonical, untouched
  source of replay decoding).
- The total count of `timedActions` per player must equal the
  existing `actions.totals` per category — this gives a free
  invariant for the new pytest assertion.

**Alternatives considered**:
- *Modify the Parser to denormalize per-player timed actions into
  parser-output JSON.* Rejected: adds Node-side classification
  logic that's already implicit in `w3gjs`, expands feature scope,
  and complicates Parser tests for no Visualizer-visible benefit
  the Processor route doesn't already provide.
- *Have the Visualizer walk parser-output `events[]` directly.*
  Rejected: violates Principle I (the Visualizer's only input is
  the Processor's analysis JSON; it does not consume parser
  output) and would force every Visualizer instance to redo the
  classification work.
- *Pre-bucket minor actions on the Processor side at a fixed bucket
  width* (option A from the spec clarification). Rejected by user
  choice (option B); pre-bucketing also caps zoom-in granularity at
  the chosen bucket width, defeating one of the Timelines tab's
  goals.

**w3gjs action-id classification reference** (used by the Processor
extractor): the categories already surfaced as totals in
`player.actions` — `assigngroup`, `rightclick`, `basic`,
`buildtrain`, `ability`, `item`, `select`, `removeunit`, `subgroup`,
`selecthotkey`, `esc` — are the same categories the new
`timedActions[].category` field uses. The Processor extractor maps
each `actions[].id` to its category using w3gjs's documented opcode
table; the Processor preserves the `id`-to-category mapping inline
to avoid a fragile cross-language dependency on w3gjs internals.

## R2. Should the Visualizer migrate to React for this feature?

**Decision**: **No.** The Visualizer remains static HTML + vanilla
ES2020+ JavaScript with no build step, no package manager, and no
framework. The user's "consider React" hint is acknowledged and
recorded as a future-trigger checklist below; none of the triggers
fire for this feature.

**Rationale**:
- Constitution Principle V (Incremental Frontend Evolution) requires
  a *concrete user-facing requirement that static HTML cannot meet*
  before a framework is adopted. The work in feature 004 — tab
  routing, three new aggregation render passes, an SVG histogram, a
  global zoom state — is straightforward in vanilla JS:
  - Tabs: one CSS class swap on the active tab + one show/hide on
    the active panel. No router, no state library.
  - Aggregations: pure functions over the loaded JSON. Three
    `renderProductionAggregation`, `renderHeroAggregation`,
    `renderTransferAggregation` functions, called from the Summary
    tab renderer.
  - Histogram: SVG `<rect>` per bucket, one row per player. Bucket
    counts are recomputed on zoom/resize from a memoized
    per-player events array. Manual DOM diff is unnecessary —
    `innerHTML` swap of the histogram subtree is fast at the bucket
    counts in scope (≤ 500 bars per row at any zoom level).
  - Global zoom: a single `{visibleStartMs, visibleEndMs}` field on
    the page state object, broadcast to every player row's
    re-render on change. No virtual-DOM diff library needed.
- File:// loading remains a hard requirement (FR-001 of feature
  003). React's typical tooling (Vite, CRA) produces ES-module
  bundles that hit CORS errors when loaded from `file://` in
  Chromium browsers. The framework path therefore *also* costs a
  build step that produces a `file://`-safe bundle.
- The current `visualizer.js` is 811 lines. The expected delta for
  this feature is +600–900 lines, putting the file in the
  ~1,400–1,700 line range. That's still a single file two engineers
  can hold in their head; the feature-003 plan flagged ~1,500 lines
  as a soft split point, and we'll exercise that split (still
  vanilla, still no build step, multiple `<script>` tags in load
  order) only if the implementation actually crosses it.

**Alternatives considered**:
- *Adopt React with Vite + a single-file build target* (e.g., `vite
  build --base=./` with inlined assets). Rejected: still a build
  step, still `npm install` in `visualizer/`, still a dependency
  graph the next maintainer has to learn — three Principle-V
  costs without a Principle-V justification.
- *Adopt a no-build option (htm + Preact via a single-file CDN
  copy)*. Rejected on two counts: copying a CDN script into the
  repo introduces a vendored dependency the constitution doesn't
  currently allow without amendment, and the same set of work
  (tabs, render passes, histogram) ships at lower cost without it.
- *Adopt a charting library* (d3, Chart.js). Rejected: same
  Principle-V cost, plus the histogram we need is one render pass
  with one zoom transform — a library is overkill for this scope.

**Future-trigger checklist (when "should we adopt a framework?"
would change to yes)**: Any one of the following, recorded in a
plan document, justifies a Principle V amendment proposal:
1. The visualizer needs to express **shared, deeply-nested mutable
   state** across more than ~3 unrelated tabs (e.g., a fifth tab
   that mutates a comparison-pinned set referenced by two other
   tabs).
2. The visualizer hits a **performance ceiling** that vanilla DOM
   updates can't clear — measured, not anticipated. For instance,
   if a future replay format produces ≥10x today's record counts
   and `innerHTML`-swap histogram updates take >50 ms.
3. The visualizer must support **accessibility** features (focus
   management, ARIA live regions, keyboard navigation across
   thousands of histogram bars) that hand-rolled DOM cannot
   reasonably deliver inside a small file.
4. The visualizer must adopt **server-side rendering** or a hosted
   page (which would also break the file:// guarantee — Principle
   V amendment + product-scope amendment both required).

For feature 004, none of (1)–(4) fire.

## R3. How is global zoom state implemented and shared across player rows?

**Decision**: A single `zoomState` object on the page-level state —
`{visibleStartMs, visibleEndMs}` — is the source of truth. Every
player's histogram row is a render function `(player, zoomState,
viewportPx) → SVG`. Zoom and pan input handlers mutate
`zoomState`, then dispatch a single re-render of all player rows.

**Rationale**:
- The spec requires **global** zoom (FR-012): all rows zoom and pan
  in sync. A single source of truth is the simplest implementation
  that meets that requirement.
- The Timelines tab is the only consumer of zoom state, and it's
  rebuilt from scratch on tab activation, so a module-scoped
  variable is sufficient — no cross-tab observer pattern, no event
  bus.
- Zoom resets to "full match visible" on file reload (FR-018). The
  `loadFile()` function clears `zoomState` to `{0, match.duration}`.

**Alternatives considered**:
- *Per-row zoom state synchronized via observer pattern.* Rejected:
  needless plumbing for a single-source-of-truth requirement.
- *URL hash / `localStorage` persistence of zoom state.* Rejected:
  out of scope (spec, "Out of Scope": no cross-session persistence).

## R4. Histogram bucket-width selection rule

**Decision**: At each render, compute target bucket count =
`floor(viewportContentPx / TARGET_BUCKET_PX)`, where
`TARGET_BUCKET_PX` is a tunable constant in the 8–12 px range.
Bucket width in milliseconds = `(visibleEndMs - visibleStartMs) /
target_bucket_count`, then snapped to a "nice" interval (1 s, 2 s,
5 s, 10 s, 15 s, 30 s, 1 m, 2 m, 5 m, 10 m, …) so bar boundaries
align with human-recognisable time units. The snap floor preserves
the at-most-`TARGET_BUCKET_PX`-wide bar guarantee (snapping rounds
*down* when zooming in, *up* when zooming out, both keeping bars
within the legibility band).

**Rationale**:
- Satisfies SC-006 (no sub-pixel bars, no bar wider than 25% of
  the row) by construction at any zoom level on a ≥1280 px
  viewport.
- "Nice" intervals keep tooltips readable ("00:30–00:45") and avoid
  wobbly axis labels that would change every zoom tick.
- `TARGET_BUCKET_PX` is a single tweakable constant, easy to revise
  in code review without restructuring.

**Alternatives considered**:
- *Fixed bucket count regardless of viewport.* Rejected: fails the
  resize requirement (FR-014).
- *Continuous (non-snapped) bucket widths.* Rejected: produces
  unreadable axis labels at zoom transitions.

## R5. How are aggregations grouped and ordered on the Summary tab?

**Decision**:
- **Production** (FR-006): group by `(player, entityId)`, sum
  count of completed entries. Ordering: grouped under section
  headers `Buildings / Units / Upgrades / Items` (preserving
  feature 003's section order); within each section, sort
  alphabetically by display name. The display name comes from the
  Processor's pre-attached label.
- **Heroes** (FR-007): group by `(player, heroId)`. For each hero,
  the visible content is `${displayName} — Level ${finalLevel}: A
  → B (L1) → A (L2) → ...` where the arrow chain preserves the
  `abilityOrder` array's order from the analysis JSON. Level
  parenthesis is shown on every learn (consistent with the
  feature description's example) — the spec assumption that allows
  omitting it on single-learn abilities is dropped here for visual
  consistency.
- **Resource transfers** (FR-008): group by `(player, recipientId,
  resource)` where `resource ∈ {gold, lumber}`. For each group,
  show `recipientName: ${total} ${resource} (${count} transfers)`.
  Ordering: by total amount descending (the largest movement is
  the most informative).

**Rationale**: These are the natural groupings implied by the
spec's example output and the analysis JSON's existing structure.
The choice to show level parens on every hero ability is a small
deviation from the spec's permissive "MAY omit on single learn"
assumption — chosen here for visual consistency across heroes
(every entry has the same shape).

**Alternatives considered**:
- *Group transfers by recipient only, summing gold and lumber into
  one row.* Rejected: gold and lumber are separately interesting
  resources in WC3 strategy; collapsing loses information.
- *Sort production by chronological first-occurrence.* Rejected:
  the Summary tab deliberately drops the time axis; chronological
  sort would be confusing without timestamps to anchor it.

## R6. Where do the Analysis and Map stub tabs live in the rendered page?

**Decision**: Each stub tab is a single `<section>` registered in
the same tab-routing table as Summary and Timelines, with a fixed
inner template — a heading, two short explanatory paragraphs, and
no interactive controls. The template is rendered once on tab
activation and is identical regardless of the loaded analysis JSON
(stubs do not read replay data).

**Rationale**: Keeps the tab-routing surface uniform (every tab is
a render function over `(state)`); makes it obvious to any future
contributor where to "fill in" each stub when its real feature
lands.

**Alternatives considered**:
- *Render stub content via a `<template>` tag in HTML rather than a
  JS render function.* Rejected for inconsistency with the other
  tabs and for the marginal value (we'd save ~10 lines).

## R7. Visualizer file split (single-file vs. multi-file)

**Decision**: Start single-file (`visualizer.js`). If implementation
crosses ~1,500 lines, split into multiple plain `<script>` files
loaded in dependency order via separate `<script src="...">` tags
(no `type="module"`). Likely split, if needed:
`state.js` → `tabs.js` → `summary.js` → `timelines.js` →
`stubs.js` → `main.js`. The split is mechanical (top-level
`function` declarations remain global; no import / export
syntax) so it preserves the file:// loading guarantee.

**Rationale**: Feature 003's plan already flagged ~1,500 lines as
the soft split point. Vanilla file-split with global functions
loaded in script-tag order has the lowest cognitive cost and zero
new constraints (no bundler, no module resolution, no build).

**Alternatives considered**:
- *Adopt ES modules*. Rejected: `<script type="module">` from
  `file://` triggers CORS errors in Chromium-family browsers.
- *Inline everything into one file no matter the size*. Rejected
  prophylactically: a 1,700-line file is on the boundary of
  reviewability; pre-deciding the split rule keeps the
  implementation honest.

---

All `[NEEDS CLARIFICATION]` markers from the spec are resolved.
Phase 0 complete.
