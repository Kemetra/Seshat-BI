# Ratify ledger: spec 142 -- capability ownership fields

**Branch**: `spec/142-capability-ownership-fields`

**Prepared**: 2026-08-07 (revised same day after owner rulings)

**Status**: **RATIFIED by Ahmed Shaaban, 2026-08-07 -- implementation permitted,
NOT started.**

Ratification was the owner's decision, recorded on their explicit instruction.
The chain itself neither granted nor inferred it. All 31 tasks in `tasks.md`
remain unchecked: permission to implement is not implementation.

---

## Recommendation

**Ratified 2026-08-07.** All twenty findings from the two review
passes are resolved, and the six decisions the chain could not make were ruled by
the owner on 2026-08-07.

This reverses the earlier verdict in this file. The first version said
DO-NOT-RATIFY on two CRITICAL findings (A1, A2); both are now fixed at the design
level rather than patched, and the reasons are recorded below.

## Chain

ground -> specify -> plan -> tasks -> analyze -> adversarial plan-review ->
owner rulings -> revision -> this ledger. Hand-driven, no workflow engine.

| Artifact | State |
| --- | --- |
| `spec.md` | 8 fields, **10 tokens**, FR-001..011 + FR-002a, SC-001..007, Non-goals, 3 resolved decisions |
| `plan.md` | Constitution check, 5 phases (+Phase 0 in tasks), 4 risks, complexity tracking |
| `tasks.md` | 34 dependency-ordered TDD-gated tasks, **every box unchecked** |
| `analysis.md` | 12 findings -- all fixed |
| `plan-review.md` | 8 findings -- all now addressed (see below) |

## The owner rulings applied

| # | Decision | Ruling | Where it landed |
| --- | --- | --- | --- |
| 1 | The 61 unclassified entries (A1/A2) | Add tokens for uncovered surfaces **+ a required `unclassified` sentinel**; re-derive Phase 4 from the manifest | FR-002 (10 tokens), **FR-002a**, SC-001, T042 |
| 2 | Write-only axis (A3/A7) | **Land one reader** -- render the axis through the existing inventory surface | **FR-011**, T016 |
| 3 | OD-1 `speckit-*` | Investigate first, then rule | Resolved: `vendored-upstream`, **not** a Principle II violation |
| 4 | OD-2 dev-workflow skills | `seshat-governance` with documented deltas | Resolved, with a delta table |
| 5 | OD-3 dead constants | Record, do not fix | Resolved; T005 records, FR-010 forbids reviving |
| 6 | Push and open a PR | Yes | pending at the end of this chain |

## How the two CRITICALs were resolved

### A1 -- SC-001's floor was unsatisfiable

Independently verified: the source audit names **41** of 102 manifest `id`s, so
**61 entries** had no audit-derived classification (47 `cli`, 5 `docs`, 4 `skill`,
2 `execution-adapter`, one each `product-module` / `plugin` / `human-artifact`),
while SC-001 permitted about five unclassified.

**Fixed**: the impossible floor is **withdrawn and marked as withdrawn**. Phase 4
is re-derived from the manifest. SC-001's measure is now that every entry is
*declared* -- classified, or explicitly `unclassified` with an entry-specific
reason.

### A2 -- Six tokens fit none, or two

**Fixed**: FR-002 gains `seshat-product-module`, `human-deliverable`,
`specified-not-built` for the surfaces that fit nothing, plus the `unclassified`
sentinel. Ten tokens total.

### A4, as a bonus of the sentinel

FR-002a makes `capability_owner` **required**, so absence is never meaningful.
This was the sharpest finding: mid-migration, `pbi-mcp-doctor` carrying no
`ownership` would have read as Seshat-owned when it wraps a Microsoft preview MCP.
A half-landed migration is now honest instead of misleading -- structurally, not
by documentation.

### A5, A6, A8

- **A5**: `generated_targets` is **removed**. Destinations are owned by
  `distribution/public-knowledge-allowlist.yaml`; a hand-written copy was the
  "second source of truth" the Non-goals forbid, with nothing binding it.
- **A6**: T013 is now **behavioral** -- construct an entry carrying
  `ownership_confidence` and prove the detector fires, instead of comparing two
  hardcoded lists that could not fail.
- **A8**: all three manifest-reading contract tests are in the gate set,
  including `test_dbt_documentation.py`, which guards the entry T020 edits first.

## OD-1 in full -- it overturned my own framing

I had called `speckit-*` a possible **Principle II** ("Depend, Never Fork")
finding. On investigation that was wrong, and the correction matters:

- **Principle II is scoped to the Power BI execution adapter**
  (`constitution.md:271-275`), not to all tooling.
- The vendoring was **sanctioned by constitution amendment v1.1.0 in the same
  commit that performed it** (`constitution.md:556-563`, commit `1eb0c98`) -- a
  versioned, documented decision, not a silent fork.
- Hash-verified against `.specify/integrations/claude.manifest.json`; zero local
  drift; no Seshat vocabulary in any of the 14 bodies.
- **There are 14 such skills, not 12.** That error had propagated into the merged
  audit doc and this spec; both are corrected.

**Residual gap, real but narrower**: no re-vendor or upgrade path is recorded
anywhere -- no lockfile, no `specify upgrade` record, no re-run instructions. That
is the fork tax the Principle II *rationale* warns about, unpaid today only
because the copy is provably unmodified. T042a records it; fixing it is its own
decision.

## Verification

```
seshat check                      exit 0 -- pre-existing RS1 only, no new finding
export_agent_bundles.py --check   PASS
seshat kit-lint                   no projection drift
test_dbt_documentation.py         6 passed (includes the fence contract)
tests/contract/                   201 passed, 1 skipped
```

## Ratification -- granted

**Ratified by Ahmed Shaaban on 2026-08-07.** `spec.md`'s `**Status**` line and the
`<!-- SPECKIT -->` fence in both `CLAUDE.md` and `AGENTS.md` record it; the fence
now reads "implementation permitted".

**Implementation has not started.** All 31 task boxes are unchecked. The next
action is a separate, explicit instruction to begin -- ratification authorizes the
work, it does not perform it.

Two unrelated items still need a human:

- **RS1** -- `mappings/retail_store_sales/readiness-status.yaml` audit metadata
  predates the 2026-07-23 approval. Non-blocking by design; a **named human** must
  recompute it. Not something a ruling can delegate to an agent.
- **The spec-kit re-vendor path** -- surfaced by OD-1, out of scope here.

## What this chain did NOT do

- Did not merge or push to `main`.
- Did not start any task -- all 31 boxes unchecked.
- Did not self-ratify. Ratification was recorded only on the owner's explicit
  instruction, naming them; the chain cannot infer or grant it.
- Did not revive the five dead constants (OD-3).
- Did not ship `capabilities.yaml` inside the bundles (would force a drift-gate
  re-baseline).

## Related

- Issue **#592** -- the source; section C is this spec, section D is downstream.
- Issue **#573** -- closed 2026-08-07; spec 138's T021/T060/T070 were
  *removed, not completed*.
- `docs/capabilities/ownership-audit.md` -- the audit (PR #593, merged; corrected
  on this branch for the 12-vs-14 count and the resolved OD-1).
