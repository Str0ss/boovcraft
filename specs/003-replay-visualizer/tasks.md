---

description: "Task list for feature 003 — Replay Visualizer"
---

# Tasks: Replay Visualizer

**Input**: Design documents from `/home/stross/repos/boovcraft/specs/003-replay-visualizer/`
**Prerequisites**: plan.md, spec.md (required); research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Per spec ("No automated frontend tests in v1") and per Constitution Principle IV scope (parser/processor only) — no automated test tasks are generated. Acceptance is the manual walkthrough in `quickstart.md`.

**Organization**: Tasks are grouped by user story so each story can be independently completed, manually validated, and demoed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase (different files, no shared dependencies)
- **[Story]**: User-story label (US1, US2, US3) — applies to story-phase tasks only

## Path Conventions

This project is multi-layer; the Visualizer layer is added under a new
top-level directory `visualizer/`. All file paths in this document are
absolute from the repo root.

```text
visualizer/
├── index.html
├── styles.css
├── visualizer.js
└── DATA.md
```

Almost every implementation task edits one of three shared files
(`visualizer/visualizer.js`, `visualizer/styles.css`,
`visualizer/index.html`). Because tasks within a story typically share
those files, [P] markers are rare in this feature; they appear only
where two tasks genuinely write to different files with no ordering
dependency.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the empty `visualizer/` directory and four skeleton files so subsequent tasks have a clear write target.

- [X] T001 Create directory `visualizer/` at the repository root.
- [X] T002 [P] Create `visualizer/index.html` with a minimal HTML5 skeleton: `<!doctype html>`, `<html lang="en">`, `<head>` containing `<meta charset="utf-8">`, `<meta name="viewport" content="width=1280">`, `<title>Boovcraft Replay Visualizer</title>`, and `<link rel="stylesheet" href="styles.css">`; `<body>` containing a single empty `<main id="app"></main>` mount point and `<script src="visualizer.js" defer></script>` at end of body. No content beyond the mount point yet.
- [X] T003 [P] Create `visualizer/styles.css` with empty content (a placeholder one-line comment is acceptable).
- [X] T004 [P] Create `visualizer/visualizer.js` with a single top-level `'use strict';` line and an empty IIFE wrapper: `(() => { /* visualizer entry point */ })();`. No behavior yet.
- [X] T005 [P] Create `visualizer/DATA.md` with a one-paragraph orientation: layer position (third / final), input contract pointer to `processor/DATA.md`, how to open the page (double-click `index.html`), and what file to pick (`*.analysis.json`).

**Checkpoint**: Opening `visualizer/index.html` in a browser shows a blank page with no console errors. Setup is complete.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire the load → parse → validate → render pipeline that every user story depends on, plus the cross-cutting helpers (time formatting, unknown-entity rendering, mount-point lifecycle). Everything that needs to be in place before US1 can render any report at all.

**⚠️ CRITICAL**: No user-story phase can begin until this phase is complete.

- [X] T006 In `visualizer/visualizer.js`, add the global state holder: a single module-scope variable `currentAnalysis = null`, plus three references to DOM mount points obtained on `DOMContentLoaded` (`appEl`, populated lazily inside the IIFE).
- [X] T007 In `visualizer/index.html`, replace the empty `<main id="app">` with the landing-state markup defined in `contracts/ui-contract.md §Landing state`: a header (`<h1>` page title), a paragraph instruction, an `<input type="file" id="picker" accept=".json,application/json">` with a visible label, and an empty `<div id="report" hidden></div>` and `<div id="error" role="alert" hidden></div>` mount points. (This task touches `index.html` only.)
- [X] T008 In `visualizer/styles.css`, add baseline styles per `contracts/ui-contract.md §Layout`: page reset, system font stack, container max-width, landing-state spacing, error-state styling (border, muted color), and `[hidden] { display: none; }`. Desktop-first, ≥1280 px target. (This task touches `styles.css` only.)
- [X] T009 In `visualizer/visualizer.js`, implement `formatTimeMs(ms, totalMs)` per `research.md §R4` and `contracts/ui-contract.md §Time formatting`: `m:ss` when `totalMs < 3_600_000`, else `h:mm:ss`. Pure function, no DOM.
- [X] T010 In `visualizer/visualizer.js`, implement `validateAnalysisShape(parsed)` per `contracts/input-contract.md §What the visualizer validates`: checks parsed is a plain object (not array, not null), has all seven required top-level keys, `match` is an object, `players`/`observers`/`chat` are arrays. Returns `{ ok: true }` or `{ ok: false, message: <FR-004 string> }`. Pure function, no DOM.
- [X] T011 In `visualizer/visualizer.js`, implement `loadFile(file)` (the picker/drop entry point) using `FileReader.readAsText`. On success: `JSON.parse` (catch SyntaxError → "Couldn't parse this file as JSON."), then `validateAnalysisShape` (on failure → "This file doesn't look like a replay analysis."), then call `renderReport(parsed)`. On any failure path, call `showError(message)` and ensure no partial render persists. Bind to `#picker` `change` event.
- [X] T012 In `visualizer/visualizer.js`, implement `showError(message)` and `clearError()`: toggle `#error` visibility, set/clear its text content (use `textContent`, never `innerHTML`), hide `#report`. Implement `clearReport()`: empty `#report` (`replaceChildren()`) so loading a new file fully replaces the prior render (FR-009).
- [X] T013 In `visualizer/visualizer.js`, implement `renderReport(analysis)`: clear errors, set `currentAnalysis = analysis`, build the report DOM tree off-document, then mount it into `#report` in a single `replaceChildren()` call. Reveal `#report`. The function delegates to per-section renderers (`renderMatchHeader`, `renderTeams`, `renderChat`, `renderObservers`) implemented in later phases — at this point, declare them as TODO stubs that emit a single `<p>` with the section name.
- [X] T014 In `visualizer/visualizer.js`, implement `entityLabelEl(entity, kind = 'span')`: returns a DOM element of the chosen tag whose textContent is `entity.name`, with `class="entity entity--unknown"` and a `title` attribute `Unknown entity id: ${entity.id}` plus an appended `[?]` glyph child when `entity.unknown === true`; otherwise `class="entity"` and the resolved name only. This is the central helper for `contracts/ui-contract.md §unknown-marker`. Pure DOM construction, no external state.
- [X] T015 In `visualizer/styles.css`, add `.entity--unknown` styling: italic, muted color, `[?]` glyph styled as a small inline badge. Document in a one-line comment that this applies wherever an entity is named.

**Checkpoint**: Opening `index.html`, picking a valid analysis JSON shows section-name placeholders inside `#report`. Picking an invalid file (a `.txt`, a `package.json`, a malformed `.json`) shows the appropriate FR-004 error and no partial report. Foundational pipeline is ready.

---

## Phase 3: User Story 1 — Read A Complete Match Report (Priority: P1) 🎯 MVP

**Goal**: With a single file picked, the user sees a full text-form match report — match header, per-team player panels with build orders, hero progression, resource transfers, chat, observers — for both committed fixtures.

**Independent Test**: Per `quickstart.md §Smoke-test`: open the page, pick `sample_replays/base_1.w3g.analysis.json`, walk the SC-004 review checklist; repeat for `base_2`; pick `base_2` after `base_1` and verify replacement (FR-009).

### Implementation for User Story 1

- [X] T016 [US1] In `visualizer/visualizer.js`, implement `renderMatchHeader(analysis, durationMs)` per `contracts/ui-contract.md §match-header` and `data-model.md §MatchHeader`: outcome ("Team N" or "Undetermined"), version + build (`"v{version} (build {buildNumber})"`), gameType + matchup, map filename (with full path in `title`), duration (via `formatTimeMs`). Append a small definition list with low-prominence lobby settings (gameName, creator, speed, observerMode, fixedTeams).
- [X] T017 [US1] In `visualizer/visualizer.js`, implement `groupPlayersByTeam(players)` per `data-model.md §TeamGrouping`: returns a `Map<teamId, players[]>` with ascending teamId iteration, slot-order within each team. Pure function.
- [X] T018 [US1] In `visualizer/visualizer.js`, implement `renderTeams(analysis)`: iterates `groupPlayersByTeam(analysis.players)`, emits a team header for each group ("Team N — winners" if every player in the group has `isWinner === true`, else "Team N"), then calls `renderPlayerPanel(player, durationMs, isWinningTeam)` for each player.
- [X] T019 [US1] In `visualizer/visualizer.js`, implement `renderPlayerPanel(player, durationMs)` shell: panel container with `style="border-left-color: ${player.color}"`, header line containing name + race label + APM + winner badge (when `player.isWinner`). Race label per `research.md §R8`: full name from `RACE_NAMES = { H: "Human", O: "Orc", U: "Undead", N: "Night Elf", R: "Random" }`; if `race === "R"` and `raceDetected !== "R"`, append `" → ${RACE_NAMES[raceDetected]}"`. Winner badge is a small `<span class="badge--winner">Winner</span>`.
- [X] T020 [US1] In `visualizer/visualizer.js`, implement `renderActionTotals(player)` and `renderGroupHotkeys(player)` as compact sub-blocks of the player panel (both rendered inline in `renderPlayerPanel`). Action-totals: a flat key/value list of `player.actions.totals`. Group hotkeys: a small two-column table covering keys `0`–`9` with `assigned` / `used` per row.
- [X] T021 [US1] In `visualizer/visualizer.js`, implement `renderProductionSection(production, durationMs)` per `contracts/ui-contract.md §player-panel`: emits four sub-sections (Buildings, Units, Upgrades, Items) each a chronological `<ol>` of `entityLabelEl(entry) + " — " + formatTimeMs(entry.timeMs, durationMs)`. Empty array → empty-state element ("No buildings recorded.", etc.). Wire into `renderPlayerPanel`.
- [X] T022 [US1] In `visualizer/visualizer.js`, implement `renderHeroSection(heroes, durationMs)` per `data-model.md §HeroSection`: per hero, header `entityLabelEl(hero, 'h4') + " — Level " + hero.level`, then `<ol>` of ability rows formatted as `formatTimeMs(ability.timeMs, durationMs) + " — " + entityLabelEl(ability) + " (L" + ability.level + ")"`. Empty heroes array → empty-state ("No heroes used."). Wire into `renderPlayerPanel`.
- [X] T023 [US1] In `visualizer/visualizer.js`, implement `renderTransferSection(transfers, durationMs)` per `data-model.md §TransferSection`: `<ul>` of rows formatted `formatTimeMs(timeMs, durationMs) + " → " + toPlayerName + ": " + (gold ? "+" + gold + " gold" : "") + (lumber ? ", +" + lumber + " lumber" : "")` (skip the zero side gracefully). Empty → "No allied resource transfers." Wire into `renderPlayerPanel`.
- [X] T024 [US1] In `visualizer/visualizer.js`, implement `renderChat(chat, durationMs)` per `contracts/ui-contract.md §chat`: top-level chronological list. Each row: sender + channel label + time + text. Use `textContent` for the text field (never `innerHTML`). Empty array → "No in-game chat in this replay."
- [X] T025 [US1] In `visualizer/visualizer.js`, implement `renderObservers(observers)` per `contracts/ui-contract.md §observers`: comma-separated names, or "No observers." when empty.
- [X] T026 [US1] In `visualizer/visualizer.js`, replace the section-name stubs in `renderReport` (from T013) with calls to the real renderers from T016, T018, T024, T025 in this top-to-bottom order: match header → teams → chat → observers. Pass `analysis.match.durationMs` down to renderers that need it.
- [X] T027 [US1] In `visualizer/styles.css`, style the report layout: match-header block, team headers, player-panel grid (4 columns at ≥1280 px, fewer columns at narrower viewports via plain `flex-wrap` or `auto-fit` grid — no media-query gymnastics), player-panel content (header line, action totals, group hotkeys, build-order subsections, hero block, transfers, empty-state styling). Channel labels for chat (`Team`, `Observer`, `Private`) get distinct text-and-tint styling so channel is readable both as a label and visually.
- [ ] T028 [US1] Manually verify FR-009 (reload replacement): with `base_1` rendered, pick `base_2`; confirm no leftover panels, names, hero blocks, or chat from `base_1` remain. If `clearReport` from T012 leaves stragglers, fix at the source — do NOT add a `setTimeout`-based workaround.

**Checkpoint**: User Story 1 ships. Both fixtures render cleanly through the SC-004 review checklist. The visualizer is usable as a text-form match report. The MVP is shippable here.

---

## Phase 4: User Story 2 — Per-Player Timeline (Priority: P2)

**Goal**: Each player panel gains a visual SVG timeline whose horizontal axis is the match duration and whose markers cover the union of build-order entries (buildings, units, upgrades, items) and hero ability-learn entries. Markers are interactive (hover and keyboard focus reveal name + time).

**Independent Test**: Per `quickstart.md §Manual SC-005 timeline-completeness spot-check`: pick a player, count timestamped entries in the JSON, count markers across the five timeline rows, confirm equal. Hover and Tab through markers to verify tooltips on both interactions.

### Implementation for User Story 2

- [X] T029 [US2] In `visualizer/visualizer.js`, implement `buildTimelineEvents(player)` per `data-model.md §TimelineView §Construction`: union the four production-order arrays (each entry tagged with its category) and the per-hero `abilityOrder` arrays (tagged `category="ability"`, with `heroLabel` and `abilityOrdinal` fields), then sort by ascending `timeMs`. Pure function.
- [X] T030 [US2] In `visualizer/visualizer.js`, implement `renderTimeline(player, durationMs)` returning a single `<svg>` element. Compute `viewBox` based on a fixed pixel size (e.g., width 720, height 200 — 5 rows × 32 px + 40 px axis area). Render an axis line at the bottom of the SVG, four labelled tick marks at evenly-spaced match-time intervals (formatted via `formatTimeMs`), and the five fixed category rows top-to-bottom (`building`, `unit`, `upgrade`, `item`, `ability`). Wire into `renderPlayerPanel`.
- [X] T031 [US2] In `visualizer/visualizer.js`, implement `renderTimelineMarker(event, player, durationMs, layout)` per `data-model.md §TimelineView §Marker shape`: returns an SVG element of the right shape per category (`<rect>` square, `<circle>`, two `<polygon>` triangles, one `<polygon>` star), positioned at `x = leftMargin + (timeMs / durationMs) * axisWidth`, `y = rowOffset[category]`. Filled with `player.color` when `event.isUnknown === false`, stroke-only neutral grey when `event.isUnknown === true`. Each marker carries `tabindex="0"` and a `<title>` child with the tooltip text per `contracts/ui-contract.md §timeline §Marker tooltip`. Iterate `buildTimelineEvents(player)` inside `renderTimeline` to emit one marker per event.
- [X] T032 [US2] In `visualizer/styles.css`, add timeline styling: SVG container sizing, axis stroke, tick text, focus outlines on markers (visible focus ring for keyboard users), and unknown-marker stroke styling. Markers MUST be visually distinguishable by both shape and row, so color-blind users still read the categories — explicit reminder in a one-line CSS comment.
- [ ] T033 [US2] Manually verify with `base_1`'s busiest player and `base_2`'s busiest player that markers are legibly spaced (no unreadable clumps at the panel's ≥1280 px column width), per spec acceptance scenario US2-4. If clumps appear, accept them in v1 as long as tooltips are still reachable; do NOT add density reduction or zoom in v1.

**Checkpoint**: User Story 2 ships. Both fixtures' player panels show a complete timeline. Hover and Tab navigation reveal each event. The visualizer becomes an analytic tool, not just a text dump.

---

## Phase 5: User Story 3 — Drag-And-Drop (Priority: P3)

**Goal**: A user with the analysis JSON in their file manager can drag it onto the visualizer page; the same load path the picker uses fires.

**Independent Test**: Per `spec.md §US3 Independent Test`: drag `sample_replays/base_1.w3g.analysis.json` from a file-manager window onto the visualizer; confirm it renders the same report the picker would. Also: drop a non-JSON file and confirm the FR-004 error path.

### Implementation for User Story 3

- [X] T034 [US3] In `visualizer/index.html`, add an empty `<div id="dropzone" hidden></div>` directly inside `<body>` (sibling of `<main>`), with a child element containing the cue text "Drop to load".
- [X] T035 [US3] In `visualizer/visualizer.js`, bind whole-document drag listeners per `research.md §R6` and `contracts/ui-contract.md §Loading`: `dragover` (preventDefault, set `dropEffect = "copy"`, reveal `#dropzone`), `dragleave` (hide `#dropzone` only when leaving the document), `drop` (preventDefault, hide `#dropzone`, take `event.dataTransfer.files[0]` and feed it to `loadFile` from T011). Reject drops with no files or with multiple files via the FR-004 message "Please select a single .json file."
- [X] T036 [US3] In `visualizer/styles.css`, style `#dropzone`: full-viewport overlay with dashed border, semi-transparent background, centered "Drop to load" cue, high z-index. Visible only when not `[hidden]`.

**Checkpoint**: All three user stories are independently functional. The visualizer is feature-complete per spec.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final manual review, performance spot-check, and documentation pass.

- [X] T037 Regenerate both committed-fixture analysis JSONs by running `python processor/analyze.py sample_replays/base_1.w3g.json` and `python processor/analyze.py sample_replays/base_2.w3g.json`. These are `.gitignore`d (per `research.md §R5`); regenerate them locally before manual review.
- [ ] T038 Walk the full SC-004 manual review checklist (`quickstart.md §Manual SC-004 review checklist`) for `base_1.w3g.analysis.json` and again for `base_2.w3g.analysis.json`. Fix any missing or incorrectly-rendered sections at the source — do NOT add visualizer-side workarounds for analyzer-side gaps.
- [X] T039 Walk the SC-005 timeline-completeness spot-check for at least one player in each fixture (`quickstart.md §Manual SC-005 timeline-completeness spot-check`). Any count mismatch is a bug in `buildTimelineEvents` or in a marker-skipping branch in `renderTimeline`; fix it before signing off. **Verified programmatically before handoff: `buildTimelineEvents` emits exactly the expected count for every player in both fixtures (8/8 in base_1, 6/6 in base_2). Browser-side eyeball pass still pending in T038.**
- [ ] T040 Perform the SC-002 performance spot-check on commodity laptop hardware: `base_1` end-to-end (pick → fully rendered) under 3 s, `base_2` under 1 s (`quickstart.md §Performance spot-check`).
- [ ] T041 Open browser devtools and verify the console is silent during a successful render of each fixture — no warnings, no errors, no deprecation notices. Treat any console output as a defect and resolve it.
- [ ] T042 Walk the edge-case sanity checks in `quickstart.md §Edge-case sanity checks`: pick a `.txt`, pick a Parser-output `*.w3g.json`, pick a malformed JSON, drop a folder. Each must surface its FR-004 error and stay in the landing state. **Validation logic verified programmatically before handoff (parser-output JSON is rejected, malformed JSON is rejected, missing top-level keys are rejected).**
- [X] T043 [P] Update `visualizer/DATA.md` to reflect the as-built page: link to `processor/DATA.md`, link to `specs/003-replay-visualizer/quickstart.md`, summarize the user flow in 4–5 sentences. No screenshots, no large code samples — keep it under 80 lines.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies; T002, T003, T004, T005 are all parallelizable; T001 (mkdir) precedes them.
- **Phase 2 (Foundational)**: depends on Phase 1. Must complete fully before any user-story phase begins.
- **Phase 3 (US1 / P1)**: depends on Phase 2. Must complete to ship MVP.
- **Phase 4 (US2 / P2)**: depends on Phase 2. **Also depends on T019 (`renderPlayerPanel` shell)** because the timeline mounts inside the player panel; in practice US2 starts after Phase 3 has at least the panel skeleton.
- **Phase 5 (US3 / P3)**: depends on Phase 2 (specifically T011 `loadFile` is the entry point reused by drop). Independent of Phase 3 and Phase 4 once Phase 2 is done.
- **Phase 6 (Polish)**: depends on whichever stories are intended to ship.

### Within Each User Story

- US1: T016, T017 are pure helpers and can precede T018; T018 wires team grouping; T019–T025 are the panel sub-renderers that compose into T026; T027 styles them; T028 is the FR-009 verification step.
- US2: T029 is the pure helper; T030 mounts the SVG; T031 is the marker emitter; T032 styles; T033 verifies legibility.
- US3: T034 markup; T035 wiring; T036 styling.

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T005 in parallel after T001.
- **Phase 2**: minimal — most tasks share `visualizer.js`. T008 (CSS only) and T007 (HTML only) can run alongside JS work.
- **Phase 3+**: most JS tasks share one file; in parallel-team mode you would bracket per-renderer work by function and merge serially. The `[P]` marker is reserved for genuinely cross-file independence (T043 polish).
- **Cross-story (with multiple devs)**: once Phase 2 and T019 are in, US2 and US3 can be developed in parallel.

---

## Parallel Example: Phase 1 (Setup)

```bash
# After T001 (mkdir visualizer) completes:
Task: "Create visualizer/index.html skeleton (T002)"
Task: "Create visualizer/styles.css placeholder (T003)"
Task: "Create visualizer/visualizer.js IIFE skeleton (T004)"
Task: "Create visualizer/DATA.md orientation note (T005)"
```

## Parallel Example: Cross-Story Development (Phase 4 + Phase 5)

```bash
# After Phase 2 + T019 (renderPlayerPanel shell) complete:
Developer A: Phase 4 — Timeline (T029–T033)
Developer B: Phase 5 — Drag-and-drop (T034–T036)
# Both can land independently. Final integration is `git merge`-trivial because the touchpoints are different functions in visualizer.js plus disjoint CSS sections.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → 4 skeleton files exist.
2. Phase 2 Foundational → load + validate + render shell + helpers wired; landing-state and error-state work end-to-end.
3. Phase 3 US1 → full text-form match report renders for both fixtures.
4. **Stop and validate**: walk the SC-004 checklist for both fixtures. If it passes, US1 is shippable as the MVP.

### Incremental Delivery

1. Setup + Foundational → smoke-tests with section-name stubs.
2. + US1 → MVP demo (text report).
3. + US2 → analytic-tool demo (timelines).
4. + US3 → polish demo (drag-and-drop).
5. + Phase 6 → shippable v1.

### Parallel Team Strategy (with two developers)

1. Together: Phase 1 + Phase 2.
2. Together: Phase 3 (US1) — tightly integrated, single-file work.
3. Split: Phase 4 (Dev A — timeline) || Phase 5 (Dev B — drag-and-drop). Merge.
4. Together: Phase 6 polish.

---

## Notes

- **No automated frontend tests in v1** — confirmed by spec, by Principle IV scope, and by `plan.md` Constitution Check. Acceptance is the manual walkthrough in `quickstart.md`.
- **No build step, no package manager, no framework** — Principle V. If a task seems to want one ("install d3 for the timeline", "add a `package.json`", "transpile with Babel"), that task is wrong; revisit `research.md` for the no-dependency alternative.
- **No fetch of any kind** — FR-008. The visualizer reads only the file the user picks. If a task suggests fetching `processor/entity_names.json` or any other resource, that task is wrong.
- **One file per concern**: HTML is structure, CSS is presentation, JS is behavior. Cross-file leaks (inline `style=` attributes for layout, inline `onclick=` handlers, etc.) violate the simple-static spirit; avoid them.
- **Console-silent rule (T041)**: the browser devtools console must show zero warnings and zero errors during a successful render. This is a hard precondition for the manual review.
- Commit after each task or each tight task group. Two natural seams: end of Phase 2 (foundational landing), end of Phase 3 (US1 MVP).
