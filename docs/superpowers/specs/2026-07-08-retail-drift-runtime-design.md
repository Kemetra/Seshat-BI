# retail drift runtime — design (F014 detector, spec 015 deferred runtime)

**Date:** 2026-07-08
**Feature branch:** `worktree-015-retail-drift-runtime`
**Advances:** roadmap F014 (Source Drift Detector), the RUNTIME that spec
`015-source-drift-detector` designed and explicitly deferred.
**Emits the contract:** `schemas/source-drift-findings.schema.json` (the F014 seam,
PR #228 — verified internally consistent before this build).

## 1. What this is (and what spec 015 already settled)

Spec 015 shipped the *design* slice: the nine-class drift taxonomy
(`docs/readiness/source-drift.md`), the human report template
(`templates/source-drift-report.md`), the re-profile/compare checklist, and — via
PR #228 — the machine-readable findings contract
(`schemas/source-drift-findings.schema.json`). It deliberately deferred the
**runtime**: the comparator that reads a baseline profile, diffs it against an
observed re-profile, classifies the differences, and emits the findings.

This design is that runtime. It does **not** re-derive the taxonomy, the status
model, the Principle-V seams, or the output shape — all of those are ratified in
spec 015 and pinned by the schema. It only decides the three things spec 015 left
open: **(a)** how the baseline profile becomes machine-comparable, **(b)** the pure
diff/classify/emit logic, and **(c)** the CLI surface.

## 2. Scope

**In scope (this build, full end-to-end per owner instruction):**
1. `src/seshat/drift.py` — the pure, I/O-free comparator + classifier + schema
   emitter. `ProfileResult × (ProfileResult | None) → findings dict`.
2. `src/seshat/source_profile_reader.py` — parses a **template-conformant**
   committed `source-profile.md` into a `ProfileResult`-equivalent baseline.
3. `retail drift` CLI command — `cli/commands/drift.py` + parser + dispatch row,
   mirroring `validate`'s two-mode (deferred-live vs live) structure.

**Out of scope (unchanged from spec 015):**
- Any change to the nine classes, the status enum, or the schema.
- A numeric drift "score" (hard rule #9 — forbidden).
- Auto-resolution of any Principle-V class (grain/PK, returns, PII, identity).
- Continuous/scheduled drift watch (a later orchestration concern).

## 3. Architecture (advisor-corrected)

```
baseline source-profile.md  ──(source_profile_reader)──►  ProfileResult (baseline)
                                                                  │
observed: live re-profile ──(retail.profile.profile)──►  ProfileResult (observed)
          OR no DSN ─────────────────────────────────►   None                │
                                                                  ▼           ▼
                                        drift.classify_drift(baseline, observed)
                                                                  │
                                                                  ▼
                                        drift.derive_status(findings)
                                                                  │
                                                                  ▼
                                        drift.to_findings_dict(...)  ──► JSON matching
                                                                         the F014 schema
```

**Rejected alternatives (recorded so the decision is auditable):**
- *Structured JSON sidecar baseline* — rejected: it invents a machine baseline the
  human never approved, silently desyncing from spec 015's model that "the baseline
  IS the committed `source-profile.md` that earned pass." Unratified architecture.
- *Emit observed to `.md` then re-parse both sides through one parser* — rejected:
  the baseline is already hand-authored prose that exists on disk; it can never be
  machine-generated retroactively, so the symmetry never materialises. The observed
  side already has a `ProfileResult` in hand from `profile.py` — round-tripping it
  through markdown adds an emitter and a write step for no benefit.
- **Chosen:** parse the committed baseline `.md` directly; take observed as a live
  `ProfileResult` (or `None`); diff two structures. Simplest, faithful to 015.
  **This baseline-representation decision is REVERSIBLE** — if a machine-readable
  profile artifact is later ratified, the reader swaps for a loader with no change
  to `drift.py`'s pure core.

## 4. The parser's honesty boundary (a real finding, not a hypothetical)

The two filled baselines in the tree have **different markdown structures**:
- `mappings/retail_store_sales/source-profile.md` follows the template: a
  `## Per-column profile` table with `Column | Type as landed | Missingness
  ('' OR NULL, count / %) | Distinct cardinality | Candidate key? | Notes`, plus a
  `## Candidate grain & candidate PK` section with the uniqueness proof.
- `mappings/demo_sample_orders/source-profile.md` uses a freeform 3-column layout
  (`Column | Kind | Notes`) with **no missingness or cardinality columns** — the raw
  material for `missingness_shift`/`cardinality_shift` is not machine-extractable.

Therefore the reader parses **only the template-conformant structure** and, for a
non-conformant baseline, **reports it as uncomparable rather than fabricating a
diff** — this is exactly the schema/taxonomy's "profile schema-version skew" edge
case ("compare only the fields both profiles carry; record which were
uncomparable"). This keeps the runtime honest: it never invents a measurement the
baseline doesn't actually record.

## 5. Which classes this runtime can measure honestly

`ProfileResult` (from `retail.profile`) carries: per-column `name`,
`missing_count`, `missing_pct`, `distinct_cardinality`, and a `PkProof`
(`total`, `distinct_pk`, `null_pk`, `is_unique`). From that, the runtime **measures**:

| Class | Measured from | Default severity |
|-------|---------------|------------------|
| `column_added` | name present in observed, absent in baseline | warning |
| `column_removed` | name present in baseline, absent in observed | blocked |
| `column_retyped` | type differs (when the baseline records a type) | warning / blocked if key/measure |
| `missingness_shift` | `missing_pct` moved beyond tolerance | warning |
| `cardinality_shift` | `distinct_cardinality` moved beyond tolerance | warning |
| `grain_pk_drift` | `PkProof.is_unique` flipped, or null_pk appeared | **blocked (Principle-V)** |

The remaining three classes (`returns_rule_drift`, `pii_surface_drift`,
`semantic_pair_drift`) require inputs a mechanical `ProfileResult` does not carry
(the authoritative returns column, a PII ruling, a code/label 1:1 relationship).
The runtime **does not fabricate** them. When the baseline profile records enough
to *notice* a candidate (e.g. a dropped-PII column name reappearing), it raises a
`principle_v_handoff` entry for the named owner — it never classifies or decides.
This respects hard rule #9 (no measure it can't back with data) and Principle V.

## 6. Deferred-live fail-closed path

When no DSN / no observed re-profile is available: `observed = None` →
`classify_drift` returns no findings, `derive_status` returns
`pending_live_reprofile`, and `to_findings_dict` sets `observed.available = false`.
The CLI prints a `validate`-style message to stderr and does **not** fabricate a
comparison (Principle VIII; matches the template's `[PENDING LIVE RE-PROFILE]` +
`warning` posture).

## 7. Testing (TDD, `pytest.mark.unit`, driver-free)

- **Classifier:** table-driven — two `ProfileResult`s differing by exactly one
  class → assert class + severity + status. One test per class.
- **Schema conformance:** every emitted dict validates against the *real*
  `schemas/source-drift-findings.schema.json` (jsonschema Draft 2020-12).
- **Fail-closed:** `observed=None` → `pending_live_reprofile`, empty findings,
  `observed.available=false`.
- **Principle-V:** `grain_pk_drift` → `blocked` + a handoff row + **no** proposal.
- **Parser:** parses `retail_store_sales/source-profile.md` into the expected
  `ProfileResult`; reports `demo_sample_orders` (non-conformant) as uncomparable.
- **CLI:** `main(["drift", ...])` deferred path → pending message + expected exit;
  mirrors `test_cli_status.py` / the `validate` CLI tests. No live DB.

## 8. Success criteria

- All new unit tests pass; full existing unit suite stays green.
- `retail check` stays exit 0 (this adds a command + pure modules, no rule change).
- `ruff format --check` and `ruff check` clean.
- No numeric drift score anywhere; every Principle-V class fails closed to a
  named-owner handoff; no fabricated diff on the deferred-live path.

## 9. Non-goals / deferred (recorded, not built)

- A machine-readable profile artifact (would make the parser a loader) — deferred;
  the current decision (parse the committed `.md`) is reversible.
- Tolerance policy for missingness/cardinality "shift" — until set, any movement is
  an observation at `warning` (spec 015 assumption, unchanged).
- Wiring a drift outcome into `readiness-status.yaml` end-to-end — spec 015 US3 (P2);
  the emit shape supports it, the auto-write is a follow-up.
