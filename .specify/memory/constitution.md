# Boovcraft Constitution

Amendment history: see `.specify/memory/CHANGELOG.md`.

## Core Principles

### I. Strict Layer Separation (Parser → Processor → Visualizer)

The system is composed of three isolated layers — **Parser** (Node.js +
w3gjs, extracts raw replay structure), **Processor** (Python, computes
derived statistics, aggregations, and analysis), and **Visualizer**
(browser, presents results to the user). Layers MUST communicate only
through JSON documents serialized to disk or stdout. A downstream layer
MUST NOT import, link to, or invoke upstream code in-process; it consumes
the upstream JSON as its sole input contract.

Rationale: Each layer has a distinct runtime (Node, Python, browser) and
a distinct responsibility. JSON-at-the-boundary lets any layer be
replaced, inspected, diffed, cached, or rerun in isolation without
breaking the others. It also makes fixtures trivially reusable across
layers.

### II. w3gjs Is The Canonical Parser

All Warcraft III replay (`.w3g`) parsing MUST go through the `w3gjs`
library. Writing a custom binary reader, forking w3gjs into this repo,
or adopting an alternative parser is prohibited unless w3gjs is
demonstrably unable to express a needed field AND the limitation is
documented in a proposed amendment to this constitution. If a bug or
gap is found in w3gjs, the first response is to upstream a fix, not to
replace the library.

Rationale: Replay format parsing is the one domain where "do it
ourselves" has unbounded cost and compounding bug surface. Centralizing
on w3gjs collapses that cost and guarantees that the parser layer's
output semantics match the ecosystem rather than a local interpretation.

### III. No Premature Abstractions

This principle governs **internal structure**: the helpers, base
classes, generic pipelines, configuration layers, and plugin systems
that a contributor might be tempted to add inside this codebase. Code
MUST be written for the concrete case in front of it. Internal
abstractions are forbidden until a second or third real use case
demands them. Duplicating three similar lines is preferred to
introducing an abstraction that anticipates a fourth. Dead parameters,
"just-in-case" options, and unused extensibility points MUST be
removed on sight.

This principle does NOT govern external dependencies. The choice of
whether to *adopt* a third-party library — chart rendering, scale
arithmetic, parsing, state management, etc. — is governed by Principle
VI. III restricts what we *build*; VI restricts what we *write
ourselves when something well-established already exists*. The two
principles together describe right-sized engineering effort: lean on
the ecosystem for the hard problems (VI), keep your own code simple
for the easy ones (III).

Rationale: This is a single-purpose analysis tool. Every speculative
internal abstraction adds surface area that must be read, maintained,
and reasoned about while delivering no user value. The
JSON-between-layers contract already provides enough structural
flexibility; further internal indirection is cost without benefit.

### IV. Fixture-Based Testing With Real Replays

Tests MUST exercise real `.w3g` replay files committed as fixtures.
Synthetic byte streams, mocked w3gjs output, and hand-rolled fake
game-event sequences are prohibited in tests whose purpose is to verify
parsing or analysis correctness. Each fixture SHOULD be accompanied by
a short note describing the match (players, map, notable events) so
that expected-output assertions are grounded in reality.

Rationale: Replay parsers fail in ways that only real files expose
(patch-version drift, unusual action sequences, desyncs, observers).
A test suite built on mocks will happily stay green while the tool
breaks on the next replay a user drops in.

### V. Incremental Frontend Evolution

The visualizer layer began as static HTML with vanilla JavaScript and
SHOULD remain that simple by default. Adoption of a frontend framework,
build step, bundler, package manager, or component system is prohibited
unless a concrete user-facing requirement makes the static approach
materially insufficient AND that requirement is recorded in a feature
spec. "It will probably be nice later" is not a sufficient
justification.

**Interactive-analytical exception.** When a feature spec records a
concrete interactive-analytical requirement — examples include
brush-to-zoom over multi-chart layouts, cross-chart filter coordination
synchronized across many panels, animation of derived state, or
multi-axis interactions whose state cannot be cleanly separated from
rendering without accumulating bugs at the seams — a framework +
build step + package manager MAY be adopted in the visualizer layer.
Adoption MUST preserve all three of the following:

  (a) **JSON-on-disk inter-layer contract from Principle I.** The
      visualizer consumes `*.analysis.json` exactly as the static
      implementation did. Adopting a framework MUST NOT require any
      change to the Parser or Processor layers in order for the
      visualizer to load a previously-rendered fixture.

  (b) **Simple deployment.** Bringing up the visualizer MUST be a
      single command with no manual configuration of paths, ports, or
      environment beyond documented defaults. Both production usage
      (e.g., `docker run` / `docker compose up`) and developer
      iteration (e.g., `npm run dev` or equivalent) are first-class;
      neither is privileged over the other. The build artifact's
      shape (single-file HTML, dist folder, container image) is a
      per-feature plan decision; the constraint is the user-facing
      one-command property.

  (c) **No runtime network egress from the browser.** The page MUST
      function fully offline once the image / dist is local. No CDN
      scripts, no external fonts, no telemetry, no analytics, no
      "open by URL" loaders, no remote JSON fetches. Local-only HTTP
      between the browser and a sibling container in the same compose
      graph is permitted — that traffic is part of the user's local
      process, not external network access.

Rationale: Static HTML loading JSON from the processor and rendering
it was the entire visualizer contract at v1.0.0. As the visualizer
grows from "static document" toward "interactive analytical UI" —
zoomable histograms, brush selection, cross-chart filtering, spatial
map rendering, animation — the cost of preserving the literal
no-build-step constraint exceeds the cost of accepting a tooling
chain. The three preserve clauses keep the discipline (offline-capable,
JSON-only inter-layer contract, single-command deploy) while opening
the door to mature analytical-UI tooling. The default posture remains
"static unless justified": no feature gets a free pass; the
interactive-analytical trigger MUST be specific and recorded.

### VI. Prefer Well-Established Tools Over Bespoke Implementations

When a problem domain has a mature, widely-adopted solution — chart
rendering, scale arithmetic, replay parsing (see also II), date math,
state management, layout, virtualization, schema validation, and so on
— a contributor MUST use a third-party library rather than write a
bespoke implementation. Bespoke implementations require justification:

  - A measured limitation in the candidate libraries (documented with
    the specific case the library cannot express),
  - A license incompatibility (the candidate library is GPL or other
    license incompatible with this repository's license posture),
  - A runtime incompatibility (the candidate library requires a
    runtime feature this layer cannot provide),
  - **OR** the YAGNI escape hatch: the requirement is small enough
    that a handful of inline lines genuinely beats a dependency. This
    is where Principle III bites — internal abstractions are also
    forbidden, so the inline path MUST be both small and direct.

"Well-established" means **all four** of the following:

  1. **Active maintenance** — commits to the library's main branch
     within the past ~12 months.
  2. **Broad adoption** — the library appears in the dependency lists
     of multiple major projects in its domain, OR is part of an
     official tooling ecosystem (e.g., a framework's recommended
     companion library), OR has comparably credible adoption signal.
     Star count alone is not adoption; "popular among hobbyists" is
     not enough.
  3. **Permissive license** — MIT, BSD, Apache-2.0, or ISC.
  4. **API stability track record** — at least one stable major
     release line, with an explicit policy or demonstrated history of
     not breaking consumers without a major-version bump.

Do not over-engineer custom solutions. Reach for the boring,
established tool first; introduce bespoke code only with one of the
justifications above documented in the feature plan.

Rationale: Bespoke implementations of solved problems compound
maintenance cost, multiply bug surface, and lock the project out of
ecosystem improvements. Principle III rules out building elaborate
internal scaffolding, but it must not be misread as ruling out
*external* libraries that already solve the problem cleanly. A
handwritten histogram engine is not "minimal" — it is a permanent
maintenance debt swapped for a transient one-time integration cost.
The four "well-established" criteria are deliberately strict so that
VI does not become a rubber-stamp for adding any random package: the
test is whether a reviewer five years from now will still recognize
the dependency as a sensible choice.

## Technology Stack & Interface Contracts

**Parser layer**: Node.js, `w3gjs` as the sole parsing dependency.
Output is a JSON document on disk (or stdout) describing the replay's
structural content — defined by what w3gjs produces, optionally
narrowed; never a reinterpretation.

**Processor layer**: Python. Reads the parser's JSON, writes analysis
JSON. MUST NOT shell out to Node or call w3gjs directly.

**Visualizer layer**: Browser-based view of the analysis JSON. Default
posture is static HTML + vanilla JS. A framework + build step + package
manager MAY be adopted under Principle V's interactive-analytical
exception (see V for the trigger and the three preserve clauses); this
is a per-feature plan decision, not a project-wide flip.

**Interface rule**: Every inter-layer boundary is a JSON file (or
stdout piped to a file). If you cannot point at the file that one
layer wrote and another layer read, the separation is violated.

## Development Workflow & Quality Gates

1. **Fixture-first for parsing/analysis changes**: Any change
   affecting the parser or processor MUST be accompanied by at least
   one real replay fixture exercising the new behavior, or reuse an
   existing fixture that demonstrably covers it.

2. **Layer boundary check**: Every PR MUST be reviewable as "does
   this change keep the three layers separable?" A change that
   introduces a cross-layer import, a shared in-process data
   structure, or a shell-out from one layer to another MUST be
   rejected or justified in the plan's Complexity Tracking table.

3. **YAGNI review**: Reviewers MUST flag new internal abstractions,
   config surfaces, and parameters that lack a named current use case
   (Principle III). The default disposition is removal. This gate is
   independent of the library-adoption gate (item 5 below).

4. **Frontend gate**: Any PR introducing a new framework, bundler,
   transpiler, or first-time package manager in the visualizer layer
   MUST: cite the concrete interactive-analytical requirement that
   triggers the Principle V exception (or, in the limit, propose a
   further constitution amendment); verify each of the three V
   preserve clauses (JSON-only contract, single-command deploy, no
   runtime egress); and document the choice in the feature's plan.

5. **Library justification gate**: Per Principle VI, any PR
   introducing a new external dependency (in any layer) MUST: cite
   the concrete problem domain the dependency solves; record the
   library's adherence to all four "well-established" criteria
   (active maintenance, broad adoption, permissive license, API
   stability); or explicitly justify a bespoke implementation under
   one of VI's escape hatches (measured limitation, license
   incompatibility, runtime incompatibility, or YAGNI). Reviewers
   MUST flag new dependencies that fail any of the four criteria.

## Governance

This constitution supersedes ad-hoc preferences. When a PR, plan, or
task conflicts with a principle, the principle wins until an amendment
resolves the conflict.

**Amendments** are proposed by editing this file in a PR that also adds
an entry to `.specify/memory/CHANGELOG.md`, bumps the version, and
propagates any required changes to templates (plan / spec / tasks) and
runtime guidance (`CLAUDE.md`). They take effect when the PR merges.

**Versioning** is semantic. MAJOR = principle removed or redefined
incompatibly. MINOR = new principle or section added, or existing scope
materially expanded. PATCH = wording, clarification, presentation.

**Compliance review**: every `/speckit.plan` run MUST pass a
Constitution Check gate derived from Principles I–VI before Phase 0
research and again after Phase 1 design. Violations require an entry in
the plan's Complexity Tracking table with explicit justification;
unjustified violations block the plan.

**Runtime guidance**: `CLAUDE.md` is the entry point for agent runtime
guidance.

**Version**: 1.1.1 | **Ratified**: 2026-04-21 | **Last Amended**: 2026-05-08
