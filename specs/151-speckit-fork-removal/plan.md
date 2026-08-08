# Implementation Plan: Remove the Spec Kit template fork and externalize Seshat status governance

**Branch**: `151-speckit-fork-removal`

**Status**: draft; NOT ratified. Implementation is not authorized.

## Phase classification

**REQUIRED.** The fork exists on `main` at `766c0ee` and is not yet externalized.

| Question | Answer | Evidence |
| --- | --- | --- |
| Does the template still differ from upstream? | Yes | `git diff 1eb0c98 HEAD -- .specify/templates/spec-template.md` = +11/-1; upstream seeds `**Status**: Draft`, the tree carries `draft` plus an 11-line vocabulary block |
| What behavior does the difference provide? | Documentation of ADR-0019's closed vocabulary, plus the seeded lowercase value | the diff itself |
| What depends on it? | One test, which reads the file and runs in CI | `tests/unit/test_spec_status_vocabulary.py:24,66-72` |
| Is the vocabulary in shipped code? | No | zero hits for `ratified`/`superseded` under `src/seshat/` |

Not ALREADY-SATISFIED: nothing in `src/seshat/` owns the policy.
Not BLOCKED: no upstream permission is needed to stop modifying our own checkout.

## The smallest thing that works

1. **A policy module in `src/seshat/`** owning the vocabulary, canonical case,
   line grammar, and per-value evidence requirements. One module, importable,
   no state machine.
2. **Migrate the one real consumer.** `test_spec_status_vocabulary.py` stops
   declaring `VOCABULARY` itself and stops reading the template for policy; it
   imports the authority and validates `specs/*/spec.md` against it.
3. **Reconcile the H3 grammar** so the canonical ratified form is accepted by
   `implement.js`, with a contract test that fails if the two diverge.
4. **Restore the template** to its upstream baseline, and reconcile the
   spec-kit manifest entry with LF normalization.
5. **Correct the stale audit line**, minimally.

## Where the authority goes

`src/seshat/` — a single new module. `src/seshat/rules/status_claims.py` (SC1)
is the closest existing neighbour and shows the shape, but the authority is NOT
folded into SC1: SC1's own vocabulary is `{built, planned}` for a different
field, and merging the two would create one module answering two unrelated
questions.

Whether the authority additionally becomes a registered `seshat check` rule is
an implementation decision deferred to the ratified plan, with a bias AGAINST:
ADR-0019 §3 states "No new `seshat check` rule is added," and adding one would
expand the shipped rule surface beyond what this migration needs. The authority
is a library other checkers use; the enforcing consumer stays the CI-run test.

## Why not the alternatives

- **Keep the fork, add machinery to reapply it** — rejected by the owner. It
  institutionalizes the fork tax rather than paying it off.
- **Copy the template into `templates/` and point Spec Kit at the copy** —
  forbidden by FR-016. It is the same fork with a new address, and it silently
  inherits every future upstream template improvement as a merge conflict.
- **Fold the policy into SC1** — SC1 answers a different question with a
  different vocabulary. Overloading it creates one module with two authorities.
- **Add a new `seshat check` rule** — contradicts ADR-0019 §3 and widens the
  shipped surface for a policy whose only enforcing consumer is a test.

## The reconciliation problem, stated precisely

`implement.js` H3 currently requires:

```
**Status**: Ratified (Name, YYYY-MM-DD)      <- capital R, parenthesized
```

ADR-0019 and the forked template require:

```
**Status**: ratified -- Name, YYYY-MM-DD     <- lowercase, dash-separated
```

Verified empirically against the merged `specs/150-dbt-evidence-consumer/spec.md`:
H3_RATIFIED does not match, H3_DRAFT does not match, so the workflow refuses.

**Decided (agent recommendation, 2026-08-08): option A, widen additively.**
H3 accepts the ADR lowercase form IN ADDITION to the legacy parenthesized form.

Rejected -- option B, make the ADR form the only form and migrate existing
status lines: it touches ~40 committed `Ratified` specs, risks refusing a spec
mid-flight, and pulls corpus migration into a feature that FR-023 deliberately
keeps out.

Option A is additive, so it cannot invalidate an already-ratified spec, and
FR-011's divergence contract test is what stops the two forms drifting apart
afterwards. It may not loosen H3 into accepting an unnamed or undated
ratification (FR-012), and must not match a `**Status history**:` line
(FR-012a).

## Migration order (mandatory)

The forbidden order is: restore the template, discover governance broke, repair
afterwards. The required order:

| Step | Action | Gate before proceeding |
| --- | --- | --- |
| 1 | Enumerate every real consumer of the template's behavior | the list matches the measured dependency table in `spec.md`, re-verified at implementation time |
| 2 | Build the authority in `src/seshat/` | its own unit tests pass; it derives nothing from the template (FR-004) |
| 3 | Prove equivalent-or-stronger governance | the authority rejects every value the old test rejected, plus the cases the old test never covered (absent line, unparseable line) |
| 4 | Migrate consumers to the authority | `test_spec_status_vocabulary.py` imports it and no longer declares `VOCABULARY`; still green |
| 5 | Reconcile H3 and add the divergence contract test | the canonical ratified form is accepted; spec 150's line is accepted |
| 6 | Restore the upstream template | `git diff` against the `1eb0c98` baseline is empty |
| 7 | Prove nothing was lost | the full governance suite is green with the template clean; an invalid status is still rejected |
| 8 | Reconcile the manifest entry, LF-normalized | recomputed hash matches the recorded upstream hash |
| 9 | Correct the audit line; run repo gates | `seshat check`, `kit-lint`, `pytest -m unit`, bundle drift |

At no step may an invalid status or a missing approval become temporarily
acceptable. Step 6 is the first step that touches the template, and it comes
after the replacement is proven.

## Files expected to change (implementation, NOT this task)

| File | Reason |
| --- | --- |
| `src/seshat/<new module>.py` | the policy authority |
| `tests/unit/test_spec_status_vocabulary.py` | import the authority; stop declaring the vocabulary; stop reading the template for policy |
| `tests/unit/<new or existing>` | authority unit tests + the H3 divergence contract test |
| `.claude/workflows/implement.js` | H3 grammar reconciliation (Seshat-owned harness content) |
| `.specify/templates/spec-template.md` | **restored to upstream**; net effect is deletion of the Seshat block |
| `.specify/integrations/speckit.manifest.json` | reconcile the template entry (LF-normalized) |
| `docs/capabilities/ownership-audit.md` | minimal factual correction to the "provably unmodified" passage |
| `docs/decisions/0019-*.md` | a pointer noting the policy's executable home moved; the decision itself is unchanged |

Explicitly NOT changed: `src/seshat/fence.py`, the SPECKIT/SESHAT-KIT fences,
`src/seshat/rules/status_claims.py` (SC1), any Power BI / dbt / Dagster surface,
CI configuration, dependencies, git configuration, and the five `speckit-git-*`
skills.

## Fail-closed posture

| Case | Result |
| --- | --- |
| Spec has no `**Status**:` line | defect, named; never treated as valid |
| Status line unparseable | defect, named |
| Value outside the vocabulary | rejected |
| Correct value, wrong case | rejected, with the canonical form named |
| `implemented` without a tracked artifact | rejected (existing SC1 behavior) |
| `ratified` without a name or date | rejected |
| Spec file unreadable | reported as an error, not skipped |
| Template restored but authority missing | the suite fails; step order makes this unreachable |

## Validation (for the ratified implementation)

```
pytest tests/unit/test_spec_status_vocabulary.py -q
pytest tests/unit -q -m unit
python -m seshat.cli check
python scripts/export_agent_bundles.py --check
ruff format --check src tests
ruff check src tests
```

Plus, specific to this feature:

- restore the template in a scratch tree and assert an invalid status is still
  rejected (proves the authority, not the template, is doing the work);
- assert `specs/150-dbt-evidence-consumer/spec.md`'s status line is accepted by
  the reconciled H3 grammar;
- recompute the template hash with LF normalization and compare to the manifest.

## Stop point

This plan stops at ratification. No implementation task begins until a named
human records ratification in `spec.md`. The agent cannot self-ratify, and this
feature does not weaken the mechanism that enforces that.
