# Feature Specification: Idea-Bank Memory Seam (IL1)

**Feature Branch**: `052-idea-bank-memory-seam`

**Created**: 2026-06-30

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-06-30)

**Ratification note**: Ratified by the advisor agent acting under an explicit,
recorded per-spec delegated override granted by the repo owner
(info@rahmaqanater.org) for the 2026-06-30 unattended overnight session. Provenance:
this Ratified line is AI-authored under recorded human authority; it is NOT a
human-typed ratification and the git author identity does not by itself attest a
human reviewer. The three clarify ambiguities and the three deferred questions
(promotion authority, ledger authorship, replace-vs-alongside) are resolved as
recorded rulings in the Clarifications section, all taking the conservative
"read/evidence ledger, human-curated, alongside the prose appendix, never promotes"
answer. The optional IL1 static rule (FR-010) is OUT of scope. No Principle-V carve-out
arose. analyze=clean (0 critical/0 high); plan-review=PASS-WITH-NOTES (3 low).

**Input**: User description: "Idea-Bank Memory Seam / Shipped-row->roadmap-F-row hard link (IL1)"

## Overview

The idea-engine regenerates the idea backlog on every run with no durable, structured
memory of what has already SHIPPED or SETTLED. Today its Memory stage reads two soft
sources: the prior bank's prose headings and a hand-written prose appendix
("## SHIPPED / SETTLED") inside `idea-backlog.md`, plus Ground's in-session
git-derived ship-status. There is no on-disk, machine-readable ledger that records
"idea-id X shipped as PR/SHA Y, and a human placed it at roadmap F-row Z (or nowhere)".

This feature adds that seam: a curated, structured ledger
`docs/roadmap/shipped-ideas.yaml` mapping `idea-id -> { pr_sha, f_row | none }`, plus a
read step in the idea-engine Memory stage that consumes it as known-history so the engine
stops re-pitching ideas that already shipped (A1/B1/B2/F7/F8 today) and can name the
shipped row's evidence to the lenses.

The link is **evidence-OF-shipped**, never auto-promotion. The ledger records the F-row
a human has *already* placed; no step (engine or future rule) may write a roadmap F-row
from it. This preserves the project invariant that the output is an idea bank, not a
roadmap, and that a human rules every promotion.

Scope is deliberately the CORE seam only (the ledger artifact + the engine read step).
The OPTIONAL static reconciler rule the idea mentions ("Add IL1 rule separately if the
rule budget allows") is explicitly OUT OF SCOPE for this spec and deferred to a separate
rule-budget decision.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Engine remembers what already shipped (Priority: P1)

As the maintainer running the idea-engine, when the engine regenerates the backlog I want
it to read a structured shipped-ledger so it labels and de-emphasizes ideas that have
already shipped (instead of re-pitching A1/B1/B2/F7/F8 as if new), and so the evidence
(PR/SHA, and the human-placed F-row when one exists) is available to the scoring lenses
as known-history.

**Why this priority**: This is the load-bearing fix the idea names. Without it the engine
has a self-referential orphaning loop: shipped ideas get re-litigated every run, wasting
the bank's yield and eroding trust in its memory. Delivering just this story is a viable
MVP: a structured ledger that the engine reads is the whole point of the seam.

**Independent Test**: Author `shipped-ideas.yaml` with one shipped entry whose idea-id
matches a candidate the engine would otherwise generate; run the Memory stage; confirm the
candidate is labeled SHIPPED (with its cited evidence) rather than presented as new. Fully
testable against committed files; no live DB, no executor.

**Acceptance Scenarios**:

1. **Given** `shipped-ideas.yaml` contains `A1` with a `pr_sha` and `f_row: F062`,
   **When** the Memory stage runs, **Then** the engine treats A1 as known-history and
   surfaces its `pr_sha`/`f_row` evidence to the lenses, and does not present A1 as a new
   idea.
2. **Given** `shipped-ideas.yaml` contains an entry with `f_row: none`,
   **When** the Memory stage runs, **Then** the engine records it as shipped-with-no-F-row
   (honest orphaning signal) and never assigns or writes an F-row for it.
3. **Given** an idea-id that is NOT in `shipped-ideas.yaml`,
   **When** the Memory stage runs, **Then** the engine treats it as genuinely new (the
   ledger never deletes or suppresses a not-yet-shipped idea).

---

### User Story 2 - Ledger is a readable, honest history record (Priority: P2)

As a maintainer reviewing the bank's memory, I want `shipped-ideas.yaml` to be a small,
human-readable, hand-curated record (each entry citing its PR/SHA evidence) so I can audit
at a glance what the engine considers shipped and why, without parsing prose bullets.

**Why this priority**: The ledger is the durable artifact; its readability and curation
model are what make the memory trustworthy. Secondary to the engine actually reading it.

**Independent Test**: Open `shipped-ideas.yaml`; confirm each entry has a stable idea-id
key and cites evidence (a PR number and/or commit SHA), and that the file is valid YAML.

**Acceptance Scenarios**:

1. **Given** a new idea ships, **When** a human adds its row to `shipped-ideas.yaml`,
   **Then** the row carries the idea-id, the PR/SHA evidence, and the F-row a human placed
   it at (or `none`), with no sample data or domain specifics.
2. **Given** the existing prose "## SHIPPED / SETTLED" appendix in `idea-backlog.md`,
   **When** the ledger ships, **Then** the relationship between the two memory sources is
   explicit and non-contradictory (see Clarifications for which is authoritative).

---

### Edge Cases

- What happens when `shipped-ideas.yaml` does not exist yet (first run before any entry)?
  The Memory stage MUST treat an absent or empty ledger as "no structured history" and
  fall back to its existing prose/ship-status sources without error (graceful degradation).
- What happens when an idea-id appears in BOTH the structured ledger and the prose
  appendix? The reconciliation rule (Clarifications) governs which wins; the engine MUST
  NOT double-count or contradict itself.
- What happens when a ledger entry has `f_row: none` but the prose claims a roadmap row,
  or vice versa? This is a memory-integrity inconsistency surfaced for a human; the engine
  records what the ledger says and never silently "fixes" it by writing an F-row.
- What happens when the YAML is malformed? The read step MUST fail loudly (clear error)
  rather than silently proceeding as if there were no history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a structured, machine-readable ledger file at
  `docs/roadmap/shipped-ideas.yaml` keyed by the idea's existing backlog short-code
  (e.g. `A1`, `B2`, `F7`, `IL1`) -- the same token the prose appendix and ship-status
  already use; no new keying scheme is invented. Each entry MUST record a `status`
  (`shipped` or `settled`), `pr_sha` (PR number and/or commit SHA evidence), and `f_row`
  (the roadmap F-row a human has placed the idea at, or `none`). SETTLED-rejected ideas
  (e.g. F5/F6) are recorded too so the engine stops re-litigating them, not only re-pitching
  shipped ones.
- **FR-002**: The idea-engine Memory stage MUST read `shipped-ideas.yaml` and use it as
  known-history input to the scoring lenses, so already-shipped ideas are labeled and
  de-emphasized rather than re-pitched as new.
- **FR-003**: The ledger and every code path that reads it MUST be evidence-OF-shipped
  ONLY. No step (the engine, and any future rule) may write, assign, or promote a roadmap
  F-row from the ledger. The ledger records an F-row a human already placed; it never
  grants a roadmap decision.
- **FR-004**: The Memory stage MUST NOT re-read git to derive ship-status. Ground remains
  the single owner of git-derived ship-status; the ledger is a curated record of what a
  human has already shipped, distinct from Ground's live git read, and must not duplicate
  or override Ground's ownership.
- **FR-005**: An absent or empty `shipped-ideas.yaml` MUST be handled gracefully: the
  Memory stage falls back to its existing prose appendix + Ground ship-status sources and
  continues without error.
- **FR-006**: A malformed/unparseable `shipped-ideas.yaml` MUST cause the read step to
  fail loudly with a clear error, never to silently proceed as if no history existed.
- **FR-007**: The ledger MUST contain only generic governance identifiers (idea-ids,
  PR numbers, commit SHAs, F-row labels). It MUST NOT contain any sample data, metric
  values, mapping content, or domain (e.g. pharmacy/C086) specifics.
- **FR-008**: The change MUST be docs + a JS workflow read step only. It MUST NOT add an
  executor, a database connection, or any live-data path. Ledger authorship is RESOLVED
  (see Clarifications): entries are strictly human-curated like `status-claims.yaml` /
  `parked-on.yaml`; the engine only reads the ledger and never appends, so the
  single-owner-of-ship-status invariant is preserved.
- **FR-009**: When the structured ledger and the prose "## SHIPPED / SETTLED" appendix in
  `idea-backlog.md` disagree on an idea-id, the engine MUST treat `shipped-ideas.yaml` as
  authoritative for its machine read and MUST surface the disagreement as a
  memory-integrity signal; it MUST NOT silently rewrite either source. Replace-vs-alongside
  is RESOLVED (see Clarifications): the yaml sits alongside the prose appendix in this spec
  (no replacement); the mechanical read precedence above holds regardless.
- **FR-010**: The optional static IL1 reconciler rule (a fail-closed check on a SHIPPED row
  lacking evidence, mirroring SC1/DF1) is OUT OF SCOPE for this feature and MUST NOT be
  built here. If it is later approved as a separate rule-budget decision, it MUST register
  its id and appear in `EXPECTED_RULE_IDS` in the same change.

### Key Entities

- **Shipped-idea ledger entry**: One record in `shipped-ideas.yaml`, keyed by the idea's
  backlog short-code. Attributes: `status` (`shipped` | `settled`), `pr_sha` evidence
  (PR number and/or commit SHA), `f_row` (a human-placed roadmap F-row label, or `none`).
  No sample data, no domain specifics.
- **Idea-engine Memory stage**: The existing history-aware stage (`phase('Memory')`) that
  reads prior bank prose + Ground ship-status and labels/de-emphasizes already-handled
  ideas. This feature adds one read input (the structured ledger) to it; it remains a
  labeler that never writes the roadmap and never re-reads git.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After this feature, 100% of ideas listed in `shipped-ideas.yaml` are labeled
  as known-history by the Memory stage and are not presented as new ideas in a fresh run.
- **SC-002**: Zero roadmap F-rows are written, assigned, or promoted by any code path as a
  result of reading the ledger (verifiable: the engine's output never adds a row to
  `roadmap.md`).
- **SC-003**: A run with an absent or empty `shipped-ideas.yaml` completes without error
  and produces the same result it produces today (graceful fallback verified).
- **SC-004**: A maintainer can read `shipped-ideas.yaml` and identify, for each shipped
  idea, its evidence and its F-row placement (or `none`) without consulting any other file.
- **SC-005**: The ledger contains zero sample-data / domain-specific values on inspection
  (generic-identifiers-only check passes).

## Assumptions

- The idea-engine Memory stage (`phase('Memory')`) exists today and is the intended
  consumer; this feature adds a read input, it does not create the stage.
- `shipped-ideas.yaml` does not exist yet and is created NEW by this feature.
- The current set of already-shipped ideas to seed the ledger (A1, B1, B2, F7, F8, and the
  SETTLED F5/F6) is drawn from the existing prose appendix and Ground ship-status; the seed
  is small and hand-curated.
- The seam is pure JS workflow + YAML doc; no F016 Power BI Execution Adapter, no
  F031-F033 spec-only runtimes, and no live DB are assumed or required.
- Rule-count note: the authoritative current registered-rule count is the length of the
  `EXPECTED_RULE_IDS` frozenset in `tests/unit/test_rules_wiring.py` (currently 38 ids:
  S/D/R/A/B/C/G/P/PP1/SC1/DF1). Prior idea-bank prose citing "33/34" is stale. Because the
  optional rule is OUT OF SCOPE here, this feature makes NO "N+1" rule-count claim; any
  future IL1 rule would be 38 -> 39 and must reconcile against the live frozenset, not prose.

## Clarifications

<!--
  Principle-V judgment calls (promotion authority, ledger authorship, single-owner
  boundary) are recorded here for a human and are NOT answered by the planning agent.
  Ordinary ambiguities are resolved in /speckit-clarify and appended under a session block.
-->

### Session 2026-06-30

Advisor-resolved ordinary ambiguities (recommended answers, integrated into the spec):

- Q: What is the stable key for a ledger entry (the idea-id keying scheme)?
  -> A: The idea's existing short-code from the backlog (e.g. `A1`, `B2`, `F7`, `IL1`) --
  the same token the prose appendix and ship-status already use. Reuse, do not invent a
  new scheme. (Reasoning: matches the tokens A1/B1/B2/F7/F8 the engine already keys
  known-history on; minimizes reconciliation surface against the prose appendix; reversible.)
- Q: Does the ledger record SETTLED-rejected ideas (F5/F6) too, or only SHIPPED?
  -> A: Both, with an explicit `status` field per entry (`shipped` | `settled`). The
  engine's known-history must stop re-litigating settled REJECTs as well as re-pitching
  shipped ideas, so the same ledger carries both with their evidence. (Reasoning: the prose
  appendix already records both SHIPPED and SETTLED; a structured ledger that dropped
  SETTLED would lose half the memory the Memory stage needs; reversible.)
- Q: When the structured ledger and the prose appendix disagree on an idea-id, which is
  authoritative for the engine's read (mechanical precedence, distinct from the human
  scope question of whether the yaml replaces the prose)?
  -> A: The structured `shipped-ideas.yaml` is authoritative for the engine's machine read;
  on a conflict the engine uses the yaml value and SURFACES the disagreement as a
  memory-integrity signal (it never silently rewrites either source). (Reasoning: a machine
  read needs one deterministic source of truth; surfacing rather than auto-fixing preserves
  the human-rules-everything and fail-loud invariants; reversible. NOTE: whether the yaml
  ultimately REPLACES the prose appendix entirely is the separate human scope call below.)

### Resolved at the ratify gate (recorded rulings)

Ruled by the advisor under the recorded per-spec override (see the Ratification note in
the front-matter); all three take the conservative "add the seam, not the implementation"
answer and are easily reversible.

- **Promotion authority** -- RESOLVED: `shipped-ideas.yaml` is **strictly a read/evidence
  ledger**. NO step (the engine read, or any future rule) may write a roadmap F-row from it.
  An entry records an `f_row` value only when a human has already placed that F-row; the seam
  never assigns one. This preserves the "idea bank is not a roadmap" and Principle-V
  human-rules-every-promotion invariants.
- **Ledger authorship vs single-owner-of-ship-status** -- RESOLVED: entries are **strictly
  human-curated**, exactly like `status-claims.yaml` and `parked-on.yaml`. The engine only
  READS the ledger; it never appends. This keeps Ground the single owner of git-derived
  ship-status and avoids the engine-append boundary entirely.
- **Replace vs alongside the prose appendix** -- RESOLVED: `shipped-ideas.yaml` sits
  **alongside** the prose `## SHIPPED / SETTLED` appendix (no replacement in this spec). The
  structured ledger is authoritative for the engine's machine read (Q3 above); replacing the
  prose appendix is a larger, separate change left for later. No Principle-V carve-out arose.
