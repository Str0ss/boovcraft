# Phase 0 — Research: Replay Visualizer

**Feature**: 003 Replay Visualizer
**Branch**: `003-replay-visualizer`
**Status**: complete — no NEEDS CLARIFICATION items remain.

## Scope

This document records the design questions raised during planning and
the decisions taken before Phase 1 (data model + contracts). Each entry
follows: **Decision → Rationale → Alternatives considered**.

Items marked `[INFORMS-PHASE-1]` produce concrete artifacts in
`data-model.md`, `contracts/`, or `quickstart.md`.

---

## R1 — Loading a JSON file from disk in a `file://`-served page

**Decision**: Use a `<input type="file" accept=".json,application/json">`
control plus `FileReader.readAsText()`. Drag-and-drop (US3) reuses
`DataTransfer.files` and feeds the same `FileReader` path.

**Rationale**: This works in every modern browser when the page itself
is loaded from `file://`. No server, no permissions prompt, no API
divergence. `FileReader` is in every browser since 2010. The newer
`File.text()` Promise method (~Chrome 76) would be slightly cleaner, but
the older callback API is universal and we have no reason to forfeit
that compatibility for one fewer line of code.

**Alternatives considered**:
- **`fetch('./local-file')` from `file://`** — rejected. Chromium-family
  browsers refuse `fetch` against `file://` with a CORS error, and
  Firefox refuses for resources outside the document's directory. The
  picker pattern bypasses the security model entirely because the user
  selects the file.
- **File System Access API (`window.showOpenFilePicker`)** — rejected.
  Not available in Firefox or Safari at present, and the secure-context
  requirement makes `file://` behavior brittle. The classic input
  element is universal.

`[INFORMS-PHASE-1]` — described in `quickstart.md` and the
`contracts/ui-contract.md` "Loading" section.

---

## R2 — JavaScript file layout: single file vs. ES modules

**Decision**: One concatenated `visualizer/visualizer.js`, loaded by
`<script src="visualizer.js"></script>` (no `type="module"`).

**Rationale**:
- ES modules loaded from `file://` trigger CORS errors in
  Chromium-family browsers ("Origin null is not allowed by
  Access-Control-Allow-Origin"). They work in Firefox and Safari, but
  the spec requires the page to load by double-click in *any* modern
  evergreen browser (FR-001, target platform).
- Principle III rules out preemptive modular structure when the whole
  layer is one page rendering one document.
- A single file is also easier to inspect, diff, and grep — relevant
  because frontend correctness is eyeball-reviewed, not auto-tested.

**Alternatives considered**:
- **`type="module"` ES modules** — rejected per the Chromium `file://`
  CORS issue above. Adopting modules would force users to start a local
  server, which violates FR-001 and the no-server constraint.
- **Multiple classic scripts loaded in order** — acceptable as a future
  split if `visualizer.js` exceeds ~1,500 lines. Not adopted now.

`[INFORMS-PHASE-1]` — declared in the project structure and the
`contracts/ui-contract.md`.

---

## R3 — Timeline rendering technique

**Decision**: Inline SVG, one `<svg>` per player. Markers are SVG shapes
(`<circle>`, `<rect>`, `<polygon>`) positioned by `x = (timeMs /
durationMs) * width`, grouped by event category onto distinct vertical
rows, given `<title>` children for hover tooltips and `tabindex="0"`
for keyboard focus.

**Rationale**:
- SVG markers are native DOM nodes — focusable, hover-reachable, easy to
  give a `<title>` tooltip without a custom tooltip layer (which would
  bleed into framework-shaped territory).
- No external library is needed for what is fundamentally a series of
  positioned shapes plus an axis. This honors Principles III and V.
- Categories are visually distinguished by both row position and shape:
  buildings = squares (top row), units = circles (second row), upgrades
  = upward triangles (third), items = downward triangles (fourth),
  hero ability-ups = stars (fifth). Player accent color tinges all
  markers; unknown-flagged events are stroked instead of filled, with
  an `[?]` glyph appended in the tooltip.
- The legible-density requirement (acceptance scenario US2-4) is
  addressed by the per-category row split: even a busy player has at
  most one row's worth of markers per category, not all stacked on a
  single line.

**Alternatives considered**:
- **`<canvas>` 2D drawing** — rejected. Canvas pixels are not
  individually focusable or hoverable; we would have to implement a hit
  test, a tooltip layer, and keyboard navigation manually. SVG
  delivers all three for free.
- **Pure-HTML absolute-positioned `<div>`s** — rejected. Comparable to
  SVG but with weaker semantics (no native shape variety, harder to
  size markers consistent with a logical axis). The SVG `viewBox`
  affords clean axis math.
- **Charting library (d3, chart.js, observable plot)** — rejected on
  Principle V; we do not need a chart, we need positioned event marks.

`[INFORMS-PHASE-1]` — described in `data-model.md §timeline-row` and
`contracts/ui-contract.md §timeline`.

---

## R4 — Time formatting (millisecond integers → user-facing strings)

**Decision**: Render times in `m:ss` for matches under 1 hour and
`h:mm:ss` for matches at or over 1 hour. Use a single helper
`formatTimeMs(ms, totalMs)` that picks the format based on `totalMs`,
applied uniformly to every timestamp the user sees.

**Rationale**:
- The Processor spec leaves presentation entirely to the visualizer
  (`processor/DATA.md` §Scope exclusions: "Preformatted display strings
  ... Visualizer owns presentation"), so this is the right layer to
  decide.
- The 1-hour threshold gives `m:ss` to all base_2-class matches
  (~16 minutes) and `h:mm:ss` to base_1-class matches (~88 minutes),
  matching how players verbally refer to times.
- A single helper means timestamps are uniform across the match header,
  build order, hero ability-learn list, resource transfers, chat, and
  timeline tooltips.

**Alternatives considered**:
- **Always `mm:ss`** — rejected. base_1 has events past 60 minutes;
  `mm:ss = 88:14` is awkward.
- **Pad with leading zero on minutes for short matches** (e.g. `04:32`)
  — rejected. WC3 timing convention is `4:32`; players read it that way.
- **Decimal minutes** (`32.4 min`) — rejected. Builds and timings are
  spoken as `m:ss` in the WC3 community.

`[INFORMS-PHASE-1]` — formal definition in `contracts/ui-contract.md`.

---

## R5 — Are the analysis JSONs themselves committed fixtures?

**Decision**: No. The committed fixtures are the Parser outputs
(`sample_replays/base_*.w3g.json`, already tracked). The
`*.analysis.json` files are `.gitignore`d and regenerated locally by
`python processor/analyze.py sample_replays/base_*.w3g.json` before
running the visualizer's manual walkthrough.

The spec's phrase "the two committed fixtures" (FR-012, SC-005, SC-006)
refers to the two committed *replays + parser outputs*, whose
`*.analysis.json` projection through the Processor is deterministic
(modulo `diagnostics.parserParseTimeMs`). For the visualizer, this is
equivalent: regenerating produces the same render input every time.

**Rationale**:
- Committing analysis JSONs would tie repository state to the analyzer
  version, forcing a regen-and-recommit on every analyzer change.
- The Processor layer is already fixture-tested (feature 002, 53
  passing pytest cases) so the visualizer's input is already covered.
- The visualizer's correctness is eyeball-checked; reviewers regenerate
  before review.

**Alternatives considered**:
- **Commit the analysis JSONs** — rejected. Adds churn (~390 KB of JSON
  on every analyzer change) for no test benefit.
- **Update the spec to refer to "Processor outputs of committed
  fixtures"** — partially adopted in `quickstart.md`, but FR-012's
  current phrasing is accurate enough for the user-facing spec since
  *the Visualizer's view* is that the analysis JSON exists on disk
  when it is rendered, regardless of whether it is git-tracked.

`[INFORMS-PHASE-1]` — `quickstart.md` covers regeneration before review.

---

## R6 — Drag-and-drop (US3 / FR-002 secondary path)

**Decision**: Whole-document drag-and-drop. The page binds `dragover`
(prevent default, set `dropEffect = "copy"`, show overlay), `dragleave`
(hide overlay), and `drop` (read `event.dataTransfer.files[0]`,
re-enter the same load path the picker uses). A dashed full-viewport
overlay appears while a drag is in progress.

**Rationale**:
- The picker covers 100% of load paths, so drop is purely
  quality-of-life (P3). Restricting it to a small drop-target panel
  reduces discoverability without simplifying anything; whole-document
  drop is the modern convention.
- All validation and error messages are shared with the picker path —
  US3-3 ("a non-JSON file dropped") reuses the same "couldn't read this
  file as JSON" / "doesn't look like a replay analysis" copy.

**Alternatives considered**:
- **A small dedicated drop zone** — rejected; adds UI weight, hides
  affordance until the user finds it.
- **No drop, picker only** — would technically meet FR-002 (drop is
  optional), but US3 is explicitly a P3 user story; including drop
  satisfies it for the same architectural cost.

`[INFORMS-PHASE-1]` — `contracts/ui-contract.md §loading`.

---

## R7 — Empty-state copy

**Decision**:
- No chat: **"No in-game chat in this replay."**
- No observers: **"No observers."**
- No resource transfers (per player): **"No allied resource
  transfers."**
- No heroes for a player: **"No heroes used."**

Each empty state renders inside the section it would otherwise fill,
with a muted color and italic style, so the section is visibly present
(per the spec's edge case requirement that empty sections are
*rendered as empty states*, not omitted).

**Rationale**:
- Direct, plain English. No emoji, no "Oops!" / "Looks like ...".
- Matches the spec's edge cases ("zero chat", "zero observers", "zero
  resource transfers", "zero heroes") explicitly.

**Alternatives considered**: localized variants (out of scope per
Assumptions: English-only); icon-only empty states (less clear,
no upside).

`[INFORMS-PHASE-1]` — `contracts/ui-contract.md §empty-states`.

---

## R8 — Race code → race full-name + race accent

**Decision**: Inline a small const lookup in `visualizer.js`:
`{ H: "Human", O: "Orc", U: "Undead", N: "Night Elf", R: "Random" }`.
Display `raceDetected` (full name) prominently in the player panel
header; if `race === "R"` AND `raceDetected !== "R"`, also display the
chosen race as "(Random → Detected)".

**Rationale**:
- Five entries; not worth fetching a separate JSON. Inlining respects
  Principle III.
- The Processor's data-model exposes both `race` (lobby choice) and
  `raceDetected` (inferred when chose Random); FR-005 calls for both.

**Alternatives considered**: extending `entity_names.json` to cover
race codes — rejected (cross-purpose), and would violate FR-008 if it
required a separate fetch.

`[INFORMS-PHASE-1]` — `contracts/ui-contract.md §player-panel`.

---

## R9 — Unknown-entity visual treatment

**Decision**: Italic display label + a `[?]` badge appended after the
name + a `title` attribute on the element containing the raw 4-char id
(or `"UNKN"`). The same treatment is applied wherever the entity
appears: player hero list, build-order list, hero ability-order list,
timeline marker (stroked-not-filled, with `[?]` in the tooltip).

**Rationale**:
- Italic + `[?]` is unambiguous to a human reader yet visually
  unobtrusive. The `title` attribute is keyboard-reachable and
  screen-reader accessible.
- The marker style change (stroke-only) lets the timeline render
  unknown entries without crowding any new visual axis.
- `unknown: true` and the `"UNKN"` sentinel id are handled identically
  (FR-007, edge case "A player with a hero entry whose id is the `UNKN`
  sentinel").

**Alternatives considered**: red text, danger badge — rejected;
overstates the severity. Hidden behind a toggle — rejected; the spec
requires unknowns to be visible.

`[INFORMS-PHASE-1]` — `contracts/ui-contract.md §unknown-marker`.

---

## R10 — Validation: what counts as "looks like a replay analysis"?

**Decision**: After `JSON.parse`, run a structural sanity check:
the parsed value must be an object with the seven required top-level
keys (`match`, `settings`, `map`, `players`, `observers`, `chat`,
`diagnostics`); `match` must be an object; `players` must be an
array; `observers` and `chat` must be arrays. Type-mismatches at this
top level abort the render with the FR-004 error message ("This file
doesn't look like a replay analysis"). Inside the structures, the
visualizer trusts the Processor's contract — no per-field re-validation,
no defensive type-coercion.

**Rationale**:
- The Processor's contract guarantees the inner shape; doubling the
  validation in the Visualizer would violate Principle III.
- The seven-key check rules out arbitrary other JSON files (a
  `package.json`, a parser-output `*.w3g.json`, a `tasks.md` rendered
  to JSON, etc.) — those will fail this check at the door.
- Loading a *parser-output* `*.w3g.json` by mistake is a foreseeable
  user error. The parser-output document has different top-level keys
  (`players` is an array but the analyzer keys `diagnostics` /
  `observers` / etc. differ); the seven-key intersection check will
  reject it cleanly with the FR-004 error.

**Alternatives considered**:
- **Validate the full schema (every nested type)** — rejected;
  duplicates the Processor's contract, slows the load path, and
  introduces a parallel schema definition that drifts.
- **No validation, render directly** — rejected; the spec's FR-004
  explicitly requires a clear error rather than a partial broken render.

`[INFORMS-PHASE-1]` — `contracts/input-contract.md §validation`.

---

## R11 — Performance posture for ~20 MB analysis JSONs

**Decision**: Measure first, optimize on evidence. Initial render
strategy:
- Parse JSON synchronously after `FileReader` resolves
  (`JSON.parse(text)` is ~200 MB/s on commodity hardware; a 20 MB JSON
  parses in ~100 ms).
- Render player panels by appending pre-built HTML strings in a single
  `outerHTML = ...` per panel (one DOM mutation per player).
- Render timelines as a single SVG per player, building markers as a
  single template-literal SVG string. Avoid one-marker-at-a-time
  `appendChild` loops.
- Defer no work (no virtualization, no paginated rendering). 8 player
  panels × ~hundreds of markers = ~thousands of SVG nodes total — well
  under what desktop browsers handle without paint pauses.

The 3-second budget (SC-002) is comfortable; if benchmarks during
implementation surface a hot spot (e.g., one player with thousands of
markers), the fix is local (e.g., lower the marker DOM count for that
player) and does not require an architectural change.

**Rationale**:
- Premature use of `requestIdleCallback`, web workers, or chunked
  rendering would violate Principle III.
- The DATA.md scope notes that the analyzer does not emit raw event
  streams — so the input set is bounded by per-player aggregated
  entries (build orders + hero abilities), not by raw replay action
  count. base_1 is the upper edge.

**Alternatives considered**: incremental rendering, `requestIdleCallback`,
worker-thread parsing — all rejected up front; revisit only on
measured budget violations.

`[INFORMS-PHASE-1]` — noted in `quickstart.md §performance-spotcheck`.

---

## R12 — Accessibility floor for v1

**Decision**:
- Semantic HTML throughout (`<main>`, `<header>`, `<section>`, `<nav>`
  where appropriate, `<table>` for tabular data).
- Every interactive control is keyboard-reachable (tab order, focus
  outlines preserved).
- Timeline markers are `tabindex="0"` and have `<title>` children that
  surface on hover AND focus (FR-006).
- Color is not the sole signal: race shows the full name; unknown
  flags use both italic+badge AND tooltip; timeline categories use both
  shape AND row position (not color alone).

Out of scope per spec Out-of-Scope: dark mode, high-contrast mode,
keyboard shortcuts beyond tab order, ARIA live regions, screen-reader
narration of the timeline visualization.

**Rationale**: The spec's Out-of-Scope list is explicit. The above
floor is what falls out of using semantic HTML correctly.

**Alternatives considered**: a fuller WCAG AA pass — rejected as out
of scope for v1; can be a future feature.

`[INFORMS-PHASE-1]` — woven through `contracts/ui-contract.md`.

---

## NEEDS CLARIFICATION

None. All Phase 0 questions are resolved. Proceeding to Phase 1.
