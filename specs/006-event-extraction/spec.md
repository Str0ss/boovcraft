# Feature Specification: Narrative Event Extraction

**Feature Branch**: `006-event-extraction`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "Event extraction analysis layer that derives narrative game events (creeping departures, expo placements, base incursions, joint engagements, ally-zone creeping, idle periods, building rebuilds, tech milestones, tower rushes, hero TPs, production stalls, intensity peaks) from replay data so an LLM can write a human-readable game summary. The current processor analysis output strips action coordinates; this feature extends the processor to retain (x, y) on timed actions and on production.*.order entries (additive contract change), then adds a new analysis stage that emits a per-replay events document. Methods are pandas + scikit-learn DBSCAN for spatial/temporal clustering; thresholds are derived per-replay from observed building-placement spread (no map metadata available). The output is a separate document shape consumed by the visualizer and downstream LLM tooling. All claims must be hedged because we never observe unit deaths, gold, or vision — only player input."

## Clarifications

### Session 2026-05-07

- Q: Should resource transfers (gold/lumber sent ally→ally) be surfaced as an event kind, or remain only in the analyzer output? → A: Surface as a 13th event kind. Every transfer becomes an event; consecutive transfers between the same sender/receiver pair separated by small inter-transfer gaps are clustered into a single "transfer burst" event.
- Q: How is the events list laid out in the document — flat chronological, kind-keyed, or both? → A: Flat chronological array under a single well-known key. Each event carries its `kind` as a discriminator field. Order is by event start time with ties broken by a documented deterministic secondary key.
- Q: Should each event carry a stable identifier, and if so derived how? → A: Yes — every event MUST carry a stable, content-derived identifier computed from its kind, start time, and sorted participant ids (and any further kind-specific fields needed to disambiguate). The derivation rule is documented in the data-shape document. Identifiers are stable across re-runs and across non-breaking spec revisions; consumers can use them for citation, deduplication, and cross-document references.
- Q: Where do per-replay extractor state (thresholds, fallback rules fired, event counts) and tooling metadata (extractor version) live in the events document? → A: In a top-level `diagnostics` block that mirrors the analyzer's existing `diagnostics` pattern. It MUST contain at least the extractor version, the per-player home derivation method (primary or named fallback), the per-replay threshold values used, and per-kind event counts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A Replay Becomes A Narrative-Ready Event Stream (Priority: P1)

An analyst — human or LLM — points a tool at a replay's analysis output and receives a single events document that lists what happened during the match in human terms: when each player went out to creep, when expansions were placed, when bases were entered, when teammates fought together, when somebody sat idle, when buildings were rebuilt after presumed loss, when tech milestones were reached, when a tower rush went up, when a hero teleported, when production stalled, and when overall game intensity peaked. Each event carries an in-game timestamp, the players involved, a short machine-readable type label, and any quantitative parameters needed to talk about it concretely (durations, distances, counts). The analyst never has to read raw command streams, compute clusters by hand, or guess what the data implies.

**Why this priority**: This is the entire point of the feature. The Parser already preserves the replay byte-for-byte and the Analyzer already produces a structured per-player view, but neither answers the question "what *happened* in this game?" in a form a non-specialist or an LLM can narrate without reasoning over thousands of low-level actions. Without this story, every downstream summarization tool has to redo the same spatial-temporal inference work, badly. With this story, a downstream consumer can read the events document top-to-bottom and write match commentary directly.

**Independent Test**: Run the events extractor against the committed analysis fixture (`sample_replays/base_1.w3g.analysis.json`) and confirm that (a) a single events JSON document is written to a predictable location, (b) the document contains at least one event of each kind that the underlying replay actually exhibits (e.g., the 4v4 match must show creeping departures, expos, joint engagements), (c) every event is timestamped in in-game milliseconds and references the players it concerns by id, and (d) a reader who knows nothing about the WC3 action stream can describe what happened from the events document alone.

**Acceptance Scenarios**:

1. **Given** an analyzer-output file written by the Processor layer (which now includes per-action coordinates per User Story 2), **When** the events extractor is run against it, **Then** a single events JSON document is written to disk and the process exits successfully.
2. **Given** the written events document, **When** a consumer opens it, **Then** they can locate, for each event, a stable type label (one of the recognized event kinds), an in-game start time, an end time when applicable, the player or players involved, the team affiliations of those players, and any kind-specific parameters (e.g., distance from home for an expo, intensity score for a peak, duration in milliseconds for an idle period).
3. **Given** a replay in which a particular event kind cannot occur or simply did not occur (e.g., `base_2.w3g`'s 3v3 may not contain a tower rush), **When** the events extractor runs, **Then** the document still exits successfully, the absent kind is represented by an empty list (not a missing key), and no inference is fabricated to fill the gap.
4. **Given** the events document, **When** an LLM is prompted with it and asked to summarize the match, **Then** every claim it can ground in a specific event references that event's timestamp and participants without consulting any other artifact.
5. **Given** an analyzer-output file that predates User Story 2's coordinate-retention change (i.e., an older `*.analysis.json` produced before this feature shipped), **When** the events extractor is run against it, **Then** the process exits with a clear diagnostic identifying the missing coordinate fields and writes no partial output.

---

### User Story 2 — Action Coordinates Survive The Analyzer Layer (Priority: P1)

A developer opens the analyzer's output for any replay and finds, for every timed action and for every entry in the production history (buildings, units, upgrades, items, where the action carried a position in the underlying replay), the in-game `(x, y)` coordinate at which that action occurred. Coordinates are present alongside the existing fields, not replacing them; consumers that ignore coordinates continue to work unchanged.

**Why this priority**: Every spatial event the feature claims to extract — creeping departures, expos, base incursions, joint engagements, ally-zone creeping, building rebuilds, tower rushes — is impossible without coordinates. Today the Analyzer strips them. This story is the precondition that unblocks User Story 1, but it also has independent value: a future Map tab in the Visualizer (already foreshadowed in features 003 and 005) and any other spatial analysis tool can reach for the analyzer output without having to re-parse the replay. It earns a P1 alongside US1 because the events document cannot be produced at all until this lands.

**Independent Test**: Run the existing analyzer against `sample_replays/base_1.w3g.json` and `sample_replays/base_2.w3g.json` and inspect the written `*.analysis.json` documents. Confirm that (a) timed-action entries that originate from replay actions carrying a position now expose those coordinates, (b) production-order entries similarly expose coordinates when the underlying action was a building placement or a positioned ability, (c) entries originating from coordinate-less actions (e.g., hotkey assignments, escape presses, group selections) continue to omit coordinates without error, and (d) every other field of the analyzer output is byte-identical to the pre-change output (i.e., the change is strictly additive on the contract).

**Acceptance Scenarios**:

1. **Given** the existing analyzer-output contract, **When** the analyzer is re-run after this change, **Then** every previously-emitted field is still present with the same value, and new optional coordinate fields appear on entries whose underlying action carried a position.
2. **Given** a timed action that originates from a replay action without a position (e.g., a hotkey assignment), **When** the analyzer emits it, **Then** the coordinate fields are absent (not zero, not a null sentinel) and the entry is otherwise unchanged.
3. **Given** a production-order entry for a building, **When** the analyzer emits it, **Then** the coordinate of the placement is present.
4. **Given** the analyzer's data-shape document (`processor/DATA.md`), **When** this change ships, **Then** the document records the new optional coordinate fields, the categories of actions for which they appear, and the unit/coordinate-system semantics.
5. **Given** the existing visualizer (feature 005), **When** it reads an analysis file produced after this change, **Then** it functions exactly as before — coordinate fields it does not consume are simply ignored.

---

### User Story 3 — The Events Document Is Self-Describing (Priority: P2)

A developer building a consumer of the events document — a visualizer panel, an LLM-prompting harness, a sanity-check script — needs to know exactly which event kinds the extractor emits, what fields each kind carries, what the kind-specific parameters mean, and what assumptions or hedges the extractor applies before claiming an event happened. They learn all of this from a documentation artifact in the repository, not by reading the extractor's source code or running it on a fixture.

**Why this priority**: The events document is a contract between this feature and every downstream consumer. The Parser ships `parser/DATA.md`, the Analyzer ships `processor/DATA.md`, and a third on-disk artifact deserves the same treatment. It is not strictly required for the first end-to-end run (US1 produces *something* readable on its own), so it ranks below P1, but it is required before this feature is considered complete enough to be relied on outside the immediate author's head.

**Independent Test**: Hand the events-document data-shape document to a developer who has never seen the extractor's output. Ask them to describe how they would render a "joint engagement" event in a visualizer or how they would phrase a "tower rush" event in a natural-language summary. They should be able to answer without opening source code or sample output.

**Acceptance Scenarios**:

1. **Given** the events-document data-shape document, **When** a developer reads it, **Then** for every event kind and every kind-specific field they can identify the field's name, type, meaning, units (where applicable), and the bounds within which the value makes sense.
2. **Given** an event kind that carries an inherent uncertainty hedge (e.g., "this is consistent with a tower rush but cannot be confirmed because we do not observe construction completion"), **When** a developer reads the document, **Then** the hedge and its rationale are stated alongside the event kind, not buried in source code.
3. **Given** a change to the events document's shape, **When** the change lands, **Then** the data-shape document is updated in the same change.

---

### User Story 4 — Every Inferred Claim Is Hedged Honestly (Priority: P2)

A developer or LLM consuming the events document never sees a claim that overstates what the data actually supports. The extractor knows that it does not observe unit deaths, gold or lumber balances, fog of war, or any in-game state beyond the player's own input stream. When it reports an event whose interpretation depends on inference (e.g., a "rebuild" assumes the prior building was destroyed; a "joint engagement" assumes the simultaneous nearby clicks of teammates were combat-related), it labels that inference explicitly and provides the underlying observable signal so a downstream consumer can decide whether to trust it.

**Why this priority**: Without this discipline, the events document looks authoritative ("Player X attacked Player Y at 12:34") when the data only supports a softer claim ("Player X clicked inside Player Y's base for ~30s starting at 12:34, consistent with an attack"). An LLM prompted with overstated events will confabulate confidently. The hedging discipline is the single non-obvious quality bar that distinguishes this feature from a naive event labeler. It is P2 (not P1) because US1 produces useful events even with crude hedging — but the hedging is what makes the output trustworthy at scale.

**Independent Test**: For each of the 13 recognized event kinds, inspect a generated event of that kind and confirm that (a) the event's natural-language label is consistent with what the underlying signal can support, (b) any inferred component (death, attack, retreat, harassment) is named explicitly as inference rather than fact, and (c) the underlying observable fields (timestamps, click coordinates, click counts, distances, idle gaps) are exposed in the event so a skeptical reader can audit the call.

**Acceptance Scenarios**:

1. **Given** a "building rebuild" event, **When** a consumer inspects it, **Then** the event names the original placement, the rebuild placement, the time gap between them, and the spatial bucket within which they were considered "the same location" — without claiming the original was destroyed in combat or by whom.
2. **Given** a "joint engagement" event, **When** a consumer inspects it, **Then** the event names the participants, the spatial centroid, the time window, the count of clustered actions, and the cluster's tightness — without claiming a winner or that combat occurred.
3. **Given** a "tower rush" event, **When** a consumer inspects it, **Then** the event names the placing player, the placement coordinate, the distance to the nearest opponent's home, the distance to the placer's own home, and the placement time — flagged as "consistent with a tower rush" rather than as a confirmed completion.
4. **Given** any event kind that requires a per-replay threshold (e.g., a "home radius" derived from observed building spread), **When** a consumer inspects the event, **Then** the threshold's value as actually used for that replay is included so the call can be re-derived or second-guessed.

---

### Edge Cases

- **Analyzer-output file does not exist or is unreadable**: Events extractor exits non-zero with a clear message; no events file is produced.
- **Analyzer-output file exists but is not valid JSON**: Events extractor exits non-zero with a clear message; no events file is produced.
- **Analyzer-output file is from a build before US2 shipped (no coordinate fields)**: Extractor exits non-zero with a clear message identifying the missing fields and citing the version the consumer needs.
- **Replay is extremely short (e.g., a few seconds, immediate disconnect)**: Extractor still produces a valid events document with empty arrays for kinds whose minimum-duration or minimum-evidence thresholds were not met. It does not raise.
- **Replay has only a single non-observer player or only observers**: Extractor produces a valid events document with empty arrays for kinds that require ≥ 2 participants (joint engagements, ally-zone creeping, base incursions). Single-player kinds (idle, rebuilds, expo, tech milestones) still populate.
- **A player's first 60 seconds contain no building placements (Random race spawning in, AFK opener)**: Extractor falls back to a documented secondary heuristic for that player's home location, records which heuristic was used, and continues.
- **Two events of the same kind overlap in time and space (e.g., two consecutive joint-engagement clusters whose participants and centroids would naturally merge)**: The extractor reports them as a single event with the merged time window, not as duplicates. The merge rule is recorded in the data-shape document.
- **An event's confidence-supporting threshold is barely met (e.g., a creeping departure that just grazes the home-radius boundary)**: The extractor still emits the event but exposes the ratio of the underlying signal to the threshold so a consumer can downweight borderline calls.
- **Coordinate units in the underlying replay differ from what the extractor expected**: The extractor records the per-replay derivation of all spatial thresholds (home radius, engagement clustering ε) so that misaligned units produce visibly anomalous threshold values rather than silently wrong events.
- **Resource-transfer bursts straddle a quiet gap**: When transfers between the same sender/receiver pair are separated by a gap exceeding the burst-clustering threshold, the extractor emits two separate transfer events rather than one merged event, and records the threshold value used in each emitted event.
- **Output file already exists at the target location**: Extractor overwrites it deterministically (matching the Parser and Analyzer layers' behavior).
- **Output location is not writable**: Extractor exits non-zero with a clear message.

## Requirements *(mandatory)*

### Functional Requirements

#### Analyzer-layer changes (User Story 2)

- **FR-001**: The Processor's existing analysis stage MUST retain the `(x, y)` coordinate of every timed action whose underlying replay action carries a position, attached to the existing timed-action entry.
- **FR-002**: The Processor's existing analysis stage MUST retain the `(x, y)` coordinate of every production-order entry (buildings, units, upgrades, items) whose underlying replay action carries a position, attached to the existing order entry.
- **FR-003**: The coordinate fields added by FR-001 and FR-002 MUST be optional: timed-action and production-order entries whose underlying actions do not carry a position MUST continue to be emitted without the coordinate fields, and consumers that do not read the coordinate fields MUST continue to function unchanged.
- **FR-004**: All other fields of the existing analyzer output MUST be unchanged in name, type, position, and value. The change is strictly additive on the existing contract.
- **FR-005**: `processor/DATA.md` MUST be updated in the same change to record the new coordinate fields, the action categories that carry them, the units they are reported in, and the source field in the parser output from which each is derived.

#### Events-stage core (User Story 1)

- **FR-006**: The system MUST accept a path to a single analyzer-output file (the JSON document produced by the Processor's analysis stage and updated per FR-001..FR-004) as its input.
- **FR-007**: The system MUST produce a single events JSON document per invocation, written to a deterministic location derived from the input path so that downstream consumers can locate it without extra configuration.
- **FR-008**: The events document MUST be a separate on-disk artifact from the analyzer output. The events stage MUST NOT modify or rewrite the analyzer output.
- **FR-009**: The events document MUST contain match-level metadata sufficient to identify the replay it derives from (at minimum: a stable parser id, the in-game duration in milliseconds, the players' ids and team ids), so the consumer is not obligated to re-open the analyzer output to use the events. The events themselves MUST be emitted as a single flat array under one well-known top-level key, with each event carrying a `kind` discriminator field. The array MUST be ordered chronologically by event start time, with ties broken by a deterministic secondary key documented in the data-shape document. Each event MUST also carry a stable content-derived identifier computed from its kind, start time, sorted participant ids, and any further kind-specific fields required to disambiguate two events that would otherwise collide; the derivation rule MUST be recorded in the data-shape document. The events document MUST also contain a top-level `diagnostics` block mirroring the existing analyzer-output `diagnostics` pattern, containing at minimum: the extractor version, per-player home derivation method (primary or named fallback), the per-replay threshold values used, and per-kind event counts. The data-shape document MUST enumerate the diagnostics block's full field list and any volatile fields it contains.

#### Recognized event kinds (User Story 1)

The events document MUST recognize the following event kinds. Each kind has a stable type label, a participant set, an in-game time anchor (start, optionally end), and kind-specific parameters defined in the data-shape document (User Story 3).

- **FR-010 (Idle period)**: A continuous span of time during which a single player issued no input. The event MUST report start time, end time, duration, and the player.
- **FR-011 (Building rebuild)**: A second or subsequent placement of the same building entity by the same player at approximately the same coordinate. The event MUST report the original placement time and coordinate, the rebuild placement time and coordinate, the time gap, and the spatial bucket size used to deem the two placements colocated.
- **FR-012 (Tech milestone)**: A first-occurrence-per-player marker for any of: tier-2 main hall, tier-3 main hall, altar/equivalent, race-specific key tech buildings, and major upgrade research starts. The event MUST report the milestone label, the player, and the in-game time.
- **FR-013 (Expo placement)**: A main-hall placement by a player at a coordinate further than that player's home radius from their home. The event MUST report the player, the placement time, the placement coordinate, the home coordinate, the home radius, and the distance from home.
- **FR-014 (Creeping departure)**: A transition of a player's recent-action centroid from inside their home radius to outside it, sustained for a documented minimum duration. The event MUST report the player, the start time, the destination centroid, and the distance from home at the destination.
- **FR-015 (Tower rush, candidate)**: A defensive or offensive tower placement by a player at a coordinate closer to an opponent's home than to the placer's own home. The event MUST report the placer, the placement time, the placement coordinate, the distance to each home, and the opponent home it appears to threaten. The event label MUST clearly mark this as a candidate inference rather than a confirmed completion.
- **FR-016 (Base incursion)**: A span of action coordinates by a player that fall inside an opponent's home radius. The event MUST report the player, the opponent whose base was entered, the start and end of the span, the count of clustered actions inside the opponent's radius, and the centroid of those actions.
- **FR-017 (Ally-zone creeping)**: A span of action coordinates by a player that fall inside an *ally's* home-radius band but outside the player's own band, with action density consistent with combat (kind-specific minimum). The event MUST report the player, the ally whose zone was entered, the start and end of the span, the action count, and the centroid.
- **FR-018 (Joint engagement)**: A spatial-temporal cluster of actions (per kind-specific clustering parameters) involving two or more teammates. The event MUST report the participants, the cluster's time window, the cluster's spatial centroid, the action count, the per-participant action breakdown, and the cluster tightness.
- **FR-019 (Hero teleport / staff usage)**: A timed item-use action whose item id matches the documented set of teleport items (Town Portal, Staff of Teleportation, etc.). The event MUST report the player, the hero (when attributable), the time, and the originating coordinate.
- **FR-020 (Production stall)**: A continuous span during which a player issued zero production-order entries despite continuing to issue any actions. The event MUST report the player, the start time, the end time, the duration, and the player's input rate during the stall.
- **FR-021 (Intensity peak)**: A local maximum in a per-team or all-player aggregate input-rate curve, exceeding documented thresholds. The event MUST report the time of the peak, the participating team(s) (or "all"), the peak value, and the baseline against which it is a peak.
- **FR-022 (Resource transfer)**: A gold or lumber transfer from one player to an ally. Consecutive transfers between the same sender and receiver separated by gaps below a documented threshold MUST be clustered into a single "transfer burst" event; isolated transfers are emitted as singleton events of the same kind. The event MUST report the sender, the receiver, the start time, the end time when clustered, the count of transfers in the burst, the total gold transferred, the total lumber transferred, and the inter-transfer-gap threshold used to define the burst.

#### Hedging discipline (User Story 4)

- **FR-023**: Every event kind whose interpretation requires inference (FR-015 tower-rush candidacy, FR-016 base incursion, FR-017 ally-zone creeping, FR-018 joint engagement, FR-021 intensity peak) MUST carry an explicit, machine-readable label distinguishing the observable signal from the inferred meaning.
- **FR-024**: Every event whose generation depended on a per-replay threshold (home radius, engagement-cluster radius, idle-gap minimum, transfer-burst-gap, etc.) MUST expose the threshold's value as actually used for that replay, alongside the event.
- **FR-025**: The events document MUST NOT report any event whose evidence is purely speculative — every emitted event MUST be backed by at least one observable signal (a timed action, a production-order entry, a chat message, or a resource transfer) referenced in the event's body or derivable from the supplied parameters.
- **FR-026**: The events document MUST NOT claim outcomes the data does not support. Event labels and field names MUST stay in the vocabulary of player input — words like "killed", "destroyed", "stole", and "won the fight" MUST NOT appear as factual claims.

#### Per-replay threshold derivation

- **FR-027**: All spatial thresholds (home location, home radius, engagement-cluster radius, rebuild-bucket size, etc.) MUST be derived from the data of the replay being processed, not hardcoded in absolute map units. The derivation rule for each threshold MUST be documented in the data-shape document.
- **FR-028**: When a replay does not contain enough signal to derive a threshold (e.g., a player placed no buildings in their first 60 seconds), the extractor MUST apply a documented fallback rule and record which rule was applied for that replay.

#### Documentation (User Story 3)

- **FR-029**: A data-shape document for the events JSON output MUST be written in the same change (a sibling of `parser/DATA.md` and `processor/DATA.md`).
- **FR-030**: The data-shape document MUST list every recognized event kind, every field on every kind, the field's type, the field's units (where applicable), and any per-replay threshold the kind depends on.
- **FR-031**: The data-shape document MUST state explicitly, in prose, that the extractor does not observe unit deaths, gold, lumber, food, vision, or build completion — and MUST list which event kinds depend on inferring around those gaps.
- **FR-032**: Any future change to the events document's shape MUST update the data-shape document in the same change.

#### Operational behavior

- **FR-033**: The events extractor MUST exit non-zero with a clear diagnostic and write no partial output when its input is missing, unreadable, not valid JSON, or does not match the post-FR-001..FR-004 analyzer-output contract.
- **FR-034**: The events extractor MUST overwrite an existing output file at the target location deterministically (matching the Parser and Analyzer layers' behavior).
- **FR-035**: The events extractor MUST be deterministic for a given input: re-running it on the same analyzer-output produces a byte-identical events document, modulo any volatility documented in the data-shape document.
- **FR-036**: The events extractor MUST consume only the analyzer-output file as input; it MUST NOT re-parse the original `.w3g` file or read the parser-layer JSON.

### Key Entities

- **Coordinate-bearing timed action**: An entry on the analyzer output's per-player timed-action stream, augmented per FR-001 with `(x, y)` when the underlying replay action carried a position. Existing fields (time, category, etc.) unchanged.
- **Coordinate-bearing production-order entry**: An entry on the analyzer output's per-player production-order stream (buildings, units, upgrades, items), augmented per FR-002 with `(x, y)` when applicable. Existing fields (time, entity reference, etc.) unchanged.
- **Player home**: Per-player derived `(x, y)` representing the inferred starting location, computed primarily from early building placements per FR-027, with a documented fallback per FR-028.
- **Home radius**: Per-player derived scalar distance defining the "near home" band, computed from the spread of that player's early building placements per FR-027.
- **Event**: An object in the events document representing one recognized occurrence. Carries a stable content-derived identifier, a stable `kind` label, an in-game time anchor, the participants, kind-specific parameters, and the per-replay thresholds it depended on.
- **Events document**: The on-disk JSON artifact emitted per replay by the extractor, containing match-level metadata, a single flat chronological array of events, and a top-level `diagnostics` block mirroring the analyzer's pattern. Each event in the array carries a stable content-derived identifier and a `kind` discriminator and is ordered by start time per FR-009.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An LLM prompted with the events document for `sample_replays/base_1.w3g` produces a 6–10 sentence match summary that names at least one expo, one creeping departure, one joint engagement, and one idle period — without consulting the analyzer output, the parser output, or the replay.
- **SC-002**: For both committed fixture replays, the events document contains a non-empty list for every event kind that the underlying replay actually exhibits, with no fabricated events for kinds that did not occur.
- **SC-003**: A reviewer reading any single emitted event of an inferred kind (tower-rush candidate, base incursion, ally-zone creeping, joint engagement, intensity peak) can identify, from the event alone, both the observable signal and the inferred interpretation — without reading source code.
- **SC-004**: A reviewer can trace any per-replay threshold value (home radius, cluster radius, idle minimum) used by the extractor for either fixture replay back to a documented derivation rule and recompute it from the analyzer output by hand.
- **SC-005**: The post-FR-001..FR-004 analyzer output is byte-identical to the pre-change analyzer output on every field that existed before, on both committed fixtures (modulo the additive coordinate fields).
- **SC-006**: Re-running the events extractor on the same analyzer-output file produces a byte-identical events document on every run.
- **SC-007**: A developer who has never seen the extractor's output can, from the events data-shape document alone, describe how to render or narrate every recognized event kind.
- **SC-008**: The events document contains zero claims using outcome vocabulary the data does not support ("killed", "destroyed", "stole", "won"). Verifiable by string search over the document for these forbidden tokens used as factual labels.

## Assumptions

- **The events stage is a new Processor-layer entry point**, not a modification of the existing `processor/analyze.py`. It mirrors the existing analyzer's CLI shape (one input path, deterministic output location, exit-code semantics). This preserves the principle that each stage's input and output is a JSON file on disk (constitution Principle I).
- **The events document is a separate file, not embedded in the analyzer output.** A separate artifact keeps each layer's contract narrow, lets consumers fetch only what they need, and lets the events shape evolve independently of the analyzer shape. The location is a sibling of the analyzer output (e.g., `<name>.w3g.events.json` next to `<name>.w3g.analysis.json`).
- **The events stage consumes the analyzer output, not the parser output.** This inherits the entity-name decoration and the cleaner contract. The parser-output JSON remains untouched per constitution Principles I and II.
- **No visualizer changes ship in this feature.** The events document is produced and documented so that a future feature can wire it into the Visualizer (e.g., a "Story" tab or annotations on the existing timelines). Visualizer consumption is a deliberate follow-up.
- **Per-replay threshold derivation uses building placements as the primary signal**, falling back to early-action centroids when building data is insufficient. The exact derivation formulas are a plan/implementation detail, but the *principle* — derived per-replay, not hardcoded — is a requirement (FR-027).
- **Coordinate units and origin** are inherited from whatever w3gjs exposes through the parser; the extractor does not transform coordinates and does not assume a particular map size. Thresholds derived per-replay (FR-027) absorb the unit choice.
- **Hero attribution for teleport events** is best-effort: when the underlying item-use action does not unambiguously identify the casting hero, the event records the player and the time without naming the hero, and notes the attribution gap.
- **All thirteen event kinds** are in scope for this feature's first release. The plan layer may phase them, but the spec recognizes all thirteen as required output (FR-010..FR-022).
- **Testing follows constitution Principle IV**: tests exercise the two committed fixture replays end-to-end. The extractor's pure helper functions (clustering, threshold derivation, event aggregation) are testable in isolation; their inputs are derived from the fixtures, not hand-rolled.
