# Feature Specification: Replay Parser

**Feature Branch**: `001-replay-parser`
**Created**: 2026-04-21
**Status**: Draft
**Input**: User description: "The first and essential feature of the project is the ability to parse replays. The replays must be parsed by the node script using w3gjs library. The resulting data must be stored for further processing. The parse result must contain ALL data from the replay, and must NOT contain any analysis (e.g. APM calculations). Our goal is to write the w3gjs-based parser once and do not modify it after that - as all available data is extracted, only downstream analysis script must be modified. Also, the doc describing the data structure must be composed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract Complete Raw Data From A Replay (Priority: P1)

A developer working on replay analysis needs a complete, lossless
representation of a single Warcraft III replay file, saved to disk in a
format their analysis tooling can read without having to touch a binary
parser themselves.

**Why this priority**: This is the foundation of the entire project. No
downstream analysis, aggregation, or visualization can happen until a
replay's raw contents are available as structured data. Every other
feature in the roadmap consumes this output.

**Independent Test**: Point the parser at any supported `.w3g` file and
confirm that (a) a structured data file is produced at a predictable
location, and (b) every field the canonical parsing library exposes for
that replay appears somewhere in that file, with no analytical
transformations applied.

**Acceptance Scenarios**:

1. **Given** a valid `.w3g` replay file, **When** the parser is run
   against it, **Then** a single structured data artifact is written to
   disk and the process exits successfully.
2. **Given** the written artifact, **When** a consumer opens it,
   **Then** every data element that exists in the replay (headers,
   metadata, players, chat, actions, timing, map info, all events) is
   present verbatim, without any derived or aggregated values (no APM,
   no counts, no summaries).
3. **Given** an invalid or unreadable replay file, **When** the parser
   is run, **Then** the process exits with a non-zero status, emits a
   clear error message, and writes no partial output artifact.

---

### User Story 2 - Understand The Parsed Data Structure Without Running The Parser (Priority: P2)

A developer planning a new analysis needs to know what fields are
available in the parser's output — their names, shape, and meaning —
without having to run the parser, open a sample output, or read the
parser's source code.

**Why this priority**: Documentation of the output contract is what
makes the "write the parser once, only modify analysis downstream"
promise credible. Without it, every new analysis task starts with
reverse-engineering the output. It is not strictly required for a
first end-to-end run, so it ranks below P1, but it is required before
the parser is considered complete.

**Independent Test**: Hand the documentation to a developer who has
never seen the parser output. Ask them to sketch how they would access
three specific pieces of information (e.g., a player's race, the chat
messages, the map file name). They should be able to do so from the
document alone.

**Acceptance Scenarios**:

1. **Given** the documentation document, **When** a developer reads it,
   **Then** they can identify the location (path within the output) of
   every top-level and nested field that the parser produces, along
   with its type and a short description of its meaning.
2. **Given** a change to the parser's output shape, **When** the
   change lands, **Then** the documentation is updated in the same
   change to reflect the new reality.

---

### User Story 3 - Parser Remains Unchanged As Analyses Evolve (Priority: P3)

A developer adding a new kind of analysis (for example, economy
tracking, hero-ability timing, or team composition) should be able to
build that analysis entirely downstream, without editing the parser.

**Why this priority**: This validates the architectural intent rather
than delivering user-visible behavior on day one. It is a property
observed over time, not a single demoable action.

**Independent Test**: Track parser-file changes across the first
several downstream analyses. New analyses that rely only on data
already present in a replay MUST NOT require any parser-layer edit.

**Acceptance Scenarios**:

1. **Given** a new analysis idea that depends on data already present
   in the replay file, **When** the analysis is implemented, **Then**
   the change is isolated to the downstream processing layer and the
   parser code is untouched.
2. **Given** an analysis idea that genuinely depends on data the
   parser does not currently emit, **When** the gap is investigated,
   **Then** it is resolved by capturing more of what the canonical
   parsing library already exposes — not by adding analytical logic
   to the parser.

---

### Edge Cases

- **File does not exist or is unreadable**: Parser exits non-zero with
  a clear message; no output file is produced.
- **File exists but is not a valid `.w3g` replay** (e.g., wrong format,
  empty, corrupt header): Parser exits non-zero with a clear message;
  no output file is produced.
- **Replay is valid but truncated** (common when a game crashed mid-
  match): Parser produces output covering everything that could be
  read, and clearly signals that the replay was partial — either by
  surfacing the underlying library's partial-read indication in the
  output, or by exiting non-zero. The behavior MUST be deterministic
  and documented.
- **Replay is from a newer game version than the parsing library
  supports**: Parser exits non-zero with a clear message that
  distinguishes "unsupported version" from "corrupt file".
- **Output file already exists at the target location**: Parser
  overwrites it deterministically (no prompt, no rename, no error).
- **Parser output location is not writable** (permissions, read-only
  disk): Parser exits non-zero with a clear message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a path to a single `.w3g`
  Warcraft III replay file as its input.
- **FR-002**: The system MUST extract every piece of data that the
  canonical parsing library exposes for that replay — headers,
  metadata, player records, chat, map details, action/event streams,
  timing information, and any other surfaced fields — with no
  omissions.
- **FR-003**: The system MUST NOT compute, include, or embed any
  analytical or derived values in its output. No APM, no action
  counts, no win/loss inference, no economy estimates, no summaries,
  no aggregations. Only data actually present in the replay file.
- **FR-004**: The system MUST persist its output as a single
  structured data file, written to a deterministic location derived
  from the input file path so that downstream processing can locate
  it without extra configuration.
- **FR-005**: The system MUST exit with a non-zero status and emit a
  clear diagnostic message when parsing fails. No partial output file
  MUST be written in that case.
- **FR-006**: The system MUST overwrite an existing output file at
  the target location without prompting.
- **FR-007**: A documentation artifact MUST exist alongside the
  parser that describes the shape of the output: for every top-level
  and nested field, its name, type, and meaning. This document MUST
  be updated whenever the output shape changes.
- **FR-008**: The output format MUST be consumable by the downstream
  processing layer (a separate runtime) without any runtime-specific
  serialization concerns — i.e., only portable, widely-supported
  data types.
- **FR-009**: The parser, once it extracts everything the canonical
  parsing library exposes, MUST NOT require modification in order to
  support new downstream analyses that rely on data already present
  in the replay.

### Key Entities

- **Replay file**: A Warcraft III `.w3g` replay, produced by the
  game client. Binary, version-specific. The sole input to this
  feature.
- **Parse output**: A single structured data artifact persisted to
  disk. Contains the complete set of fields the canonical parsing
  library exposes for a given replay, and nothing derived.
- **Structure documentation**: A human-readable document describing
  the shape of the parse output — its fields, types, and semantics.
  Serves as the contract for downstream consumers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the parser on any supported `.w3g` file
  produces a valid, non-empty output artifact on disk in under
  5 seconds for a typical 1 MB replay on commodity hardware.
- **SC-002**: For any given replay, 100% of the fields that the
  canonical parsing library exposes for that replay appear in the
  parse output — verified against a set of real replay fixtures by
  diffing the library's in-memory output against the persisted
  artifact.
- **SC-003**: A developer unfamiliar with the parser can, using only
  the structure documentation, locate the path to any field they
  need for a new analysis in under 2 minutes per field — measured by
  spot-checking against randomly selected fields during review.
- **SC-004**: After the parser is declared complete, subsequent
  downstream analysis features (measured over the first 5 such
  features delivered) introduce zero changes to parser-layer files.
  Any exception MUST be traced to a genuine gap in raw data
  extraction, not to analytical logic leaking upward.
- **SC-005**: Every parse failure produces a diagnostic message that
  a developer can act on within 1 minute (identifying which file,
  why, and what to do next) — verified by reviewing captured error
  messages across the edge-case set.

## Assumptions

- **Parsing library is fixed**: The canonical parsing library is
  `w3gjs`. This is a project-wide constraint (see constitution,
  Principle II), not a per-feature decision. The parser consumes
  whatever fields w3gjs exposes; future library upgrades can widen
  the output without requiring parser logic changes.
- **Single-file invocation**: Each parser run processes one replay.
  Batch, streaming, or watch-mode invocation is out of scope for
  this feature and will be layered on externally if needed.
- **Output location**: The parse output lives at a deterministic
  path next to the input (e.g., `<replay-path>.json`), unless a
  future feature introduces a configurable location. Downstream
  tooling locates output by convention.
- **Output format**: A single JSON document per replay, chosen for
  universal readability across the project's other runtimes. This
  is implied by FR-008.
- **Re-parsing is idempotent**: Running the parser twice on the
  same replay produces byte-identical output (modulo non-
  deterministic fields in the library itself, which are
  documented).
- **Documentation lives in-repo**: The structure documentation is a
  Markdown file committed alongside the parser code, reviewed in
  the same pull requests, not an external wiki.
- **Truncated-replay behavior is inherited**: How partial replays
  are reported follows what the canonical library does; this
  feature does not add its own partial-recovery heuristics.

## Out of Scope

- Any form of analysis: APM, action counts, timing analysis, build
  orders, economy, win inference, team composition, summaries.
- Batch processing, directory-walking, or a watch mode.
- A schema validator for the output (the documentation is the
  contract; validation can come later).
- Uploading replays, a web UI, or any user-facing visualization.
- Caching, incremental parsing, or diffing across replay versions.
- Supporting replay formats other than `.w3g` (e.g., StarCraft
  replays).
