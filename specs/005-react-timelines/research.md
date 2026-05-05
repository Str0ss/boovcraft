# Research: Interactive Timelines (React Migration + Brush + Filter) — Feature 005

Phase 0 of `/specs/005-react-timelines/plan.md`. Resolves the
technology, library, deployment, and testing questions raised by
Technical Context. Each section ends with the four-criteria
verification mandated by Principle VI of constitution v1.1.0
(active maintenance ≤ 12 mo, broad adoption, permissive license, API
stability).

## R1. Chart library — Apache ECharts vs visx vs Recharts

**Decision**: **Apache ECharts** via `echarts-for-react`.

**Rationale**:
- The two most expensive interactions in the spec — multi-chart
  brush-to-zoom that synchronizes across N player rows (US1 / FR-002)
  and per-category legend toggles applied uniformly across all rows
  (US2 / FR-009–017) — are first-class ECharts features. `dataZoom`
  with `type: 'inside'` + `type: 'slider'` covers slider-and-mouse
  zoom; brush selection drives `dataZoom`'s `setOption({ start, end })`
  out of the box. `echarts.connect(groupId)` synchronizes zoom +
  axis + tooltip across multiple chart instances with one call. The
  built-in legend is interactive by default (click a series to toggle).
  None of this is custom code — the spec is largely a configuration
  problem with ECharts.
- Feature 004's vanilla SVG histograms reached the limit of what's
  tractable without a library (this feature's trigger). The user's
  "looks poor" complaint targeted precisely the polish-and-feel layer
  that ECharts ships well-tuned: smooth bar transitions, anti-aliased
  axis ticks, accessible focus rings, locale-aware tooltips.
- Canvas rendering at 8 charts × ~500 buckets × 12 categories sustains
  the 100 ms re-render budget (SC-002 / SC-003) more reliably than
  SVG-based libraries. visx is SVG; large stacked histograms can
  push past 100 ms with N players × thousands of `<rect>` nodes.
- ECharts produces clean, polished defaults; we don't need a designer
  to ship something that looks professional on day one.

**Alternatives considered**:
- **visx (Airbnb)** — composable React wrappers around D3. Gorgeous
  fit for React idiom; smaller bundle (~50–80 KB depending on
  imports). Rejected because: (1) brush + dataZoom + connected zoom
  across N charts requires writing the orchestration ourselves —
  exactly the bespoke code Principle VI wants us to avoid; (2) SVG
  rendering at 8 charts × thousands of bars approaches the 100 ms
  budget on the largest fixture, where ECharts' canvas comfortably
  beats it; (3) recent maintenance cadence has slowed (commits
  irregular over the past year) — borderline on Principle VI's
  "actively maintained" criterion. Worth re-evaluating if ECharts
  bundle size becomes a real problem.
- **Recharts** — easiest API, but synchronized zoom across many
  charts is genuinely hard (Recharts assumes one chart per consumer).
  Skipping for the same reason called out in earlier conversation:
  it would fight the user.
- **D3 directly with React refs** — most flexible, most code. The
  whole point of this migration is to stop hand-rolling visualization
  primitives.
- **Plotly** — feature-rich but bundles much heavier (~600 KB+);
  styling is dated; less React-idiomatic.

**Principle VI verification (ECharts)**:
1. **Active maintenance**: ✓ — `apache/echarts` on GitHub has
   commits and releases within the past 90 days as of 2026-05-04.
   Apache governance ensures ongoing maintenance independent of any
   single corporate sponsor.
2. **Broad adoption**: ✓ — used by Apache Superset, Grafana plugins,
   countless internal tools at major Chinese tech firms (Alibaba,
   Tencent, Bytedance), 60k+ GitHub stars. The `echarts-for-react`
   wrapper has ~2M weekly npm downloads.
3. **Permissive license**: ✓ — Apache-2.0 (allowed list).
4. **API stability**: ✓ — major version 5 has been stable since
   2021; ECharts has historically deprecated APIs over multiple
   minor versions before removal.

All four criteria pass.

## R2. Framework — React vs Svelte vs SolidJS

**Decision**: **React 18.x**.

**Rationale**:
- The user's trigger description named React explicitly. Per the
  spec's Assumption section, the spec is technology-agnostic at the
  FR level, but the plan commits — and there's no signal pulling
  toward an alternative.
- React + ECharts + Vite is the path with the highest density of
  recent reference implementations (every "ECharts in a React app"
  tutorial, the maintained `echarts-for-react` wrapper, and the
  paved path for the file-picker / drag-drop / state-Context
  patterns we already know).
- The React ecosystem has the deepest pool of well-established
  companion libraries that meet Principle VI criteria for any future
  add-ons (Map tab → Leaflet/Mapbox, Analysis tab → markdown
  rendering, etc.) — keeps optionality open without re-amending.

**Alternatives considered**:
- **Svelte / SvelteKit** — smaller bundle, no virtual-DOM overhead,
  arguably nicer DX. Rejected because: ECharts integration is
  thinner (no comparable wrapper to `echarts-for-react`); the user
  explicitly named React; future-feature optionality (LLM-paste UI,
  map tile rendering) has more paved-road support in React.
- **SolidJS** — fast, fine-grained reactivity. Same problem as
  Svelte: thinner ecosystem for our specific chart + future-feature
  needs.

**Pin to React 18 (not 19)**: As of 2026-05-04, React 19 is GA but
some chart-library wrappers (including `echarts-for-react` 3.x) ship
peer-dep ranges that support 16–18; we don't fight peer-dep mismatches
during the first ship. Upgrade in a follow-up once `echarts-for-react`
or its replacement supports 19 cleanly.

**Principle VI verification (React 18)**: ✓ all four (active
maintenance, broadest possible adoption, MIT license, semver
discipline established for many years).

## R3. Build tool — Vite

**Decision**: **Vite 5.x**.

**Rationale**:
- Fast dev server with hot module reload — directly supports the
  spec's SC-005 ≤ 10 s `npm run dev` startup target.
- Standard for React + TypeScript SPAs in 2025–2026; effectively
  replaced Create React App (which was archived).
- Default production output (`dist/`) is a static folder that nginx
  can serve directly — no server-side anything required.
- Configuration surface is small: `vite.config.ts` with `react()`
  plugin, no custom Webpack-style juggling.

**Alternatives considered**:
- **Next.js** — overkill (SSR, file-based routing, RSC) for a
  client-only SPA loading user-picked JSON; would also drag in a
  Node runtime in production where we want plain nginx. Rejected.
- **Parcel** — fine but smaller ecosystem.
- **esbuild / Rollup directly** — more configuration; Vite already
  uses both under the hood.

**Principle VI verification (Vite)**: ✓ all four (active maintenance
under VoidZero/Vite team, broad adoption — most React tutorials post
2023 default to Vite, MIT license, stable v5 since late 2023).

## R4. Type checker / language — TypeScript

**Decision**: **TypeScript 5.5+** in strict mode.

**Rationale**:
- The analysis JSON has a 50+ field shape across nested objects.
  Typing it once (`AnalysisJson`, `Player`, `TimedAction`, etc.)
  pays for itself the first time you mistype a field name in a
  component prop or aggregation function.
- ECharts' option object is large and easy to misconfigure;
  `@types/echarts` (or types bundled with `echarts-for-react`)
  catches misnamed series properties at compile time.
- Vitest first-class supports TypeScript with no extra setup.
- Strict mode (`strict: true` in tsconfig) catches the `null`/`undefined`
  edge cases that vanilla JS would only surface at runtime — the
  same edge cases feature 004's smoke test surfaced as zero-render
  bugs that took manual investigation.

**Alternatives considered**:
- **Plain JavaScript** — fewer types to fight; zero compile step in
  the source mental model. Rejected because the JSON-shape surface
  is large enough that the TS investment pays back during the first
  feature, and Vite's TS handling is essentially zero-config.
- **JSDoc types over JS** — typing without TS. Plausible but the
  ergonomics of inline interfaces in `.tsx` files vastly exceed
  JSDoc. Rejected.

**Principle VI verification (TypeScript)**: ✓ all four.

## R5. Test runner — Vitest

**Decision**: **Vitest 1.x** for the new unit-test layer; pytest for
the unchanged Processor; manual walkthrough for the visual layer.

**Rationale**:
- Vitest is Vite's natural test pair — same config, same module
  resolution, same TypeScript handling. Zero-friction setup.
- Targeted at the pure logic the new code introduces: brush-rectangle
  → time-range conversion (FR-001/002 math), bucket-width selection
  given zoom + viewport, filter-state reducer, zoom-history reducer,
  aggregation helpers ported from feature 004 (`aggregateProduction`,
  `aggregateHeroes`, `aggregateTransfers`).
- Tests load real `*.analysis.json` from `sample_replays/` rather
  than hand-rolled mocks — same posture Principle IV established
  for the Processor.

**Alternatives considered**:
- **Jest** — older, more configuration to align with Vite + TS;
  rejected for the friction.
- **No automated tests in v1** (matching feature 003's stance) —
  rejected because the React migration introduces *new* pure logic
  (brush math, history reducer, filter reducer) where automated
  tests are cheap and high-leverage; only the visual layer keeps
  the manual posture from feature 003.

**Principle VI verification (Vitest)**: ✓ all four.

## R6. Deployment — Docker (production) + Vite dev server (development)

**Decision**:
- **Production**: `docker compose up` brings up a single service
  named `visualizer` running nginx-on-alpine, serving the
  Vite-produced `dist/` folder on port 8080 (configurable). The
  Dockerfile is a multi-stage build: stage 1 runs
  `npm ci && npm run build`; stage 2 copies `dist/` into
  `nginx:alpine` with a minimal `nginx.conf` (no upstream proxies,
  no remote fetch, `try_files $uri $uri/ /index.html` SPA
  fallback).
- **Development**: `npm run dev` from inside `visualizer/` starts
  the Vite dev server, default port 5173, with HMR.

**Rationale**:
- Both modes are first-class per Principle V (b). Neither requires
  the other.
- nginx-alpine is the most boring possible production server: tiny
  image (~20 MB), zero logic, predictable behavior. Caching headers
  are set sensibly by default. No Node runtime in production —
  matches the "ship a static dist" posture exactly.
- `docker compose` (rather than raw `docker run`) keeps the bring-up
  command stable and gives a place to add sibling services later
  (the future Map tab's tile-server, the future Analysis-pipeline
  helper) without renegotiating user UX.

**Alternatives considered**:
- **GitHub Pages / Netlify / Vercel hosting** — violates Principle V
  (c) (no runtime egress) and the spec's offline guarantee; users
  may need to use this without internet.
- **`npx serve dist`** as the production mode — works but requires
  the user to have Node installed in production too. Documented as
  a fallback in `quickstart.md`, not the canonical path.
- **`vite preview`** as the production mode — same Node-required
  problem, plus it's not a hardened production server.

**Principle V (a)/(b)/(c) verification**:
- (a) JSON-only contract: ✓ — the SPA's only runtime input is the
  user-picked `*.analysis.json`. No network fetches.
- (b) Single-command deploy in both modes: ✓ — `docker compose up`
  vs `npm run dev` both bring the visualizer up with no manual
  config beyond ports (documented defaults).
- (c) No runtime egress: ✓ — the production image bundles all
  assets; nginx serves locally; the page makes zero outbound
  requests at runtime (verified by SC-006 manual check).

## R7. Bundling pitfalls — fonts, locale data, source maps

**Decision**:
- **Fonts**: system-font-stack only. CSS uses
  `font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
   Roboto, Oxygen, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;`
  (carried from feature 004). No Google Fonts, no `@font-face` URL
  loads — verified at build time by absence of any `font-display`
  or external `url(…)` references in CSS.
- **ECharts locale**: import the small set of locale strings
  statically (English only). Do NOT use ECharts' dynamic locale
  loader (which would `import()` at runtime — tree-shaking handles
  this when only English is referenced).
- **Source maps**: enabled in development; disabled in production
  builds to keep the dist size small and avoid leaking unminified
  code into the container.

**Rationale**: These are the three places a "static SPA" can
accidentally make a network request after page load. Documenting
them explicitly here and verifying them in `quickstart.md` step "X.
Network-tab egress check" prevents Principle V (c) violations.

## R8. State management — plain React + Context

**Decision**: One React Context provider exposing `pageState` and a
small set of dispatchers. No external state library.

**Rationale**:
- The cross-component state surface is small: `loadedFile`,
  `analysis`, `activeTab`, `zoomState`, `zoomHistory`, `filterState`.
  Six fields. Adding Redux / Zustand / Jotai for six fields is the
  exact "abstraction ahead of need" Principle III forbids.
- The reducer-shaped fields (`zoomHistory`, `filterState`) are pure
  TS modules tested by Vitest; the Context just plumbs them.

**Alternatives considered**:
- **Zustand** — small, idiomatic, tempting. Rejected only because
  six fields don't justify the dependency under VI. If a seventh
  feature genuinely needs a more sophisticated state surface, this
  decision is reversible.
- **Redux Toolkit** — overkill at this scale.

## R9. Testing the brush math

**Decision**: Vitest tests for the pure conversion helpers:
- `pixelsToTimeRange(brushPx, viewportPx, visibleRange) → {startMs, endMs}`
- `clampBrushedRange(rawRange, durationMs, minBucketMs) → clampedRange`
- `applyFilterToBuckets(buckets, filterState) → filteredBuckets`
- `zoomHistory.reducer(state, action) → newState` for `BRUSH`,
  `RESET`, `BACK`, `FORWARD`, `LOAD_FILE`.

Each test loads a committed `*.analysis.json` fixture, exercises the
helper, and asserts on shape / boundary conditions. Mock-free.

**Rationale**: These are the genuinely-easy-to-break pieces of the
new feature. Brush math has off-by-one risk (start < end? clamping
order?); the history reducer has the standard back/forward stack
edge cases (push after step-back discards forward; reset clears
both). Vitest unit coverage for these is cheap, pays off in
implementation, and is the layer Principle IV's spirit reaches into
(test against real fixtures).

---

All Phase 0 questions resolved. No `[NEEDS CLARIFICATION]` markers
remain in the spec; this research grounds the plan's Technical
Context choices and the Constitution Check evidence.
