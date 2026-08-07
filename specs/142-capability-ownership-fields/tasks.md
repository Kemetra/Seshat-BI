# Tasks: Capability ownership fields

**Spec**: `specs/142-capability-ownership-fields/spec.md`

**Plan**: `specs/142-capability-ownership-fields/plan.md`

**Status**: Ratified (Ahmed Shaaban, 2026-08-07) -- implementation permitted.

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
  tests/contract/test_dbt_documentation.py \
  tests/contract/test_statistical_documentation.py \
  tests/contract/test_generated_agent_bundles.py -q --no-cov
```

All three manifest-reading contract tests are listed deliberately.
`test_dbt_documentation.py` asserts on `dbt-transformation-adapter` -- the entry
T020 edits first -- so omitting it would mean the FR-004 proof never exercised the
test guarding the pilot.

Expected: `seshat check` exit 0 carrying only the pre-existing RS1 warning;
bundle drift PASS; all tests green.

---

## Phase 0 -- Baseline

- [x] T001 Capture the pre-change gate baseline into
  `specs/142-capability-ownership-fields/evidence/baseline-gates.txt` by running
  the full gate set, recording the pre-existing RS1 warning as
  expected-and-unrelated. Deliverable: the file, containing all four commands'
  output. -- **done**: evidence/baseline-gates.txt -- all gates green, 74 tests passed, pre-existing RS1 recorded as unrelated
- [x] T002 [P] Record the committed bundle digests for both harnesses into
  `evidence/baseline-bundles.txt` from
  `integrations/claude-code/seshat-bi/bundle-manifest.json` and
  `integrations/codex/seshat-bi/bundle-manifest.json`. Deliverable: both
  `manifest_digest` values, so FR-004 can be proven by comparison rather than
  by assertion. -- **done**: evidence/baseline-bundles.txt -- claude 8bf0dd0b..., codex fdba0aa6...
- [x] T003 [P] Record the current entry count and the exhaustive key set present
  across all entries of `docs/capabilities/capabilities.yaml` into
  `evidence/baseline-manifest-keys.txt`. Deliverable: the key list, proving no
  `ownership` key exists before this work. -- **done**: evidence/baseline-manifest-keys.txt -- 102 entries, `ownership` absent (verified False)
- [x] T004 [P] Resolve every capability this spec names in prose to its actual
  manifest `id`, into `evidence/id-resolution.md`. Deliverable: a
  skill-name-to-`id` table. Required because audit prose uses skill names that
  are not always `id`s -- e.g. the PBIR adapter's entry is
  `pbir-authoring-adapter-skill` while `pbir-authoring-adapter` appears in six
  other entries only as a `references.skill` value (SC-003). Every later task
  MUST edit by resolved `id`, never by skill-name match. -- **done**: evidence/id-resolution.md -- 3 traps found, incl. pbir-authoring-adapter having NO exact id and powerbi-workflows not being a manifest entry at all
- [x] T005 [P] Record the pre-existing fail-open at
  `src/seshat/capability_inventory.py:35-43` into
  `evidence/known-findings.md`: the five axis constants
  (`_LIFECYCLE_STATES`, `_AUTHORITIES`, `_SURFACES`, `_REQUIREMENTS`,
  `_PROVENANCES`) are referenced nowhere else in the module and enforce nothing,
  demonstrated by the live `surface: product-module` value that is absent from
  `_SURFACES` and causes no failure. Deliverable: the file. This discharges
  FR-010's affirmative half -- record the finding, do not fix it (OD-3).
  -- **done**: evidence/known-findings.md -- KF-1 five dead constants proven dead
  (each appears once, at its own definition; live `product-module` violates
  `_SURFACES` with no failure), KF-2 no spec-kit re-vendor path

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
- [ ] T013 Add a **behavioral** test for FR-008 clause 1: construct an in-memory
  entry carrying `ownership: {ownership_confidence: "high"}` and assert
  `find_axis_violations` (or the O6 check directly) returns a problem naming that
  key. Deliverable: a test that exercises the real detector.
  **Not** a list-versus-list comparison of the FR-001 vocabulary against
  `NUMERIC_FIELD_HINTS` — that form cannot fail unless someone edits the test's
  own list, so it would restate the risk rather than catch it. The protection is
  the pre-existing `_axis_numeric_field_names`
  (`tests/unit/_capability_oracle.py:451-456`); this task proves it fires on an
  ownership-shaped field.
- [ ] T015 Add a FAILING-then-passing test for FR-002a: an entry with no
  `ownership.capability_owner` must be rejected. Deliverable: the test plus the
  oracle check. This is what makes absence non-meaningful and a half-landed
  migration honest rather than misleading.
- [ ] T016 Implement FR-011, the reader: add `capability_owner`,
  `upstream_project`, and `seshat_delta` to `_RECORD_FIELDS` /
  `InventoryRecord` / `_project_record` in
  `src/seshat/capability_inventory.py`, and mirror them into
  `DECLARED_RECORD_FIELDS` in `tests/unit/_capability_oracle.py`. Deliverable:
  `python -m seshat.capability_inventory` renders the three fields, and the
  closed-schema assertion at `tests/unit/test_capability_inventory.py:40` passes
  with the widened set. **Leave the five dead constants at
  `capability_inventory.py:35-43` untouched** (FR-010, OD-3).
- [ ] T014 Run the gate set. Deliverable: all green, and the bundle digests from
  T002 **unchanged** — Phase 1 touches no manifest entry, so this is the
  inertness proof.

## Phase 2 -- Pilot the four known wrappers (proves FR-004 on real data)

- [ ] T020 Classify the `dbt-transformation-adapter` entry (by `id` resolved in
  T004) as `seshat-adapter`, upstream `dbt Labs`. Per FR-007,
  `upstream_reference` names the surface actually wrapped -- the
  `dbt-agent-skills` bundle (`catalog.py:168-175`) and/or `dbt-mcp`
  (`:176-186`) -- **not** `dbt-core`/`dbt-postgres` (`:151-167`), which are
  operator-environment runtime dependencies rather than the wrapped surface.
  Deliverable: the entry, with a non-empty `seshat_delta`.
- [ ] T021 [P] Classify the `dagster-orchestration-adapter` entry as
  `seshat-adapter`, upstream `Dagster`, with `upstream_reference` matching the
  `dagster` PyPI component (`catalog.py:191-198`). Per FR-007 do **not** invent a
  coordinate for `seshat-dagster-adapter` (`:199-205`) or `dagster-skills`
  (`:206-212`) -- both are Seshat-bundled and carry no coordinate. Deliverable:
  the entry.
- [ ] T022 [P] Classify `pbi-mcp-doctor`, upstream Microsoft, cross-checked
  against `catalog.py:224-235`. Deliverable: the entry, with the upstream's
  preview/pre-GA status reflected in `update_policy` as a quoted string
  (FR-008 clause 2).
- [ ] T023 [P] Classify the PBIR adapter entry — manifest `id`
  `pbir-authoring-adapter-skill`, per T004, **not** the six entries that merely
  carry `references.skill: pbir-authoring-adapter` — with
  `upstream_surface: format` (FR-003), since PBIR is an upstream-owned format
  with no executable surface. Deliverable: the entry.
- [ ] T024 Run the gate set. Deliverable: bundle digests **identical** to T002
  with four entries now carrying the axis — the empirical proof of FR-004 and
  SC-004, at four entries rather than 102.

## Phase 3 -- Knowledge roots and governance set (mechanical)

- [ ] T030 Classify the six `skills/` roots as `seshat-domain-knowledge`, each
  with `canonical_source` naming its authored path (FR-005). Deliverable: six
  entries. Do **not** add a `generated_targets` field — it was removed from the
  spec because destinations are owned by
  `distribution/public-knowledge-allowlist.yaml` and a hand-written copy would
  drift silently.
- [ ] T031 Classify the readiness/evidence/approval set as
  `seshat-governance`, per `docs/capabilities/ownership-audit.md` section 4.
  Deliverable: the entries, with no `upstream_project` (none exists).
- [ ] T032 Run the gate set. Deliverable: all green, digests unchanged.

## Phase 4 -- Remainder, in reviewable batches

- [ ] T040 Classify the orchestrator/front-door set as `seshat-orchestrator`
  (FR-002) per the audit's KEEP section. Deliverable: the entries; one commit.
  These carry no `upstream_project` and need no `seshat_delta` -- they coordinate
  Seshat's own verbs rather than wrapping an upstream surface.
- [ ] T041 Classify the Power BI layer entries. Deliverable: the entries.
  `powerbi-dashboard-design` and `powerbi-workflows` receive an `overlap_note`
  naming each other (US3) — advisory only, merging nothing.
- [ ] T042 Classify the remaining entries, **enumerated from the manifest rather
  than from the audit**. The audit names only 41 of 102 `id`s, so 61 entries have
  no audit-derived classification -- 47 `cli`, 5 `docs`, 4 `skill`, 2
  `execution-adapter`, and one each of `product-module`, `plugin`,
  `human-artifact`. Work the manifest in reviewable batches, one commit each.
  Deliverable: every entry declared. Use the FR-002 tokens added for the
  previously-uncovered surfaces:
  - `surface: product-module` -> `seshat-product-module`
  - `surface: human-artifact` -> `human-deliverable`
  - spec-only `surface: docs` -> `specified-not-built`
  - genuinely undecidable -> `unclassified` with an entry-specific reason
- [ ] T042a Classify the `speckit-*` aggregate entry as `vendored-upstream` per
  the resolved OD-1: `upstream_project` `github/spec-kit`, `upstream_reference`
  the pinned `"0.8.10"` (quoted -- FR-008 clause 2), and `update_policy`
  recording the `specify init` invocation. Deliverable: the entry, and a note in
  `evidence/known-findings.md` that **no re-vendor/upgrade path is recorded**
  (no lockfile, no `specify upgrade` record) -- the residual fork-tax gap.
  Note the count is **14** skills, not 12.
- [ ] T042b Classify the four dev-workflow skills as `seshat-governance` per the
  resolved OD-2, each with the `seshat_delta` stated in the spec's OD-2 table.
  Deliverable: four entries, each with a non-empty delta.
- [ ] T043 Run the gate set. Deliverable: all green, digests unchanged.

## Phase 5 -- Closeout

- [ ] T050 Write the `unclassified`-token census into `evidence/unclassified.md`:
  every entry whose `capability_owner` is `unclassified`, with its
  entry-specific reason. Deliverable: the file (SC-001). Note this is now a
  census of an explicit token, not a list of silent omissions — FR-002a means no
  entry can be missing the field. OD-1 and OD-2 are resolved, so neither is a
  valid reason for leaving an entry unclassified.
- [ ] T051 Verify SC-002 mechanically: every `seshat-adapter` entry carries a
  non-empty `seshat_delta`. Deliverable: the oracle passing, plus the count.
- [ ] T052 Verify SC-007 mechanically: no key name anywhere in the manifest
  contains a `NUMERIC_FIELD_HINTS` substring, and no ownership value is a bare
  numeric scalar. Deliverable: O6 green plus the grep output.
- [ ] T053 Update `docs/capabilities/README.md` to document the ownership axis
  and its token sets (FR-001, FR-002, FR-003 — the human-readable counterpart of
  the vocabulary those FRs define). Deliverable: the README section. **Not** a
  value-by-value contract table the oracle would then have to agree with — the
  oracle owns validation (FR-009), and a second normative list is exactly the
  duplicate authority this spec exists to avoid.
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
- **No shipping `capabilities.yaml` inside the bundles.** FR-011 renders three
  fields through the existing inventory surface; putting the manifest itself in
  the bundles would change every bundle digest and force a drift-gate
  re-baseline. Out of scope.
- **No re-litigating OD-1, OD-2, or OD-3.** All three are resolved by owner
  ruling 2026-08-07 and recorded in the spec's Decisions section. Implement the
  rulings (T042a, T042b, T005); do not reopen them.
- **No building the spec-kit re-vendor/upgrade path.** OD-1 surfaced that gap as
  real but out of scope here; T042a only records it.
- **No deleting, merging, or consolidating any capability.**
- **No promoting this spec into the `<!-- SPECKIT -->` fence** as part of
  implementation. Fence movement is an owner action.

## Dependencies

- T010, T011 precede T012 (RED before GREEN).
- Phase 1 precedes Phase 2: the validation must exist before data relies on it.
- T024 is the FR-004 proof gate; Phases 3-5 assume it passed.
- T050 depends on Phases 2-4 being complete, since it enumerates what remains.
- OD-1 and OD-2 block only their own entries in T042/T050, never a whole phase.
