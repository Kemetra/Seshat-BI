# Ratify ledger: spec 142 -- capability ownership fields

**Branch**: `spec/142-capability-ownership-fields`

**Prepared**: 2026-08-07

**Status**: **NOT RATIFIED. NOT RECOMMENDED FOR RATIFICATION AS IT STANDS.**

Ratification is a human edit this chain is structurally forbidden to make. This
ledger records what was produced and what a ratifier would be deciding -- it
grants nothing.

---

## Recommendation

**Do not ratify yet.** The adversarial review returned **DO-NOT-RATIFY** on two
CRITICAL findings that I independently confirmed against the tree. Ratifying now
would authorize an implementation whose Phase 4 cannot be executed as written.

This is not a formality. The package is internally consistent and factually
grounded after two review passes -- but its classification vocabulary does not
fit the population it must classify.

## What was produced

| Artifact | Purpose |
| --- | --- |
| `spec.md` | The ownership axis: 9 fields, 6 tokens, 10 FRs, 7 SCs, Non-goals, 3 open decisions |
| `plan.md` | Technical approach, constitution check, 5 phases, 4 risks, complexity tracking |
| `tasks.md` | 28 dependency-ordered TDD-gated tasks across 6 phases, all boxes unchecked |
| `analysis.md` | Read-only cross-artifact consistency check -- 12 findings, **all fixed** |
| `plan-review.md` | Adversarial default-refuted review -- 8 findings, **not fixed** (see below) |

Chain run: ground -> specify -> plan -> tasks -> analyze -> adversarial review ->
this ledger. Hand-driven, one step at a time, no workflow engine.

## The two blocking findings

Both independently verified, not taken on the reviewer's word.

### A1 -- SC-001's floor is unsatisfiable

The source audit names **41** of 102 manifest `id`s. **61 entries are named by no
audit section** (47 `cli`, 5 `docs`, 4 `skill`, 2 `execution-adapter`, and one
each of `product-module`, `plugin`, `human-artifact`).

SC-001 permits unclassified entries only for those blocked on OD-1/OD-2 -- about
five -- and forbids boilerplate reasons. Phase 4 covers those 61 entries in three
one-line tasks that cite "the audit's KEEP section", which has no row for any of
them. An implementer must breach the floor or invent classifications.

### A2 -- The six tokens fit none, or two, for real entries

Confirmed to exist with the stated surfaces: `governed-statistical-core`
(`product-module`) and `f034-built-dashboard-page` (`human-artifact`) and
`kpi-derivation-lineage` (spec-only `docs`) fit **no** token;
`claude-code-plugin` and `pbir-apply-theme` fit **two**, with nothing to break
the tie.

### Why these were recorded, not patched

Fixing them means choosing new tokens and re-deriving a phase from the manifest
rather than the audit. That changes what the spec commits to -- and an unratified
spec is not mine to redesign on my own judgment. The prior `analysis.md` pass
shows the failure mode: its C1 fix added the one missing token and declared the
set closed again without testing the population. Patching under review pressure
is how that happened.

## Also outstanding (cheap, independent of the above)

- **A3/A7** -- the axis is **write-only on landing**: `DECLARED_RECORD_FIELDS` is
  closed against `ownership`, gating and rendering are both deferred, and
  `capabilities.yaml` ships in neither bundle. Verified. Consider landing one
  reader alongside the axis.
- **A4** -- absence of `ownership` is overloaded three ways, so a half-migrated
  manifest is *affirmatively misleading* (`pbi-mcp-doctor` would read as
  Seshat-owned when it wraps a Microsoft preview MCP). An `unclassified` sentinel
  token would make this structurally impossible.
- **A5** -- `generated_targets` duplicates exporter-owned paths with no binding
  rule; the Non-goals forbid exactly this.
- **A6** -- T013 is a tautology; make it behavioral.
- **A8** -- FR-004's survey missed two manifest-reading contract tests, one
  guarding the pilot entry T020 edits.

## Human decisions this ledger cannot make

| Ref | Decision | Why it is yours |
| --- | --- | --- |
| **Ratification** | Whether spec 142 proceeds at all | Principle V human seam |
| **A1/A2** | New tokens, or a counted exemption list | Changes what the spec commits to |
| **A3** | Whether to land a consumer with the axis | Scope decision |
| **OD-1** | Is `speckit-*` vendored upstream? | A possible **Principle II** ("Depend, Never Fork") finding, not mere bookkeeping |
| **OD-2** | How to class the INSPECT dev-workflow skills | Judgment on what counts as a real Seshat delta |
| **OD-3** | Whether the five dead constants get their own spec | Separate-spec decision |

## Verification performed

```
seshat check                      exit 0 -- pre-existing RS1 warning only, no new finding
test_dbt_documentation.py         6 passed (includes the fence contract)
export_agent_bundles.py --check   PASS
seshat kit-lint                   no projection drift
tests/contract/                   201 passed, 1 skipped (at fence-move commit)
```

## What this chain did NOT do

- Did not ratify, and did not recommend ratification.
- Did not merge or push to `main`.
- Did not start any task in `tasks.md` -- every box is unchecked.
- Did not answer OD-1, OD-2, or OD-3.
- Did not patch the two CRITICAL findings.
- Did not grant implementation permission. The fence points at this spec (moved
  when 138 was closed out) but states explicitly that implementation is **NOT
  permitted** while the spec is Draft. **Being the fence target is not
  ratification.**

## Related

- Issue **#592** -- the source; section C is this spec, section D is downstream.
- Issue **#573** -- closed 2026-08-07; spec 138's T021/T060/T070 were
  *removed, not completed*.
- `docs/capabilities/ownership-audit.md` -- the audit (PR #593, merged).
