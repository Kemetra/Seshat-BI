# Feature Specification: Rule Registry Snapshot Manifest (golden-file rule inventory)

**Feature**: none (no roadmap F-number -- this idea is from the exploratory idea-bank, `docs/roadmap/idea-backlog.md`, scored V8/F8 on the scoring panel, which is "not a roadmap and not a commitment"; promotion + F-numbering is a human decision) | **Spec directory**: `043-rule-registry-snapshot-manifest-golden` (next free on-disk slot -- the create-new-feature script numbers from the current max `042`, not the first gap)

**Feature Branch**: `043-rule-registry-snapshot-manifest-golden` (located via `.specify/feature.json`)

**Created**: 2026-06-29

**Status**: Ratified (Ahmed Shaaban, 2026-06-29)

**Input**: User description: "Rule Registry Snapshot Manifest (golden-file rule inventory)"

**Readiness stage advanced**: none -- this is meta-infrastructure that hardens the static `retail check` gate itself; it does NOT advance any source/table/report readiness stage (Source -> Mapping -> Silver -> Gold -> Semantic -> Dashboard -> Publish). The roadmap states idea-bank items advance no readiness stage. This work adds NO new registered rule and NO new `EXPECTED_RULE_ID`.

## Clarifications

This block records the load-bearing ambiguities. Items marked Principle-V are deliberate
judgment calls the agent did NOT answer (constitution Principle V). At ratification (Ahmed
Shaaban, 2026-06-29) the owner ruled the one open item. Ordinary ambiguities resolved by the
advisor during clarification are recorded under the dated session below.

### Owner judgment call (Principle V -- RESOLVED at ratification, 2026-06-29)

- **[RESOLVED -- Principle V, Ahmed Shaaban 2026-06-29] Roadmap promotion + feature number.**
  RULING (owner, conservative default): **stay spec-only -- NO roadmap F-number assigned.**
  Implement directly from this spec dir; the roadmap remains the human-curated commitment ledger
  and gains no row for this work. This commits nothing additional and is reversible: promotion
  remains available later via the normal spec process.

### Session 2026-06-29

> The advisor recommendations below were integrated into the spec body during clarification
> (highest Impact*Uncertainty first). The Principle-V item above was REFUSED by the agent and
> reserved for the human owner, who ruled it at ratification (now RESOLVED above).

- **Q1 (generator placement) -- RESOLVED.** Should the manifest generator be a `retail` CLI
  subcommand or a standalone `tools/` helper? RECOMMENDED: a `retail` CLI subcommand (e.g.
  `retail manifest`), reusing the existing `cli.py` seam that already imports `all_rules()` and
  already hosts generators (the `gen` DAX subcommand is precedent). Reasoning: it keeps one
  entry point for repo tooling, inherits the package's import-side-effect registration, and adds
  no new top-level module tree. Discriminating constraint (Principle VIII): the generator must
  NOT weaken or enlarge the shipped `retail check` gate surface -- it adds NO new rule and NO new
  `EXPECTED_RULE_ID`; it is a separate subcommand that writes a doc, not a check. Reversible:
  yes (a `tools/` helper could replace it later with no consumer change beyond the invocation).
- **Q2 (snapshot test failure semantics) -- RESOLVED.** When the committed manifest and the
  live `all_rules()` disagree, does the test fail (error) or warn? RECOMMENDED: FAIL CLOSED
  (test asserts equality; drift is a hard test failure that blocks CI). Reasoning: Principle I
  (enforced, not advised) and the idea's whole point -- a golden inventory that retires
  hand-typed counts only has teeth if drift fails. The failure message MUST instruct the
  developer to regenerate the manifest (run the generator) and commit it in the same change.
- **Q3 (manifest field set) -- RESOLVED.** Which fields does each manifest entry carry?
  RECOMMENDED: exactly `id` and `title` from `RegisteredRule` (the only two serializable fields;
  `rule` is a callable). No severity, no family, no count-of-rules literal, no per-table or
  worked-example enrichment (Principle VII / hard rule #7 -- generic only). The manifest is an
  EXACT inventory keyed to code, never a numeric confidence/health score (hard rule #9).
- **Q4 (cross-platform stability) -- RESOLVED.** How is the committed JSON kept stable across
  platforms under `core.autocrlf=true`? RECOMMENDED (Principle IX): the manifest is serialized
  UTF-8 without BOM, with a deterministic stable key order, a trailing newline, and `\n` line
  endings; the snapshot test normalizes line endings (and reads bytes as UTF-8) before comparing
  live-vs-committed, so it cannot flake on Windows CRLF round-trips. A `.gitattributes` entry
  pinning the manifest to `text eol=lf` is in scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drift between code and documented rule inventory is caught automatically (Priority: P1)

A maintainer adds, removes, or renames a governance rule (a `@register(...)` call site) in
`src/retail/rules/`. The committed rule-inventory manifest no longer matches the live registry.
On the next CI run (or local test run), a golden-equality snapshot test fails closed, naming the
exact id/title that drifted and instructing the maintainer to regenerate and commit the manifest.

**Why this priority**: This is the core value -- it makes the documented rule inventory
self-verifying against the code, going UPSTREAM of the existing `EXPECTED_RULE_IDS` id-set guard
by inventorying id+title (not just the id set). It directly retires the hand-typed-count failure
mode that already produced a live defect (stale "26 rules" in the constitution body while the
live registry is 33).

**Independent Test**: Mutate a rule title (or add/remove a `@register`) on a scratch branch
without regenerating the manifest; the snapshot test fails with a clear, actionable message.
Regenerate the manifest; the test passes. Delivers value as a standalone CI guard.

**Acceptance Scenarios**:

1. **Given** the committed manifest matches `all_rules()`, **When** the snapshot test runs,
   **Then** it passes.
2. **Given** a rule title is changed in code but the manifest is not regenerated, **When** the
   snapshot test runs, **Then** it fails closed and the message identifies the drifted id and
   tells the developer to regenerate and commit the manifest.
3. **Given** a rule is added or removed in code but the manifest is not regenerated, **When** the
   snapshot test runs, **Then** it fails closed and lists the missing/unexpected ids.

---

### User Story 2 - A maintainer regenerates the manifest from the live registry (Priority: P2)

A maintainer who has intentionally changed the rule set runs the generator, which reads
`all_rules()` and writes the manifest deterministically (stable key order, UTF-8 no-BOM, `\n`,
trailing newline). The maintainer commits the regenerated manifest in the same change as the rule
edit, and the snapshot test passes.

**Why this priority**: Without a one-command regeneration path, the golden file becomes a chore
and maintainers will hand-edit it (reintroducing the exact drift the feature exists to kill). The
generator is the supported, deterministic way to update the golden file.

**Independent Test**: Run the generator against the current registry; the written file is
byte-identical to the committed manifest (no spurious diff). Run it twice; output is identical
(idempotent).

**Acceptance Scenarios**:

1. **Given** the current registry, **When** the generator runs, **Then** it writes
   `docs/rules/rules-manifest.json` from `all_rules()` (never a hand-typed literal).
2. **Given** the generator runs twice with no code change, **When** the outputs are compared,
   **Then** they are byte-identical (deterministic / idempotent).
3. **Given** the manifest already matches the registry, **When** the generator runs, **Then** the
   file content is unchanged (no diff).

---

### User Story 3 - The documented "N rules" count points at the generated inventory (Priority: P3)

A reader of the docs/constitution finds an authoritative, generated rule inventory rather than a
hand-typed count. The stale "26 rules" occurrences in the live constitution principle body
(`.specify/memory/constitution.md` lines 377 + 381) are corrected to match the live registry and
to reference the manifest as the source of truth; `docs/glossary.md` (already authoritative at 33)
and `docs/roadmap/roadmap.md` count references link to / cite the manifest.

**Why this priority**: It closes the loop -- the defect that motivated the idea (a stale count in
a live principle body) is retired and future counts are sourced from the generated artifact.
Lower priority than the guard itself because the guard prevents recurrence regardless.

**Independent Test**: Grep the live constitution principle body for "26 rules"; after this change
there are zero occurrences in the LIVE body (historical Sync-Impact-comment lines are NOT edited).
The glossary/roadmap count references resolve to the manifest.

**Acceptance Scenarios**:

1. **Given** the stale "26 rules" text on constitution lines 377 + 381, **When** this work lands,
   **Then** those live-body occurrences are corrected and reference the generated manifest.
2. **Given** historical Sync-Impact-comment occurrences of older counts elsewhere in the
   constitution, **When** this work lands, **Then** those historical-record lines are LEFT
   UNCHANGED.

### Edge Cases

- **Empty registry** (no rule submodule imported): the generator must still produce a valid
  (empty-array) manifest and the snapshot test must compare cleanly -- it asserts equality with
  the live registry, whatever its size, never against a baked-in number.
- **Windows CRLF checkout** (`core.autocrlf=true`): the snapshot test normalizes line endings and
  reads UTF-8 before comparing, so a CRLF-on-disk manifest does not cause a false drift failure.
- **BOM accidentally introduced** by an editor: the generator writes UTF-8 *without* BOM; a BOM is
  a malformed manifest and the test (reading explicit UTF-8) surfaces it as a mismatch.
- **Duplicate or non-deterministic ordering** from the registry: the generator imposes a stable
  key order so the serialized output is deterministic regardless of import order.
- **Manifest missing entirely**: the snapshot test fails closed with a message telling the
  developer to run the generator (not a silent skip).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a generator that reads the live registered rule set from
  `registry.all_rules()` and writes a rule-inventory manifest at `docs/rules/rules-manifest.json`.
  The manifest MUST be generated from the live registry at build time, NEVER hand-typed.
- **FR-002**: Each manifest entry MUST carry exactly the two serializable `RegisteredRule` fields:
  `id` and `title`. The manifest MUST NOT include the rule callable, a severity, a family label,
  a literal rule-count, or any per-table / worked-example / billing / segment / PII data
  (generic-only; hard rule #7, Principle VII).
- **FR-003**: The generator output MUST be deterministic and idempotent: a stable key order,
  serialized as UTF-8 without BOM, with `\n` line endings and a single trailing newline; running
  it twice with no code change MUST produce byte-identical output.
- **FR-004**: The system MUST provide a golden-equality snapshot test
  (`tests/unit/test_rules_manifest_snapshot.py`) that compares the committed manifest against the
  manifest derived from the live `all_rules()` and FAILS CLOSED on any difference.
- **FR-005**: The snapshot test MUST normalize line endings and read the committed file as UTF-8
  before comparing, so it does not flake under `core.autocrlf=true` on Windows.
- **FR-006**: On drift, the snapshot test failure message MUST be actionable: it MUST identify the
  drifted/missing/unexpected ids (and/or changed titles) and instruct the developer to regenerate
  the manifest with the generator and commit it in the same change.
- **FR-007**: This work MUST NOT add a new `@register`-ed rule and MUST NOT add a new
  `EXPECTED_RULE_ID`. The snapshot test is a test-only golden assertion; it is NOT a registered
  governance rule and does not run inside `retail check`. (This is the over-scope guard: the
  cited A1/routes.py precedent is materially different -- A1 IS a runtime rule and IS an
  `EXPECTED_RULE_ID`; this is not.)
- **FR-008**: The generator and the snapshot test MUST be stdlib-only with NO dependency on a
  database, the network, Power BI Desktop, or the Power BI execution adapter (F016). They inventory
  committed code and execute no rules (Principle VIII, static-first).
- **FR-009**: The stale "26 rules" occurrences in the LIVE constitution principle body
  (`.specify/memory/constitution.md` lines 377 + 381) MUST be corrected to match the live registry
  and to reference the manifest as the source of truth. Historical Sync-Impact-comment occurrences
  of older counts elsewhere in the constitution MUST be left unchanged.
- **FR-010**: A `.gitattributes` entry MUST pin `docs/rules/rules-manifest.json` to `text eol=lf`
  so the committed bytes are stable across platforms.

### Key Entities *(include if feature involves data)*

- **Rule manifest entry**: a record of one registered rule, with exactly `id` (the rule id string,
  e.g. `D1`, `S4a`, `A1`) and `title` (the human-readable rule title). No other fields.
- **Rule manifest**: the ordered collection of all manifest entries, serialized to
  `docs/rules/rules-manifest.json`. It is an exact inventory of the live registry, not a summary
  or a score.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any add/remove/rename of a rule that is not accompanied by a regenerated manifest is
  caught by a failing test 100% of the time (zero silent drift).
- **SC-002**: A maintainer can regenerate the manifest with a single command and the result is
  byte-identical on repeated runs (deterministic) and across Windows/Linux checkouts.
- **SC-003**: The live constitution principle body contains zero stale rule-count occurrences after
  this work; documented counts cite the generated manifest rather than a hand-typed number.
- **SC-004**: The feature adds zero new registered rules and zero new `EXPECTED_RULE_ID` entries
  (verified against `tests/unit/test_rules_wiring.py`), confirming it does not enlarge the gate.
- **SC-005**: The snapshot test passes on a clean checkout on both Windows (`core.autocrlf=true`)
  and Linux with no line-ending-related flakiness.

## Assumptions

- The live registry (`registry.all_rules()`) is and remains the single source of truth for the
  rule inventory; it currently returns 33 `RegisteredRule(id, rule, title)` entries, in agreement
  with `EXPECTED_RULE_IDS` (33). The earlier backlog claim of "34 incl. A1 / a 33-vs-34
  off-by-one" is FALSE -- A1 is already one of the 33. The generator reads the live count; no
  literal count is baked anywhere.
- `docs/rules/` does not yet exist and is created by this work; `docs/rules/rules-manifest.json`
  and `tests/unit/test_rules_manifest_snapshot.py` do not yet exist and are created by this work.
- The generator is placed as a `retail` CLI subcommand (per Q1), reusing the existing `cli.py`
  seam; this is a reversible placement choice.
- This spec is the PLAN only. Implementation (creating the manifest JSON, the generator, the test,
  and editing the constitution) is downstream work, not performed by the spec author.
- No deferred capability is assumed to exist: the feature requires no Power BI Execution Adapter
  (F016) and no spec-only runtime (F031-F033).
