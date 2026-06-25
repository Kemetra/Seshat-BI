# Feature Specification: grain confidence + mapping diff reviewer

**Feature Branch**: `009-grain-confidence-reviewer` (work on the feature branch per
session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Implemented (commit `2a3eeec`, 2026-06-25) -- shipped to `main`

**Input**: "Roadmap F008 (Layer 3 Mapping Governance). Advances readiness stage:
Mapping Ready. Surface grain-uniqueness CONFIDENCE as EVIDENCE (a measured
PK-uniqueness signal + the reviewer's recorded judgment), plus a reviewable DIFF
between two source-map.yaml versions. CRITICAL: 'confidence' here must be
evidence-backed (a measured uniqueness result + blockers), NOT a fabricated
numeric score -- honor hard rule #9 (no fake confidence) and the readiness
spine's status+evidence+blockers model. Grain is a Principle-V human-judgment
seam: the reviewer SURFACES and the human DECIDES; do not auto-resolve grain.
Generic only (hard rule #7)."

## Why this feature exists

The Mapping Ready stage (constitution Principle IV, `docs/readiness/mapping-ready.md`)
turns on one load-bearing fact: **is the declared grain actually unique on the
data?** Today that fact is computed mechanically (`src/retail/profile.py` returns a
`PkProof` of `total` / `distinct_pk` / `null_pk` / `is_unique`) and written by hand
into `source-profile.md`, but nothing *surfaces it as reviewable readiness
evidence*, and nothing helps a reviewer see *what changed* when a `source-map.yaml`
is revised. A reviewer re-reading a whole YAML by eye to find that the grain or a
`pii:` flag moved is exactly the unreviewed-drift failure this kit exists to prevent.

This feature fills two gaps inside the existing gate -- it adds **no new gate** and
**no new principle** (readiness spine posture):

1. **Grain confidence as EVIDENCE.** Surface the measured PK-uniqueness signal plus
   the reviewer's recorded judgment as a legible readiness artifact a human reads
   before approving Mapping Ready. The "confidence" is the measured result + the
   open blockers, expressed in the four readiness statuses -- never a fabricated
   number (hard rule #9; readiness-model.md "No fake confidence").

2. **Mapping DIFF.** Surface a reviewable, semantic diff between two
   `source-map.yaml` versions, foregrounding the load-bearing changes (grain, PK,
   `pii:` flags, `gold_placement`) so review sees only what moved.

It deepens the shipped mapping gate (roadmap Layer 3, "shipped gate; F008
deepens"). It does NOT auto-resolve grain, PII, or business rollups -- those stay
the Principle-V human seam (the reviewer surfaces, the human decides).

## What "confidence" means here (the load this feature respects)

"Confidence" in this feature is **evidence + status + blockers**, never a score:

- **The measured signal (evidence).** From `profile.py`'s `PkProof` over the landed
  data: `total` (= `COUNT(*)`), `distinct_pk` (= `COUNT(DISTINCT pk)`), `null_pk`
  (NULLs in any PK column), and the derived `is_unique` (`total == distinct_pk and
  null_pk == 0`). These are FACTS a query returned, citable as `evidence[]`.
- **The recorded judgment (evidence).** The human's resolution of the grain
  question in `mappings/<table>/unresolved-questions.md` (and the grain/PK
  statement in `source-map.yaml`). Approval is a named human action recorded in the
  readiness status `approvals[]`; the reviewer cannot self-grant it.
- **The blockers.** Concrete `blocking_reasons[]` when the signal does not hold:
  `is_unique=false`, `null_pk>0`, a row-vs-entity ratio mismatch the human flagged,
  or no live profile yet (the live boundary is deferred, Principle VIII).
- **NOT a number.** No `0.87`, no "high/medium/low" auto-label that reads as a
  score. Grain confidence is reported as one of the four readiness statuses
  (`not_started` | `blocked` | `warning` | `pass`) with the signal and blockers
  attached. A numeric score stays OPTIONAL and DEFERRED until scoring rules are
  defined (readiness-model.md); this feature does not define them.

## Architecture (a pure reviewer skill; no new gate, no codegen, no new CLI)

The reviewer is a pure agent-procedure skill, consistent with the kit's all-skills
verb architecture (the agent is the runtime, as in `source-mapping`,
`retail-build-warehouse`, `retail-orchestrate`). **Decision: a pure skill
(`.claude/skills/grain-confidence-reviewer/SKILL.md`); no new Python module, no new
`retail` CLI subcommand, no new gate.**

Deciding reason: the measured signal ALREADY EXISTS as `profile.py`'s `PkProof`, and
the diff inputs are two committed text files. The skill READS the measured signal
(re-running `profile.py` at the deferred live boundary, or reading the committed
profile numbers) and READS two `source-map.yaml` versions from git, then RENDERS a
grain-confidence card and a mapping diff for a human. Adding a Python diff/scoring
engine would (a) risk emitting a score the readiness model forbids, and (b) add the
repo's first maintained reviewer-engine surface for ~zero gain at one-table volume
(YAGNI). A pure skill that surfaces existing evidence and stops at the human seam is
the right grain. (If a future slice proves a CLI/render helper is warranted, it is a
recorded deferred decision below, not this slice.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Surface grain confidence as readiness evidence (Priority: P1)

A reviewer about to approve Mapping Ready for `mappings/<table>/` asks for the grain
confidence. The skill surfaces the measured PK-uniqueness signal (`total`,
`distinct_pk`, `null_pk`, `is_unique`) as a card, maps it to one of the four
readiness statuses with the evidence and any blockers attached, and STOPS for the
human to decide -- it never emits a numeric confidence and never approves the gate.

**Why this priority**: grain uniqueness is the single load-bearing fact of Mapping
Ready; surfacing it as legible status + evidence + blockers is the core value and
the readiness spine's central promise.

**Independent Test**: given a `mappings/<table>/source-profile.md` carrying a
measured `PkProof` (`is_unique=true`, `null_pk=0`), the skill renders a card with
status `pass`-eligible and cites the three numbers as evidence; given a profile with
`is_unique=false` or `null_pk>0`, it renders `blocked` with the concrete
`blocking_reasons[]` and raises the grain question rather than resolving it.

**Acceptance Scenarios**:

1. **Given** a profile with `total == distinct_pk` and `null_pk == 0`, **When** the
   reviewer runs the skill, **Then** it reports the grain signal as supporting a
   `pass` (evidence: the three counts) and states that human approval in
   `approvals[]` is still required (the skill does not self-grant it).
2. **Given** a profile with `distinct_pk < total` (PK not unique) or `null_pk > 0`,
   **When** the skill runs, **Then** it reports `blocked` with `blocking_reasons[]`
   ("grain not confirmed unique on data: COUNT(DISTINCT pk) < COUNT(*)" and/or
   "NULLs present in PK columns") and points to the open grain question.
3. **Given** any state, **When** the skill renders the card, **Then** it emits NO
   numeric confidence score and NO auto high/medium/low label -- only one of the
   four readiness statuses plus the cited evidence and blockers.
4. **Given** no live profile exists yet (no DSN / no `db` extra), **When** the skill
   runs, **Then** it reports the grain signal as `[PENDING LIVE PROFILE]` and status
   `blocked` (evidence missing), prints the enable steps, and does not fabricate a
   result (Principle VIII live boundary).

### User Story 2 - Reviewable diff between two source-map versions (Priority: P1)

A reviewer revising `mappings/<table>/source-map.yaml` asks what changed versus a
prior committed version. The skill renders a semantic diff that foregrounds the
load-bearing fields -- grain, primary_key, every column's `pii:` flag, and every
`gold_placement` -- so review sees the governance-relevant moves first, not a noisy
line diff.

**Why this priority**: an unreviewed change to grain, a `pii:` flag, or a gold
placement is precisely the drift the mapping gate exists to catch; making those
changes legible at review time is half this feature's value.

**Independent Test**: given two versions of a generic `source-map.yaml` where the
grain statement changed, a `pii:` flag flipped `false->true`, and one column's
`gold_placement` moved (e.g. `fact_measure -> dim:...`), the skill's diff lists
exactly those three changes under load-bearing headings, each marked with whether it
REQUIRES re-approval (grain/PK/PII changes do; a comment-only edit does not).

**Acceptance Scenarios**:

1. **Given** two `source-map.yaml` versions (a git ref/path pair), **When** the
   skill diffs them, **Then** it groups changes under `grain`, `primary_key`,
   `pii` flags, and `gold_placement`, and lists additions/removals/moves per group.
2. **Given** a change to grain, primary_key, or any `pii:` flag, **When** the diff
   renders, **Then** that change is flagged "REQUIRES RE-APPROVAL" (it invalidates
   any prior Mapping Ready approval -- the gate must be re-reviewed).
3. **Given** only non-load-bearing edits (a comment, a `reason:` wording change),
   **When** the diff renders, **Then** it states no re-approval is forced but still
   lists the edits for the audit trail.
4. **Given** a `pii:true` column whose `decision` is no longer `drop` after the
   edit, **When** the diff renders, **Then** it raises that as a governance
   blocking_reason (Principle V PII seam) rather than passing it through silently.

### User Story 3 - Judgment calls hard-stop, never auto-resolved (Priority: P1)

The reviewer surfaces and the human decides. Grain ambiguity, PII publish-safety,
and business-rollup mappings are never auto-resolved by the skill -- each
HARD-STOPS and is raised as / pointed to an `unresolved-questions.md` entry with the
named owner (analyst / governance / data-owner).

**Why this priority**: this is the Principle-V seam the whole feature must respect;
violating it would turn a reviewer aid into an autonomy hole that invents the very
grain/PII decisions the kit reserves for a human.

**Independent Test**: present a profile where `is_unique=false`; assert the skill
STOPS and raises the grain question with `Who must answer: analyst`, rather than
proposing a different PK or declaring a lower grain on its own.

**Acceptance Scenarios**:

1. **Given** `is_unique=false`, **Then** STOP -- raise the grain question to the
   analyst; never auto-pick a new candidate PK or silently widen the grain.
2. **Given** a `pii:` flag change toward publish, **Then** STOP -- route to
   governance sign-off; never declare a column publish-safe.
3. **Given** a request to "just approve" Mapping Ready, **Then** STOP -- the skill
   surfaces evidence and blockers and states approval is the human's recorded action
   in `approvals[]`; it never writes the approval itself or `Gate status: CLEARED`.

### Edge Cases

- **No prior version to diff against.** If only one `source-map.yaml` version exists
  (first map), the diff degrades gracefully to "initial version -- nothing to diff"
  and the skill still renders the grain-confidence card.
- **PK columns renamed between versions.** A `rename_to` change on a PK column is a
  load-bearing move; the diff surfaces it under `primary_key` and flags re-approval.
- **Composite-PK reordering only.** Reordering PK columns without changing the set is
  surfaced but flagged as not changing uniqueness; the human confirms intent.
- **Profile is stale vs the current map.** If the committed profile's PK columns no
  longer match `source-map.yaml`'s `primary_key`, the skill reports the mismatch as
  a blocker (the measured signal does not back the current grain claim).
- **Diff across a `gold_star` reshape.** Adding/removing a dimension or moving a
  degenerate dim is surfaced under `gold_placement`; the human judges impact.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `.claude/skills/grain-confidence-reviewer/SKILL.md` (ASCII, UTF-8
  no BOM, valid frontmatter). No new Python module, no `retail` CLI subcommand, no
  new gate, no codegen.
- **FR-002**: The skill READS the measured PK-uniqueness signal -- either by reading
  the committed `mappings/<table>/source-profile.md` numbers, or, at the deferred
  live boundary, by re-running `src/retail/profile.py` over a read-only connection
  (`resolve_dsn` + `make_psycopg2_runner`, the `db` extra). It MUST NOT re-implement
  the uniqueness query; it reuses `PkProof`.
- **FR-003**: The skill renders a grain-confidence CARD that reports `total`,
  `distinct_pk`, `null_pk`, `is_unique` as cited evidence and maps them to ONE of
  the four readiness statuses (`not_started` | `blocked` | `warning` | `pass`) with
  `evidence[]` and `blocking_reasons[]`. It MUST NOT emit a numeric confidence score
  or an auto high/medium/low label (hard rule #9; readiness-model.md).
- **FR-004**: The status mapping is explicit and evidence-only: `is_unique=true` AND
  `null_pk=0` -> the signal supports `pass` (human approval still required);
  `is_unique=false` OR `null_pk>0` -> `blocked` with the concrete reason; no live
  profile yet -> `blocked` + `[PENDING LIVE PROFILE]`; a human-recorded, data-justified
  deviation (e.g. an accepted known-duplicate handled in silver) -> `warning`, never
  auto-promoted to `pass`.
- **FR-005**: The skill renders a mapping DIFF between two `source-map.yaml` versions
  (each identified by a git ref and/or path), grouping changes under the load-bearing
  fields: `meta.grain`, `meta.primary_key`, every column `pii:` flag, and every
  `gold_placement`. Non-load-bearing edits are listed separately for the audit trail.
- **FR-006**: The diff flags any change to grain, primary_key, or a `pii:` flag as
  "REQUIRES RE-APPROVAL" -- such a change invalidates any prior Mapping Ready
  `approvals[]` entry and the gate MUST be re-reviewed.
- **FR-007**: The skill carries a fail-loud judgment-stop table. Each of these
  HARD-STOPS and is raised to / pointed at an `unresolved-questions.md` entry with
  the named owner; none is satisfiable by a silent default: grain not unique on data
  (analyst); a `pii:` flag moving toward publish or a `pii:true` column not `drop`
  (governance); a business-rollup/segment change (analyst-supplied table required);
  any request to approve the gate (human-only `approvals[]` action).
- **FR-008**: The skill never writes an approval, never writes `Gate status:
  CLEARED`, never edits `source-map.yaml` to resolve a finding, and never picks a new
  candidate PK or grain on the human's behalf. It surfaces and stops.
- **FR-009**: The grain-confidence card is emitted in a shape that can be recorded as
  the Mapping Ready stage's `evidence[]` / `blocking_reasons[]` in the readiness
  status -- read/written at the canonical `mappings/<table>/readiness-status.yaml`
  (ADR 0004), shaped to `templates/readiness-status.yaml`. It reinforces the spine,
  adding no new state field. If a numeric `score` field is ever shown it MUST be marked
  OPTIONAL and cite the evidence it derives from (default: omit it).
- **FR-010**: All examples and placeholders are GENERIC (hard rule #7 / Principle
  VII): no C086/pharmacy specifics (no billing codes, segment names, insurance/PII
  columns, or per-table grain keys) in the skill text. C086 may be CITED as the
  filled instance, never copied inline.
- **FR-011**: Append an `## Orchestration` pointer so `retail-orchestrate` can call
  this reviewer at the Mapping Ready review seam; the skill stays single-purpose
  (surface evidence + diff, then STOP) -- the self-heal loop lives only in the
  conductor, never here.

### Key Entities

- **Grain-confidence card**: a rendered view of the measured `PkProof` (`total`,
  `distinct_pk`, `null_pk`, `is_unique`) mapped to a readiness status with evidence
  and blockers. Not a score; not persisted as new state.
- **Mapping diff**: a semantic diff between two `source-map.yaml` versions, grouped
  by the load-bearing fields (grain, PK, `pii`, `gold_placement`) with a
  re-approval flag per change.
- **Reviewer skill** (`grain-confidence-reviewer`): the pure agent-procedure verb;
  the agent is the runtime. Reads existing evidence, renders, stops at the human seam.
- **`PkProof`** (existing, `src/retail/profile.py`): the measured uniqueness signal
  reused as evidence; this feature adds no new measurement code.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.claude/skills/grain-confidence-reviewer/SKILL.md` exists, ASCII +
  UTF-8 no BOM, valid frontmatter, registered by the harness; no new Python, no new
  CLI subcommand, `dependencies = []` unchanged.
- **SC-002**: `retail check` stays exit 0 (27 rules) and the full unit suite stays
  green with the new skill added (the skill is text; it changes no rule and no code).
- **SC-003**: For a generic profile with `is_unique=true`/`null_pk=0`, the rendered
  card cites the three counts as evidence and reports a `pass`-eligible status with
  "human approval still required"; for `is_unique=false`, it reports `blocked` with
  the concrete reason -- and in NEITHER case does it emit a numeric score (verifiable
  by inspecting the rendered card against FR-003/FR-004).
- **SC-004**: For a generic two-version `source-map.yaml` change set (grain edit +
  `pii:` flip + `gold_placement` move), the diff lists exactly those changes under
  their load-bearing headings and flags the grain and PII changes "REQUIRES
  RE-APPROVAL" (verifiable against FR-005/FR-006).
- **SC-005**: No judgment call is auto-resolved: a non-unique grain, a PII move, and
  an approve request each produce a HARD-STOP that names the owner and points at
  `unresolved-questions.md` (verifiable against FR-007/FR-008).

## Assumptions

- Pure reviewer skill (no new Python, no CLI, no gate) -- the measured signal already
  exists as `PkProof` and the diff inputs are two committed files, so a reviewer
  engine buys ~zero at one-table volume (YAGNI) and risks emitting the forbidden
  score.
- "Confidence" is evidence + status + blockers, never a number (hard rule #9;
  readiness-model.md "No fake confidence"). A numeric `score` stays OPTIONAL and
  DEFERRED.
- The live profile (re-running `profile.py`) is the deferred DB-read boundary
  (Principle VIII): without a DSN / the `db` extra, the skill reads the committed
  profile numbers or reports `[PENDING LIVE PROFILE]` -- it never fabricates a result.
- Grain, PII, and business-rollup decisions are the Principle-V human seam: the
  skill SURFACES and STOPS; the human DECIDES and records approval in `approvals[]`.
- This feature advances Mapping Ready (Stage 2); it adds no new gate and reinforces
  the readiness spine (status + evidence + blockers), changing no compliance posture.
- The diff is semantic (grouped by load-bearing field), not a raw line diff; it reads
  two `source-map.yaml` versions via git refs and/or paths.

## Deferred decisions (future specs / issues -- recorded, not built)

- **A numeric grain-confidence score and its scoring rules.** Deferred until the
  readiness model defines scoring (readiness-model.md: numeric scores are OPTIONAL
  and DEFERRED). Until then the four statuses + evidence + blockers are the contract.
- **A `retail diff` / `retail confidence` CLI subcommand or a Python render helper.**
  If reviewer volume grows beyond one-at-a-time agent use, a helper that renders the
  card/diff deterministically could be warranted; deferred (YAGNI), recorded here.
- **Persisting the grain-confidence card as a committed artifact** (e.g. a
  `grain-confidence.md` per table). This slice renders it for review and records it
  into the readiness status `evidence[]`/`blocking_reasons[]`; a standalone committed
  card is a possible later template, deferred.
- **Diffing the other mapping artifacts** (`assumptions.md`, `unresolved-questions.md`).
  This slice diffs `source-map.yaml` (the machine-readable spine); extending the
  semantic diff to the prose artifacts is a later enhancement.
- **An automated re-approval-invalidation hook.** This slice FLAGS that a grain/PK/PII
  change requires re-approval; wiring that to actually reset an `approvals[]` entry in
  the readiness status is a later orchestration concern.

## See also

- The stage this advances: `docs/readiness/mapping-ready.md`; the model:
  `docs/readiness/readiness-model.md` ("No fake confidence").
- The measured signal reused as evidence: `src/retail/profile.py` (`PkProof`); the
  profile artifact: `templates/source-profile.md` (Candidate grain & PK section).
- The map being diffed: `templates/source-map.yaml` (grain/PK/pii/gold_placement);
  the gate's human seam: `templates/unresolved-questions.md` (`Gate status`).
- The verbs this sits beside: `.claude/skills/source-mapping/SKILL.md`,
  `.claude/skills/retail-orchestrate/SKILL.md`; the live sibling:
  `.claude/skills/retail-validate/SKILL.md`.
- Principles: `.specify/memory/constitution.md` IV (mapping gate), V (human seam),
  VII (generic), VIII (live deferred); roadmap: `docs/roadmap/roadmap.md` (F008).
