"""Team cohesion analysis package — feature 007.

This package implements the team-cohesion analytics that produces the
`team` top-level key in the analysis JSON. See:

  - specs/007-team-cohesion-analysis/spec.md           # what & why
  - specs/007-team-cohesion-analysis/plan.md           # how (architecture)
  - specs/007-team-cohesion-analysis/data-model.md     # JSON shape
  - specs/007-team-cohesion-analysis/contracts/output-shape.md  # invariants
  - specs/007-team-cohesion-analysis/research.md       # heuristic rationale

All computation lives in this package (Principle I — Strict Layer
Separation). The Visualizer treats the emitted `team.*` block as
read-only data. No external dependencies — Python stdlib only.
"""
