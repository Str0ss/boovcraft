<!--
Sync Impact Report
==================
Version change: (unratified template) → 1.0.0
Rationale: Initial ratification. First concrete fill of the constitution
template, establishing the project identity, five core principles, tech
stack constraints, and governance. MAJOR bump from 0.0.0 → 1.0.0 reflects
the transition from placeholder template to an adopted governance document.

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Strict Layer Separation (Parser → Processor → Visualizer)
  - [PRINCIPLE_2_NAME] → II. w3gjs Is The Canonical Parser
  - [PRINCIPLE_3_NAME] → III. No Premature Abstractions
  - [PRINCIPLE_4_NAME] → IV. Fixture-Based Testing With Real Replays
  - [PRINCIPLE_5_NAME] → V. Incremental Frontend Evolution

Added sections:
  - Technology Stack & Interface Contracts (replaces [SECTION_2_NAME])
  - Development Workflow & Quality Gates (replaces [SECTION_3_NAME])
  - Governance (filled)

Removed sections: none.

Templates requiring updates:
  - ✅ .specify/memory/constitution.md (this file, written)
  - ⚠ .specify/templates/plan-template.md — Constitution Check section is a
    generic placeholder ("[Gates determined based on constitution file]");
    update when first /speckit.plan run occurs to enumerate gates derived
    from Principles I–V (layer separation, w3gjs-only parsing, YAGNI,
    fixture tests, HTML-first).
  - ⚠ .specify/templates/spec-template.md — no constitution-specific hooks
    present; no change required unless future amendments add mandated
    spec sections (e.g., a dedicated "Layer Boundary" requirements block).
  - ⚠ .specify/templates/tasks-template.md — sample tasks remain generic;
    when first feature is tasked, ensure task categorization reflects the
    three-layer pipeline (parser tasks, processor tasks, visualizer tasks)
    and fixture-test tasks rather than generic backend/frontend splits.
  - ⚠ CLAUDE.md — currently a single-line pointer to "the current plan";
    consider adding a reference to this constitution for runtime guidance
    once a feature plan exists.

Follow-up TODOs: none. No placeholders were intentionally deferred.
-->

# Boovcraft Constitution

## Core Principles

### I. Strict Layer Separation (Parser → Processor → Visualizer)

The system is composed of three isolated layers — **Parser** (Node.js +
w3gjs, extracts raw replay structure), **Processor** (Python, computes
derived statistics, aggregations, and analysis), and **Visualizer** (HTML,
later React, presents results to the user). Layers MUST communicate only
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
or adopting an alternative parser is prohibited unless w3gjs is demonstrably
unable to express a needed field AND the limitation is documented in a
proposed amendment to this constitution. If a bug or gap is found in
w3gjs, the first response is to upstream a fix, not to replace the
library.

Rationale: Replay format parsing is the one domain where "do it
ourselves" has unbounded cost and compounding bug surface. Centralizing
on w3gjs collapses that cost and guarantees that the parser layer's
output semantics match the ecosystem rather than a local interpretation.

### III. No Premature Abstractions

Code MUST be written for the concrete case in front of it. Helpers,
base classes, generic pipelines, configuration layers, and plugin systems
are forbidden until a second or third real use case demands them.
Duplicating three similar lines is preferred to introducing an
abstraction that anticipates a fourth. Dead parameters, "just in case"
options, and unused extensibility points MUST be removed on sight.

Rationale: This is a single-purpose analysis tool. Every speculative
abstraction adds surface area that must be read, maintained, and reasoned
about while delivering no user value. The JSON-between-layers contract
already provides enough structural flexibility; further indirection is
cost without benefit.

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

The visualizer layer MUST begin as static HTML (optionally with plain
JavaScript loaded from files). Adoption of React, or any other
frontend framework, build step, bundler, or component system, is
prohibited until a concrete user-facing requirement makes static HTML
materially insufficient AND that requirement is recorded in a plan
document. "It will probably be nice later" is not a sufficient
justification.

Rationale: Static HTML loads JSON from the processor and renders it —
that is the entire visualizer contract. A framework introduces build
tooling, a dependency graph, and a mental model that actively obstruct
the three-layer separation until there is a real reason to pay those
costs.

## Technology Stack & Interface Contracts

**Parser layer**: Node.js, `w3gjs` as the sole parsing dependency. Output
is a JSON document written to disk (or stdout) describing the replay's
structural content. The output schema is defined by what w3gjs produces,
optionally narrowed; it is NOT a reinterpretation.

**Processor layer**: Python. Reads the parser's JSON as input, produces
analysis JSON as output. The processor MUST NOT shell out to Node or
call w3gjs directly; it operates purely on the serialized parser output.

**Visualizer layer**: Static HTML + (optionally) vanilla JavaScript.
Loads the processor's JSON and renders it. No build step, no package
manager in this layer until Principle V is amended.

**Interface rule**: Every inter-layer boundary is a JSON file (or stdout
piped to a file). If you cannot point at the file that one layer wrote
and another layer read, the separation is violated.

## Development Workflow & Quality Gates

1. **Fixture-first for parsing/analysis changes**: Any change affecting
   the parser or processor MUST be accompanied by at least one real
   replay fixture exercising the new behavior, or reuse an existing
   fixture that demonstrably covers it.

2. **Layer boundary check**: Every PR MUST be reviewable as "does this
   change keep the three layers separable?" A change that introduces a
   cross-layer import, a shared in-process data structure, or a shell-out
   from one layer to another MUST be rejected or justified in the plan's
   Complexity Tracking table.

3. **YAGNI review**: Reviewers MUST flag new abstractions, config
   surfaces, and parameters that lack a named current use case. The
   default disposition is removal.

4. **Frontend gate**: Any PR introducing a framework, bundler, transpiler,
   or npm/yarn dependency in the visualizer layer MUST cite the concrete
   requirement that static HTML cannot meet, and MUST be accompanied by
   a constitution amendment under Principle V.

## Governance

This constitution supersedes ad-hoc preferences and informal conventions.
When a PR, plan, or task conflicts with a principle here, the principle
wins unless the conflict is resolved by amending the constitution first.

**Amendments**: Proposed by editing this file in a PR. The PR MUST
include the Sync Impact Report block at the top, the updated version,
and any propagated changes to dependent templates (plan, spec, tasks)
or runtime guidance (CLAUDE.md). Amendments take effect when the PR
merges.

**Versioning policy**: Semantic versioning applies to this document.
MAJOR = a principle is removed or its rule is redefined in an
incompatible way; MINOR = a new principle or section is added, or an
existing principle's scope materially expands; PATCH = wording,
clarification, typo, or non-semantic refinement.

**Compliance review**: Every `/speckit.plan` run MUST pass a
Constitution Check gate derived from Principles I–V before Phase 0
research proceeds, and MUST be re-checked after Phase 1 design.
Violations require an entry in the plan's Complexity Tracking table
with explicit justification; unjustified violations block the plan.

**Runtime guidance**: `CLAUDE.md` is the entry point for agent runtime
guidance and SHOULD reference this constitution once a concrete plan
exists.

**Version**: 1.0.0 | **Ratified**: 2026-04-21 | **Last Amended**: 2026-04-21
