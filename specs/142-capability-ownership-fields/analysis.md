# Cross-artifact analysis: spec 142

**Artifacts**: `spec.md`, `plan.md`, `tasks.md`

**Performed**: 2026-08-07, read-only, by an independent reviewer that did not
author the artifacts.

**Method**: FR/SC coverage, internal-contradiction check, and adversarial
verification of every `file:line` claim against the actual tree. The factual
axis was treated as the highest-value check precisely because the artifacts
assert their claims are "measured facts, not assumptions" -- a specific citation
is not a correct one.

---

## Result

**12 findings: 1 CRITICAL, 3 HIGH, 5 MEDIUM, 3 LOW.** All 12 are resolved in the
artifacts as committed. Every fix was independently re-verified against the tree
rather than accepted from the reviewer's report.

## CRITICAL

### C1 -- FR-002's token set omitted a token its own tasks used

`FR-002` declared a **closed** five-token `capability_owner` set. But
`plan.md`'s Constitution table and `tasks.md` T040 both used a sixth,
`seshat-orchestrator`, drawn from the audit's KEEP section (12 entries).

Consequence had this shipped: T040 would write a value that the oracle built in
T012 -- from the same spec -- would reject. Phase 4 was unexecutable as written.
The spec contradicted its own task list.

**Verified**: `grep` confirmed exactly five tokens in FR-002 and exactly one use
of `seshat-orchestrator`, in T040.

**Resolved**: FR-002 now declares six tokens, and defines the boundary against
`seshat-adapter` -- an orchestrator coordinates *Seshat's own* verbs (no
`upstream_project`, no `seshat_delta`); an adapter wraps an *upstream* surface.
T040 now cites FR-002 and states that consequence.

This was an authoring defect in the spec, not a reviewer misreading. Worth
noting that every mechanical gate was green while it stood: `seshat check`,
kit-lint, and 201 contract tests cannot detect a spec contradicting itself.

## HIGH

### H1 -- The `catalog.py:61-67` claim was wrong

Claimed the range "names dbt Labs, Microsoft, and Dagster with coordinates and
channels". It does not: `:61-67` is `ALLOWLISTED_SOURCES`, a name-to-URL map with
no channels and no Dagster entry distinguishable from any other PyPI source. The
per-component records with coordinates and channels begin at `:149`.

**Verified**: read `:61-67` directly -- five string values, all URLs.

**Resolved**: the passage now describes `ALLOWLISTED_SOURCES` accurately at
`:61-67` and cites `:149` onward for the component records.

### H2 -- The `.specify/feature.json` claim was self-falsified

`spec.md` stated the file "currently points at `specs/138-agent-driven-bundle`".
By the time the artifacts were committed it pointed at *this* spec -- repointed
in the same commit, by the fence move performed under the same owner ruling.

**Resolved**: the Non-goal is restated as what actually matters. Being the fence
target is **not** ratification: the fence text says implementation is NOT
permitted while this spec is Draft, and a named human must ratify `spec.md`
before any task starts. The substance of the original Non-goal survives; only
the false factual premise is gone.

### H3 -- SC-003 named an `id` that does not exist

`pbir-authoring-adapter` is not a manifest `id`. The entry is
`pbir-authoring-adapter-skill`; the bare name appears in six *other* entries only
as a `references.skill` value. An implementer matching on the prose name would
have edited the wrong entries.

**Verified**: `grep` on the manifest -- the bare name appears at `:412` as a
`references.skill` value, never as an `id`.

**Resolved**: SC-003 now warns that audit prose uses skill names rather than
`id`s and requires resolving the `id` first. New task **T004** produces a
name-to-`id` table before any entry is edited, and T023 names the correct `id`
explicitly.

## MEDIUM

### M1 -- Bundle-hash citation was wrong

`plan.md` cited `export_agent_bundles.py:455-456`. Actual locations:
`output_sha256` `:583`, `source_sha256` `:586`, `manifest_digest` `:639`.
**Resolved** with all three verified line numbers. The *conclusion* was correct
-- the hashes cover allowlist-sourced file bytes, never `capabilities.yaml` --
so FR-004 stands; only the pointer was wrong.

### M2 -- FR-005 cited a `def` line as enforcement

`:602` is `build_bundle`'s signature. Enforcement is `_validate_source` (`:319`),
`_validate_entry_policy` (`:358`), `_record_destinations` (`:397`).
**Resolved**: FR-005 now cites the driver and the three checks separately.

### M3 -- FR-007 had nothing to bind for bundled components

T021's cited range covers `seshat-dagster-adapter` and `dagster-skills`, which
are Seshat-bundled and carry **no** `coordinate`. FR-007's "MUST match the
coordinate declared there" was unsatisfiable for two of three components in
range -- an instruction to invent a value.

**Resolved**: FR-007 gains two explicit limits -- omit `upstream_reference` for
bundled components rather than inventing one, and where a project ships several
coordinates, name the one actually consumed. T021 now says which is which.

### M4 -- FR-010's affirmative half had no covering task

FR-010 requires the pre-existing dead-constant fail-open be *recorded as a known
finding*. Only the prohibition ("do not revive them") was covered; OD-3 defers
the fix, so nothing produced the required record.

**Resolved**: new task **T005** writes `evidence/known-findings.md` capturing the
five dead constants and the live `surface: product-module` value that proves they
enforce nothing.

### M5 -- SC-001 had no floor

As written, SC-001 was satisfiable by classifying **zero** of 102 entries and
writing 102 boilerplate "unclassified" reasons -- passing the letter while
defeating the feature.

**Resolved**: SC-001 now caps unclassified entries at those blocked on OD-1/OD-2
and rejects a repeated boilerplate reason.

## LOW

### L1 -- T020's coordinate ambiguity
Cited range excluded `dbt-core`/`dbt-postgres`, leaving unstated which of three
dbt coordinates to match. **Resolved** in T020 alongside M3.

### L2 -- T053 was an orphan task
Mapped to no FR and disclaimed being FR-009 evidence. **Resolved**: T053 now
cites FR-001/FR-002/FR-003 as the human-readable counterpart of that vocabulary,
and states why it deliberately is *not* a second normative list.

### L3 -- Phase-count mismatch
`plan.md` had 5 phases, `tasks.md` 6. Not a contradiction -- Phases 1-5 agree
exactly; `tasks.md` adds a decision-free Phase 0. **Resolved**: `plan.md` now
names Phase 0 and its purpose.

## Claims verified CORRECT (no change needed)

Recorded so a later reader knows these were checked, not assumed:

- `capability_inventory.py:172-186` (fixed-key permissive projection) -- exact.
- `capability_inventory.py:35-43` (five dead constants) -- exact.
- `_capability_oracle.py:441-448` and `:451-456` (O6 checks) -- exact.
- `NUMERIC_FIELD_HINTS` = `("score","maturity","confidence","completeness","health")` -- exact.
- `allowlist_derivation.py` reads only four manifest keys -- correct.
- 102 manifest entries -- exact.
- `test_capability_inventory.py:513-526` (c086/retail_store_sales literal ban) -- exact.
- Six `skills/` knowledge roots -- exactly six.
- T041's MERGE-candidate pairing -- matches the audit verbatim.
- The RS1 warning is live and pre-existing -- confirmed by running the gate.
- All constitution principle names and numbers -- real and correctly numbered.
- `edfab33` and `DECLARED_RECORD_FIELDS` -- both real.

## Verdict

The reviewer's verdict on the artifacts *as first written* was **not ready to
ratify**, on C1 plus H1-H3.

All 12 findings are now resolved and re-verified. The core design was never in
question and survived adversarial review intact: an additive metadata axis on the
existing control plane, validated by the existing oracle, with no new gate and no
new score. What failed review was citation precision and one closed-set omission
-- both fixed.

**Remaining blockers to ratification are human, not technical**: OD-1 (is
`speckit-*` vendored upstream, a possible Principle II finding), OD-2 (how to
class the INSPECT dev-workflow skills), OD-3 (whether the dead constants get
their own spec). None can be self-answered.

This analysis grants no approval and does not ratify. It records that the package
is internally consistent and factually grounded as of `2026-08-07`.
