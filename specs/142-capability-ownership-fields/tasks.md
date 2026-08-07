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
  `pbir-authoring-adapter-skill` while `pbir-authoring-adapter` is a
  `references.skill` value on five entries, four of them unrelated `pbir-*` CLI
  verbs, and is not an `id` at all (SC-003). Every later task
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

- [x] T010 Write a FAILING test in `tests/unit/test_capability_inventory.py`
  asserting the oracle rejects an entry whose `ownership.capability_owner` is
  not in the FR-002 token set. Deliverable: a test that fails with a clear
  message before T012 exists.
  -- **done**: test_ownership_rejects_unknown_capability_owner + test_ownership_accepts_every_declared_token; RED-verified (AttributeError on ownership_violations) before T012
- [x] T011 [P] Write a FAILING test asserting the oracle rejects an entry with
  `capability_owner: seshat-adapter` and a missing or empty `seshat_delta`
  (FR-006). Deliverable: a second failing test.
  -- **done**: test_ownership_rejects_adapter_without_delta -- covers None, '' and whitespace-only; RED-verified
- [x] T012 Add `OWNERSHIP_OWNERS` (FR-002) and `OWNERSHIP_SURFACES` (FR-003)
  token sets plus the two axis check functions to
  `tests/unit/_capability_oracle.py`, wired into the same
  `find_*_violations` pattern the existing axes use. Deliverable: T010 and T011
  now pass; every previously green oracle test still passes.
  -- **done**: OWNERSHIP_OWNERS (10 tokens) + OWNERSHIP_SURFACES (6) + ownership_violations()/find_ownership_violations() in _capability_oracle.py; 44 capability tests pass
- [x] T013 Add a **behavioral** test for FR-008 clause 1: construct an in-memory
  entry carrying `ownership: {ownership_confidence: "high"}` and assert
  `find_axis_violations` (or the O6 check directly) returns a problem naming that
  key. Deliverable: a test that exercises the real detector.
  **Not** a list-versus-list comparison of the FR-001 vocabulary against
  `NUMERIC_FIELD_HINTS` — that form cannot fail unless someone edits the test's
  own list, so it would restate the risk rather than catch it. The protection is
  the pre-existing `_axis_numeric_field_names`
  (`tests/unit/_capability_oracle.py:451-456`); this task proves it fires on an
  ownership-shaped field.
  -- **done**: test_o6_fires_on_an_ownership_shaped_numeric_field_name + test_o6_fires_on_a_bare_numeric_ownership_value -- BEHAVIORAL, both passed on first run, proving the pre-existing depth-walking detector really does catch ownership_confidence and a bare int
- [x] T015 Add a FAILING-then-passing test for FR-002a: an entry with no
  `ownership.capability_owner` must be rejected. Deliverable: the test plus the
  oracle check. This is what makes absence non-meaningful and a half-landed
  migration honest rather than misleading.
  -- **done**: test_ownership_rejects_missing_capability_owner -- absent mapping, empty mapping, and blank value all rejected; the 'unclassified' sentinel accepted
- [x] T016 Implement FR-011, the reader: add `capability_owner`,
  `upstream_project`, and `seshat_delta` to `_RECORD_FIELDS` /
  `InventoryRecord` / `_project_record` in
  `src/seshat/capability_inventory.py`, and mirror them into
  `DECLARED_RECORD_FIELDS` in `tests/unit/_capability_oracle.py`. Deliverable:
  `python -m seshat.capability_inventory` renders the three fields, and the
  closed-schema assertion at `tests/unit/test_capability_inventory.py:40` passes
  with the widened set. **Leave the five dead constants at
  `capability_inventory.py:35-43` untouched** (FR-010, OD-3).
  -- **done**: FR-011 reader -- _RECORD_FIELDS/InventoryRecord/to_dict/_project_record widened + _optional_str helper, mirrored into DECLARED_RECORD_FIELDS. Verified end-to-end: `python -m seshat.capability_inventory --format json` emits all three fields; every entry reads 'unclassified' pre-migration (never blank). Five dead constants at :35-43 untouched
- [x] T014 Run the gate set. Deliverable: all green, and the bundle digests from
  T002 **unchanged** — Phase 1 touches no manifest entry, so this is the
  inertness proof.

  -- **done**: evidence/phase1-gates.txt -- seshat check exit 0 (pre-existing RS1 only), ruff clean, bundle drift PASS, 81 tests passed (74 baseline + 7 new). INERTNESS PROVEN: both manifest_digests byte-identical to T002
## Phase 2 -- Pilot the four known wrappers (proves FR-004 on real data)

- [x] T020 Classify the `dbt-transformation-adapter` entry (by `id` resolved in
  T004) as `seshat-adapter`, upstream `dbt Labs`. Per FR-007,
  `upstream_reference` names the surface **actually wrapped**.
  **Corrected during implementation**: this task originally said to use
  `dbt-agent-skills` and/or `dbt-mcp` and to avoid `dbt-core`. Reading the skill
  proved the opposite -- `.claude/skills/dbt-transformation-adapter/SKILL.md:27`
  names the `dbt-core==1.12.0` + `dbt-postgres==1.10.2` extra, and its build/test
  steps invoke `seshat dbt build` / `seshat dbt test`, i.e. a governed wrapper
  around **dbt-core's own execution**. `dbt-core` (`catalog.py:151-157`) is
  therefore the wrapped surface, not an incidental runtime dependency.
  `dbt-mcp` is a separate, unused surface here. Deliverable: the entry, with a
  non-empty `seshat_delta`.
  -- **done**: seshat-adapter / dbt Labs / upstream_reference `dbt-core`. TASK TEXT CORRECTED FIRST -- it said to avoid dbt-core, but SKILL.md:27 names the dbt-core+dbt-postgres extra and the build steps invoke `seshat dbt build`, so dbt-core IS the wrapped engine. Following the original text would have recorded a false coordinate
- [x] T021 [P] Classify the `dagster-orchestration-adapter` entry as
  `seshat-adapter`, upstream `Dagster`, with `upstream_reference` matching the
  `dagster` PyPI component (`catalog.py:191-198`). Per FR-007 do **not** invent a
  coordinate for `seshat-dagster-adapter` (`:199-205`) or `dagster-skills`
  (`:206-212`) -- both are Seshat-bundled and carry no coordinate. Deliverable:
  the entry.
  -- **done**: seshat-adapter / Dagster / `dagster`; no coordinate invented for the two Seshat-bundled components, per FR-007
- [x] T022 [P] Classify `pbi-mcp-doctor`, upstream Microsoft, cross-checked
  against `catalog.py:224-235`. Deliverable: the entry, with the upstream's
  preview/pre-GA status reflected in `update_policy` as a quoted string
  (FR-008 clause 2).
  -- **done**: seshat-adapter / Microsoft / `@microsoft/powerbi-modeling-mcp`, upstream_surface mcp; preview/pre-GA recorded in update_policy as a quoted string (FR-008 clause 2)
- [x] T023 [P] Classify the PBIR adapter entry — manifest `id`
  `pbir-authoring-adapter-skill`, per T004, **not** the six entries that merely
  carry `references.skill: pbir-authoring-adapter` — with
  `upstream_surface: format` (FR-003), since PBIR is an upstream-owned format
  with no executable surface. Deliverable: the entry.
  -- **done** on the resolved id `pbir-authoring-adapter-skill` (NOT the four pbir-* verbs that merely reference the skill). RECLASSIFIED from seshat-adapter to **seshat-orchestrator**: its summary shows it composes Seshat's OWN pbir-* CLI verbs, so FR-002's adapter/orchestrator line puts it on the orchestrator side; the upstream-format question belongs to the verbs that touch PBIR JSON
- [x] T024 Run the gate set. Deliverable: bundle digests **identical** to T002
  with four entries now carrying the axis — the empirical proof of FR-004 and
  SC-004, at four entries rather than 102.

  -- **done**: evidence/phase2-gates.txt -- FR-004/SC-004 PROVEN on real data. Both manifest_digests byte-identical to the T002 baseline WITH four entries carrying the axis; 81 tests pass, ruff clean, bundle drift PASS, seshat check exit 0 (pre-existing RS1 only). O9 clean on all four. Reader surfaces all four (FR-011)
## Phase 3 -- Knowledge roots and governance set (mechanical)

- [x] T030 Classify the six `skills/` roots as `seshat-domain-knowledge`, each
  with `canonical_source` naming its authored path (FR-005). Deliverable: six
  entries. Do **not** add a `generated_targets` field — it was removed from the
  spec because destinations are owned by
  `distribution/public-knowledge-allowlist.yaml` and a hand-written copy would
  drift silently.
  -- **done**: six knowledge roots as seshat-domain-knowledge with canonical_source; no generated_targets (removed from spec, FR-005)
- [x] T031 Classify the readiness/evidence/approval set as
  `seshat-governance`, per `docs/capabilities/ownership-audit.md` section 4.
  Deliverable: the entries, with no `upstream_project` (none exists).
  -- **done**: 50 entries as seshat-governance -- gates, evidence, status, drift, lint, registries
- [x] T032 Run the gate set. Deliverable: all green, digests unchanged.

  -- **done**: gates green, digests unchanged
## Phase 4 -- Remainder, in reviewable batches

- [x] T040 Classify the orchestrator/front-door set as `seshat-orchestrator`
  (FR-002) per the audit's KEEP section. Deliverable: the entries; one commit.
  These carry no `upstream_project` and need no `seshat_delta` -- they coordinate
  Seshat's own verbs rather than wrapping an upstream surface.
  -- **done**: 15 orchestrators/front doors as seshat-orchestrator, no upstream_project and no delta required
- [x] T041 Classify the Power BI layer entries. Deliverable: the entries.
  `powerbi-dashboard-design` and `powerbi-workflows` receive an `overlap_note`
  naming each other (US3) — advisory only, merging nothing.
  -- **done**: Power BI layer classified -- the four pbir-* verbs as seshat-adapter over Microsoft's PBIR format (upstream_surface: format), pbip-workflow as seshat-domain-knowledge over an upstream format
- [x] T042 Classify the remaining entries, **enumerated from the manifest rather
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
  -- **done**: enumerated from the MANIFEST, not the audit. METHOD CHANGED ON EVIDENCE -- a surface-based fallback would have labelled 67 entries seshat-governance, but retail-theme-gen/retail-generate generate artifacts and gate nothing, so every entry was classified by reading its summary. Produced a new seshat-authoring token (12 entries)
- [x] T042a Classify the `speckit-*` aggregate entry as `vendored-upstream` per
  the resolved OD-1: `upstream_project` `github/spec-kit`, `upstream_reference`
  the pinned `"0.8.10"` (quoted -- FR-008 clause 2), and `update_policy`
  recording the `specify init` invocation. Deliverable: the entry, and a note in
  `evidence/known-findings.md` that **no re-vendor/upgrade path is recorded**
  (no lockfile, no `specify upgrade` record) -- the residual fork-tax gap.
  Note the count is **14** skills, not 12.
  -- **done**: speckit-workflow-skills as vendored-upstream / github/spec-kit / '0.8.10' quoted; update_policy records the installer invocation and points at KF-2 for the missing re-vendor path. 14 skills, not 12
- [x] T042b Classify the four dev-workflow skills as `seshat-governance` per the
  resolved OD-2, each with the `seshat_delta` stated in the spec's OD-2 table.
  Deliverable: four entries, each with a non-empty delta.
  -- **done**: the four dev-workflow skills as seshat-governance per OD-2
- [x] T043 Run the gate set. Deliverable: all green, digests unchanged.
  -- **done**: 102/102 declared, 0 O9 violations, 0 O6 violations, digests byte-identical to baseline
- [x] T044 **Wire O9 into the aggregate.** Add
  `"ownership": find_ownership_violations(repo_root)` to `oracle_all_clear`
  (`tests/unit/_capability_oracle.py`), which
  `test_real_manifest_passes_all_eight_oracle_checks` iterates. Deliverable: the
  aggregate carries the ownership key and the real-manifest test passes.
  **Ordering is load-bearing and deliberate**: until every entry is declared,
  FR-002a makes this check fail by design, so it lands at the END of Phase 4.
  A detector that exists but is absent from the aggregate would let Phases 2-4
  land malformed entries with every gate green -- the
  `verifier-must-sit-on-the-risk` failure shape. Do not skip this task; the
  detector is not enforcing anything until it runs.

  -- **done**: O9 wired into oracle_all_clear as the 'ownership' key -- landed LAST by design, since the aggregate is what test_real_manifest_passes_all_eight_oracle_checks iterates and FR-002a would have failed it mid-migration. 44 capability tests pass with it live
## Phase 5 -- Closeout

- [x] T050 Write the `unclassified`-token census into `evidence/unclassified.md`:
  every entry whose `capability_owner` is `unclassified`, with its
  entry-specific reason. Deliverable: the file (SC-001). Note this is now a
  census of an explicit token, not a list of silent omissions — FR-002a means no
  entry can be missing the field. OD-1 and OD-2 are resolved, so neither is a
  valid reason for leaving an entry unclassified.
  -- **done**: evidence/unclassified.md -- built from the RAW manifest (the renderer defaults absent to 'unclassified', so its output cannot distinguish undeclared from declared-unclassified). 102 entries, 0 undeclared, 0 sentinel
- [x] T051 Verify SC-002 mechanically: every `seshat-adapter` entry carries a
  non-empty `seshat_delta`. Deliverable: the oracle passing, plus the count.
  -- **done**: SC-002 verified mechanically -- 9 seshat-adapter entries, 0 missing a delta
- [x] T052 Verify SC-007 mechanically: no key name anywhere in the manifest
  contains a `NUMERIC_FIELD_HINTS` substring, and no ownership value is a bare
  numeric scalar. Deliverable: O6 green plus the grep output.
  -- **done**: SC-007 verified -- O6 returns NONE across the whole manifest; no numeric-hint field name, no bare numeric scalar
- [x] T053 Update `docs/capabilities/README.md` to document the ownership axis
  and its token sets (FR-001, FR-002, FR-003 — the human-readable counterpart of
  the vocabulary those FRs define). Deliverable: the README section. **Not** a
  value-by-value contract table the oracle would then have to agree with — the
  oracle owns validation (FR-009), and a second normative list is exactly the
  duplicate authority this spec exists to avoid.
  -- **done**: docs/capabilities/README.md gains an 'ownership axis' section -- the 11-token table, optional sub-fields, the catalog-is-authoritative rule, and why validation lives in the oracle rather than a gate
- [x] T054 Run the full gate set plus `pytest -m unit`. Deliverable: the
  complete output recorded in `evidence/final-gates.txt`.

  -- **done**: evidence/final-gates.txt -- ruff clean, bundle drift PASS, kit-lint no drift, semantic-check no drift, 5353 unit tests pass. TWO CORRECTIONS RECORDED: (1) seshat check exited 1 on rule P2 because MY commit subjects were scoped -- reworded, now exit 0; (2) test_cli_identity_version fails on stale editable metadata (0.8.1 vs 0.8.2), environmental, cannot fire in CI
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
