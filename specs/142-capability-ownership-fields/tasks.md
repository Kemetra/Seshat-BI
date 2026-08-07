# Tasks: Capability ownership fields

**Spec**: `specs/142-capability-ownership-fields/spec.md`

**Plan**: `specs/142-capability-ownership-fields/plan.md`

**Status**: Draft -- NOT ratified. No task below may be started until a named
human ratifies the spec.

---

## Conventions

- `[P]` = parallelizable with its siblings.
- Every task names a **verifiable deliverable**. A task is checked only after
  that deliverable is inspected -- never by sweeping the file.
- TDD: the test that proves a behavior lands **before** the behavior.

## Gate set (run at the end of every phase)

```
seshat check
ruff format --check src tests scripts && ruff check src tests scripts
python scripts/export_agent_bundles.py --check
python -m pytest tests/unit/test_capability_inventory.py \
  tests/contract/test_capability_ship_classification.py \
  tests/contract/test_generated_agent_bundles.py -q --no-cov
```

Expected: `seshat check` exit 0 carrying only the pre-existing RS1 warning;
bundle drift PASS; all tests green.

---

## Phase 0 -- Baseline

- [ ] T001 Capture the pre-change gate baseline into
  `specs/142-capability-ownership-fields/evidence/baseline-gates.txt` by running
  the full gate set, recording the pre-existing RS1 warning as
  expected-and-unrelated. Deliverable: the file, containing all four commands'
  output.
- [ ] T002 [P] Record the committed bundle digests for both harnesses into
  `evidence/baseline-bundles.txt` from
  `integrations/claude-code/seshat-bi/bundle-manifest.json` and
  `integrations/codex/seshat-bi/bundle-manifest.json`. Deliverable: both
  `manifest_digest` values, so FR-004 can be proven by comparison rather than
  by assertion.
- [ ] T003 [P] Record the current entry count and the exhaustive key set present
  across all entries of `docs/capabilities/capabilities.yaml` into
  `evidence/baseline-manifest-keys.txt`. Deliverable: the key list, proving no
  `ownership` key exists before this work.

## Phase 1 -- Vocabulary and validation (RED first, no manifest data)

- [ ] T010 Write a FAILING test in `tests/unit/test_capability_inventory.py`
  asserting the oracle rejects an entry whose `ownership.capability_owner` is
  not in the FR-002 token set. Deliverable: a test that fails with a clear
  message before T012 exists.
- [ ] T011 [P] Write a FAILING test asserting the oracle rejects an entry with
  `capability_owner: seshat-adapter` and a missing or empty `seshat_delta`
  (FR-006). Deliverable: a second failing test.
- [ ] T012 Add `OWNERSHIP_OWNERS` (FR-002) and `OWNERSHIP_SURFACES` (FR-003)
  token sets plus the two axis check functions to
  `tests/unit/_capability_oracle.py`, wired into the same
  `find_*_violations` pattern the existing axes use. Deliverable: T010 and T011
  now pass; every previously green oracle test still passes.
- [ ] T013 Add an explicit test asserting **no ownership field name contains any
  `NUMERIC_FIELD_HINTS` substring** (`score`, `maturity`, `confidence`,
  `completeness`, `health`) — FR-008 clause 1. Deliverable: a test that would
  fail if a future field were named e.g. `ownership_maturity`. This is the
  guard on the spec's own primary risk, so it must assert against the FR-001
  vocabulary list, not against whatever the manifest happens to contain.
- [ ] T014 Run the gate set. Deliverable: all green, and the bundle digests from
  T002 **unchanged** — Phase 1 touches no manifest entry, so this is the
  inertness proof.

## Phase 2 -- Pilot the four known wrappers (proves FR-004 on real data)

- [ ] T020 Classify `dbt-transformation-adapter` as `seshat-adapter`, upstream
  `dbt Labs`, with `upstream_reference` cross-checked against
  `src/seshat/integrations/catalog.py:168-186` per FR-007. Deliverable: the
  entry, with a non-empty `seshat_delta`.
- [ ] T021 [P] Classify `dagster-orchestration-adapter`, cross-checked against
  `catalog.py:191-212`. Deliverable: the entry.
- [ ] T022 [P] Classify `pbi-mcp-doctor`, upstream Microsoft, cross-checked
  against `catalog.py:224-235`. Deliverable: the entry, with the upstream's
  preview/pre-GA status reflected in `update_policy` as a quoted string
  (FR-008 clause 2).
- [ ] T023 [P] Classify `pbir-authoring-adapter` with `upstream_surface: format`
  (FR-003) — PBIR is an upstream-owned format with no executable surface.
  Deliverable: the entry.
- [ ] T024 Run the gate set. Deliverable: bundle digests **identical** to T002
  with four entries now carrying the axis — the empirical proof of FR-004 and
  SC-004, at four entries rather than 102.

## Phase 3 -- Knowledge roots and governance set (mechanical)

- [ ] T030 Classify the six `skills/` roots as `seshat-domain-knowledge`, each
  with `canonical_source` naming its authored path and `generated_targets`
  naming its two bundle projections (FR-005). Deliverable: six entries.
- [ ] T031 Classify the readiness/evidence/approval set as
  `seshat-governance`, per `docs/capabilities/ownership-audit.md` section 4.
  Deliverable: the entries, with no `upstream_project` (none exists).
- [ ] T032 Run the gate set. Deliverable: all green, digests unchanged.

## Phase 4 -- Remainder, in reviewable batches

- [ ] T040 Classify the orchestrator/front-door set as `seshat-orchestrator`
  per the audit's KEEP section. Deliverable: the entries; one commit.
- [ ] T041 Classify the Power BI layer entries. Deliverable: the entries.
  `powerbi-dashboard-design` and `powerbi-workflows` receive an `overlap_note`
  naming each other (US3) — advisory only, merging nothing.
- [ ] T042 Classify the remaining `cli`-surface entries. Deliverable: the
  entries; one commit per reviewable batch.
- [ ] T043 Run the gate set. Deliverable: all green, digests unchanged.

## Phase 5 -- Closeout

- [ ] T050 Write the deliberately-unclassified list into
  `evidence/unclassified.md`: every entry with no `ownership` mapping and the
  reason. Deliverable: the file (SC-001). Entries blocked on OD-1/OD-2 are
  listed here, not guessed.
- [ ] T051 Verify SC-002 mechanically: every `seshat-adapter` entry carries a
  non-empty `seshat_delta`. Deliverable: the oracle passing, plus the count.
- [ ] T052 Verify SC-007 mechanically: no key name anywhere in the manifest
  contains a `NUMERIC_FIELD_HINTS` substring, and no ownership value is a bare
  numeric scalar. Deliverable: O6 green plus the grep output.
- [ ] T053 Update `docs/capabilities/README.md` to document the ownership axis
  and its token sets. Deliverable: the README section. **Not** a value-by-value
  contract table — the oracle owns validation (FR-009).
- [ ] T054 Run the full gate set plus `pytest -m unit`. Deliverable: the
  complete output recorded in `evidence/final-gates.txt`.

## Explicitly NOT tasks

These are named so no one adds them mid-implementation:

- **No `seshat check` rule.** Issue #592 section D is a Non-goal; it has no
  filled target until this spec produces values. Any task proposing a static
  rule is out of scope by definition (FR-009, plan Risk R4).
- **No reviving the five dead constants** at
  `src/seshat/capability_inventory.py:35-43` (FR-010, plan Risk R3). Recorded as
  OD-3 for a separate spec.
- **No rendering the axis in inventory output.** Deferred; requires extending
  the closed `DECLARED_RECORD_FIELDS` contract.
- **No answering OD-1** (`speckit-*` vendored-upstream) **or OD-2** (INSPECT
  dev-workflow skills). Owner rulings.
- **No deleting, merging, or consolidating any capability.**
- **No promoting this spec into the `<!-- SPECKIT -->` fence** as part of
  implementation. Fence movement is an owner action.

## Dependencies

- T010, T011 precede T012 (RED before GREEN).
- Phase 1 precedes Phase 2: the validation must exist before data relies on it.
- T024 is the FR-004 proof gate; Phases 3-5 assume it passed.
- T050 depends on Phases 2-4 being complete, since it enumerates what remains.
- OD-1 and OD-2 block only their own entries in T042/T050, never a whole phase.
