# Research — Team Tab Data Drill-Downs

This document records design decisions for feature 007. Smaller in scope than feature 006's research because there are no analyzer changes, no new event probes, no new lookup tables.

## R1. Audit basis

The decision to build feature 007 came from a post-006 audit comparing what the analyzer emits in `team.*` against what the Team tab renders. The audit (recorded in chat 2026-05-08) found that ~40% of the JSON content was hidden:

| Hidden field | What it provides |
|---|---|
| `battle.pings[*]` (only count was shown) | Per-ping reaction classification — buys back original requirement 4.2 |
| `battle.focusFire.contributingPlayers[]` | Per-attacker breakdown — buys back original requirement 4.1 |
| `battle.kills[]` | Per-battle kill list with credits |
| `battle.centroids[]`, `alliedDistances[]` | Geometry behind split-engagement flag |
| `battleSummary.tei[i].perPlayerTei[]` | Per-player trade efficiency |
| `battleSummary.attributions[]` (when empty) | Strategic blame attribution surface |
| `executive[*].evidenceRef` | Click-to-scroll navigation |

Each of these is **additive UI surface** over existing JSON; no analyzer change is required.

## R2. Why a separate feature, not a 006 amendment

Per project convention (003 → 004 → 005), each iteration of the visualizer ships as its own feature with its own quickstart bar. Feature 006's quickstart documents an explicit acceptance state — adding new user-visible requirements to it after merge would invalidate the "shipped" status.

Architecturally:
- Feature 006 fixed the JSON contract (`team.*` shape).
- Feature 007 fixes the UI contract (`Team tab MUST render X for Y`).

The new `contracts/ui-contract.md` file is the first project artifact of its kind. Treating it as a feature deliverable rather than an inline amendment keeps the contract surface auditable.

## R3. Heuristic constants

**Kills top-N = 10.** Picked to fit a typical desktop viewport without scrolling internally. On `base_2` battle 0 there are 60 kills; the top-10 by `victimValue` covers the high-value targets (heroes, T2/T3 units) which are the most informative for a coach.

**Highlight pulse duration = 2000 ms.** Common UX value for "noticed without lingering." Two seconds is long enough to track gaze; longer becomes annoying on repeated clicks.

**Smooth-scroll behavior = `{behavior: 'smooth', block: 'center'}`.** `block: 'center'` keeps the highlighted target visually anchored mid-viewport. `behavior: 'smooth'` is universally supported in modern desktop browsers (V (c) target).

**Chip group order = Responded → Busy → Ignored.** Maps to severity (positive → neutral → negative). Aligns with reading order; the most actionable group (Ignored) is rightmost / last, drawing the eye via reading-flow rather than relying on color alone.

## R4. Princ. VI evaluation

**No new dependencies.** Every operation is stdlib JavaScript / DOM:

| Operation | Implementation |
|---|---|
| Chip classification | Set difference `Set([...allies]) − responded − busy` |
| Kills top-N sort | `Array.prototype.sort` + `Array.prototype.slice(0, 10)` |
| Evidence-ref dispatch | switch statement on `kind` |
| Smooth scroll | `Element.scrollIntoView` |
| Highlight pulse | CSS class toggled via React state + `setTimeout` |

The Princ. VI evaluation table is degenerate. Documented for the auditing pass; no library was considered, no library was rejected.

## R5. Library considered and rejected

For completeness, libraries that could plausibly enter scope:

| Candidate | Domain | Rejected because |
|---|---|---|
| `framer-motion` | Highlight animation | The pulse is a single CSS transition triggered by class toggle; importing a 50KB animation library for one usage violates Princ. VI YAGNI. |
| `react-virtual` / `react-window` | Kills list virtualization | Top-N=10 has zero rendering cost; virtualization is solving a problem that doesn't exist. |
| `radix-ui` / `headlessui` | Accordion / disclosure pattern | Native `<details>`/`<summary>` HTML elements provide the same semantics with zero deps. |
| `react-use` | `useTimeout` hook | One inline `useEffect` does the same. Adding a utility-hook library for one usage is over-engineering. |

If a future feature ever needs framer-motion AND a heavy disclosure library AND a virtualization library AND a hook utilities collection, the evaluation is re-run from fresh evidence. Today: nothing.

## R6. Out-of-scope decisions

These came up during scoping but are deferred:

- **Map-tab integration.** Centroids panel renders raw coordinates; on-map visualization is the future Map-tab feature's job.
- **Per-handle item-id resolution.** Item names continue as `UNKN`. Feature 008.
- **Per-handle owner tracking for losses.** Per-player TEI continues as `null`. Feature 010.
- **Spell-cast on-ally detection.** Documented Phase 0 outcome stands. Feature 011 (or never).
- **Keyboard navigation.** Mouse-only in v1. Accessibility polish belongs in a dedicated feature.
- **Persistent expansion state.** No `localStorage`. Same as 005 / 006.
- **Cross-replay comparison.** Same as 003–006 — per-replay only.
