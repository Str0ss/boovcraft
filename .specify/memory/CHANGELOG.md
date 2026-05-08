# Constitution Changelog

This file documents the version history of
`.specify/memory/constitution.md`. Every amendment PR adds a new entry
here describing what changed and why. The current state lives in
`constitution.md`; this file is the audit trail.

Newest entries first.

---

## v1.1.1 — 2026-05-08

**PATCH amendment: presentation cleanup, no semantic change.**

The constitution was loaded once per `/speckit.plan` invocation as the
Constitution Check gate input. At ~4,300 tokens, parts of it were
ceremonial rather than load-bearing — most notably an inline Sync
Impact Report block at the top documenting the prior amendment, and a
verbose Governance + Technology Stack section that paraphrased rules
already stated in the principles. This amendment moves amendment
history to this file and tightens both sections.

### Changes

- Move per-version Sync Impact Report blocks out of `constitution.md`
  and into this file (~600 tokens removed from the always-loaded
  constitution).
- Compress the **Governance** section (Amendments, Versioning,
  Compliance review, Runtime guidance) to its essential rules; verbose
  meta-process text removed (~400 tokens).
- Tighten the **Technology Stack & Interface Contracts** section. The
  Visualizer layer entry is now a one-paragraph pointer to Principle V
  rather than a paraphrase of V's interactive-analytical exception; the
  JSON-on-disk Interface rule is preserved verbatim (~300 tokens).
- Update the Amendments process: PRs now document changes in
  `.specify/memory/CHANGELOG.md` (this file) instead of inline Sync
  Impact Report blocks at the top of `constitution.md`.

Total reduction: ~1,300 tokens (~30%) from `constitution.md`. The
six principles (I–VI) and their rationales are unchanged. No behavioral
change to any quality gate.

### Modified principles

None.

### Modified sections

- **Technology Stack & Interface Contracts** — Visualizer entry
  compressed; "as of v1.1.0..." prose removed (the amendment history
  lives here now).
- **Governance** — Amendments / Versioning / Compliance review /
  Runtime guidance condensed; Amendments paragraph points at this
  file.

### Templates requiring updates

- ✅ `.specify/memory/constitution.md` — written.
- ✅ `.specify/memory/CHANGELOG.md` — created (this file).
- ⚠ `.specify/templates/plan-template.md` — no change required.
- ⚠ `.specify/templates/spec-template.md` — no change required.
- ⚠ `.specify/templates/tasks-template.md` — no change required.
- ⚠ `CLAUDE.md` — no change required (does not reference the
  Sync Impact Report block format).

### Follow-up TODOs

None.

---

## v1.1.0 — 2026-05-03

**MINOR bump** — adds Principle VI (Prefer Well-Established Tools Over
Bespoke Implementations); refines Principle III (No Premature
Abstractions) to clarify that its scope is INTERNAL structure with an
explicit cross-reference to VI for external dependencies; expands
Principle V (Incremental Frontend Evolution) with an
interactive-analytical exception that admits a framework + build step
under three preserve clauses (JSON-only inter-layer contract, simple
single-command deployment in both production and development, no
runtime network egress from the browser).

Triggered by feature 004 (visualizer-tabs) implementation: the
hand-rolled SVG histogram timeline reached the limit of what is
tractable without a chart library, and upcoming features
(brush-to-zoom, filterable events, the future Map tab's spatial
visualization, the Analysis tab's text export) push the visualizer
firmly into "interactive analytical UI" territory rather than "static
document." The amendments preserve the discipline (offline, JSON-only
contract, single-command deploy) while opening the door to the React
+ visx (or equivalent) migration that feature 005 will spec.

### Modified principles

- **III. No Premature Abstractions** — scope clarified to INTERNAL
  structure; cross-reference to VI added for external dependencies;
  YAGNI core unchanged.
- **V. Incremental Frontend Evolution** — interactive-analytical
  exception added with three preserve clauses (a/b/c). The default
  posture (static HTML until justified) and the "probably nice later
  is insufficient" guardrail are preserved.

### Added principles

- **VI. Prefer Well-Established Tools Over Bespoke Implementations.**

### Modified sections

- **Technology Stack & Interface Contracts** → Visualizer layer entry
  rewritten to align with amended V (framework + build step + package
  manager permitted under a feature spec citing the exception; the
  three preserve clauses listed).
- **Development Workflow & Quality Gates** → item 4 (Frontend gate)
  updated to reference the V exception's preserve clauses; new item 5
  (Library justification gate) added for VI.
- **Governance** → Compliance review enumerates Principles I–VI;
  runtime guidance entry unchanged.

### Removed sections

None.

### Templates requiring updates

- ✅ `.specify/memory/constitution.md` (file written).
- ⚠ `.specify/templates/plan-template.md` — no change required for
  this amendment. The Constitution Check section reads from this file
  generically and will pick up VI without template surgery.
- ⚠ `.specify/templates/spec-template.md` — no change required.
- ⚠ `.specify/templates/tasks-template.md` — no change required.
- ⚠ `CLAUDE.md` — does not reference the constitution version; no
  change required.

### Follow-up TODOs

None.

---

## v1.0.0 — 2026-04-21

Initial ratification. Five principles:

- **I. Strict Layer Separation (Parser → Processor → Visualizer)**
- **II. w3gjs Is The Canonical Parser**
- **III. No Premature Abstractions**
- **IV. Fixture-Based Testing With Real Replays**
- **V. Incremental Frontend Evolution**

Plus the Technology Stack & Interface Contracts, Development Workflow
& Quality Gates, and Governance sections.
