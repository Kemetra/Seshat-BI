# Adversarial plan review: spec 142

**Posture**: default-refuted. An independent reviewer that did not author the
artifacts was tasked to prove the plan flawed, and explicitly told not to
re-report the prior `analysis.md` findings but to find what that review missed.

**Performed**: 2026-08-07, read-only.

**Verdict**: **DO-NOT-RATIFY.** Eight findings, two CRITICAL. Every substantive
claim below was independently re-verified against the tree before being recorded
here -- none is accepted on the reviewer's word.

---

## Why the prior review was not enough

`analysis.md` fixed **C1**: FR-002's closed token set omitted
`seshat-orchestrator`, which its own T040 used. The fix added the token and
declared the set closed again.

That fix addressed **one instance and missed the class.** Nobody tested the
six-token set against the other ~90 entries. This review did, and the set fails.

That is the general lesson worth carrying: a closed set added under review
pressure needs a test against the whole population, not against the one entry
that exposed it.

## CRITICAL

### A1 -- SC-001's floor is unsatisfiable against the real manifest

The audit this spec derives from names **41** of the 102 manifest `id`s.
**61 entries are named by no audit section.**

Verified independently:

```
total entries: 102
ids literally named in audit: 41
NOT named: 61
unnamed by surface: {cli: 47, docs: 5, skill: 4, execution-adapter: 2,
                     product-module: 1, plugin: 1, human-artifact: 1}
```

Meanwhile SC-001 permits unclassified entries **only** for those blocked on
OD-1/OD-2 (roughly five) and forbids a boilerplate reason -- a floor added by the
prior review. Plan Phase 4 and tasks T040-T042 claim to cover the remainder
"per the audit's KEEP section", but the audit has no row for any of these 61.

**The implementer must either breach the floor or invent classifications.** The
plan's own Phase 4 is three one-line tasks standing in for 61 unaudited entries.

### A2 -- The six tokens demonstrably fit none, or two, for real entries

Attempted against FR-002 verbatim. All five entries confirmed to exist with the
stated surfaces:

| Entry | Surface / state | Problem |
| --- | --- | --- |
| `governed-statistical-core` | `product-module`, shipped | An executable numerical engine. Not domain *knowledge* (it runs code), not governance, wraps no upstream, sequences nothing. **Fits none.** |
| `f034-built-dashboard-page` | `human-artifact`, deferred | A human Power BI Desktop action. **Fits none** -- no token describes a human deliverable. |
| `kpi-derivation-lineage` | `docs`, spec-only | A ratified spec with no implementation. **Fits none**; five more `docs` entries share this shape. |
| `claude-code-plugin` | `plugin`, shipped | Anthropic owns the plugin format, Seshat authors the bundle. `official-upstream` or `seshat-governance`? **Fits two**, nothing breaks the tie. |
| `pbir-apply-theme` | `cli`, shipped | Writes an upstream-owned format but gates no upstream *capability*, so `seshat-adapter`'s wording fails; `seshat-governance` ("readiness gates, approvals, evidence, policy") is also false. **Fits two, badly.** |

## HIGH

### A3 -- The axis is write-only on landing

US1 and US2 are P1 outcomes promising an agent can route from the manifest. But:

- `tests/unit/test_capability_inventory.py:40` asserts
  `set(record) == oracle.DECLARED_RECORD_FIELDS` -- a **closed** set that does not
  contain `ownership`. `_project_record` drops it.
- FR-009 defers gating; the plan defers rendering.
- **`docs/capabilities/capabilities.yaml` ships in neither bundle** -- verified:
  `find integrations -name capabilities.yaml` returns nothing.

So after this spec lands, the only code reading `ownership` is the oracle
validating it against its own constants. No SC operationalizes the routing
outcome; SC-001..SC-007 are presence and inertness checks.

Sharpest instance: `pbi-mcp-doctor` **does** ship as a skill, and its ownership
fact (Microsoft, preview/pre-GA) is exactly what a bundle consumer needs -- but
the manifest carrying that fact is not in the bundle, so no shipped consumer can
ever read it.

### A4 -- Absence of `ownership` is overloaded three ways

FR-001 makes the mapping optional, so absence means (a) not yet classified,
(b) deliberately unclassified pending an owner ruling, or (c) -- to any plain
reader -- "no upstream owner, this is Seshat's."

Concrete failure: after Phase 2, `dbt-transformation-adapter` carries
`seshat-adapter`/dbt Labs while `pbi-mcp-doctor` carries nothing. The plain
reading of the second is "Seshat's own", which is **false** -- it wraps a
Microsoft preview MCP.

**A half-migrated manifest is affirmatively misleading in a way an unmigrated one
is not**, and the plan leaves that state live across roughly five commits. The
only disambiguation, `evidence/unclassified.md`, is a spec-directory file read by
no code and stale the moment entry 103 lands.

### A5 -- `generated_targets` is the second source of truth the Non-goals forbid

The Non-goals say this axis references facts other files own rather than
restating them, and FR-007 binds `upstream_reference` to `catalog.py`
accordingly. But T030 writes `generated_targets` naming bundle projection paths
already owned by `distribution/public-knowledge-allowlist.yaml` and validated by
`_record_destinations` (`export_agent_bundles.py:397`) -- while FR-005 states
outright that it "introduce[s] no new enforcement."

So the spec knowingly writes hand-maintained duplicates of exporter-owned paths
with no binding rule, for the one field where nothing prevents drift. If a
destination changes, those entries lie silently and every gate stays green.

## MEDIUM

### A6 -- T013 is a tautology

T013 requires asserting the FR-001 vocabulary contains no `NUMERIC_FIELD_HINTS`
substring -- a hardcoded list compared against a hardcoded list. It cannot fail
unless someone edits the test's own list, so it gives zero coverage against a
future author adding `ownership_confidence`.

The real protection is the **pre-existing** `_axis_numeric_field_names`
(`_capability_oracle.py:451-456`), which rejects such a field the moment it hits
the manifest. FR-008 and Risk R1 therefore describe a risk already covered, and
T013 restates rather than catches.

**Fix**: make T013 behavioral -- construct an entry carrying
`ownership_confidence` and assert `find_axis_violations` returns a problem.

### A7 -- FR-009's reasoning is applied asymmetrically

FR-009 defers the gate because "a rule needs a filled target before it is worth
building." The identical logic says **a field needs a reader before it is worth
filling** -- and per A3 none exists or is planned.

On the narrower question: the oracle *is* the manifest's only existing validator,
so "wrong home" is not defensible. The defect is the asymmetry, which argues for
**sequencing** -- land one reader alongside the axis -- not relocation.

### A8 -- FR-004's consumer survey missed two manifest-reading tests

FR-004 enumerates only `test_capability_ship_classification.py`. Also reading the
manifest, verified: `tests/contract/test_dbt_documentation.py` and
`tests/contract/test_statistical_documentation.py`. The first asserts named keys
on `dbt-transformation-adapter` -- **the exact entry T020 edits first**.

Both are named-key assertions, so FR-004's *conclusion* survives. But the survey
that "verified" FR-004 missed the test guarding the pilot entry, and the gate set
in `tasks.md` runs neither file -- so T024's "empirical proof of FR-004" would not
exercise them.

## Verdict and required changes

**DO-NOT-RATIFY.**

The single most important change: **SC-001's floor is unsatisfiable.** Either

- widen FR-002 with tokens covering `product-module`, `human-artifact`, and
  spec-only `docs` entries, and re-derive Phase 4 from the **manifest** rather
  than the audit, which does not cover 61 of 102 entries; **or**
- replace SC-001's floor with a counted, entry-by-entry exemption list derived
  from the real 102.

Either way, add an explicit `unclassified` sentinel token required on every entry,
so A4's three-way ambiguity becomes structurally impossible rather than
documented in an unread file.

Secondary, cheap, independent: drop `generated_targets` or bind it to the exporter
(A5); make T013 behavioral (A6); add one reader so the axis is not write-only on
landing (A3/A7); extend FR-004's survey and the gate set (A8).

## Status

This review grants no approval and does not ratify. The artifacts are **not
ready for a human ratification decision** as they stand -- not because the core
idea is wrong (an additive metadata axis validated by the existing oracle remains
sound), but because the classification vocabulary does not fit the population it
must classify, and the axis has no reader.

The corrections above are a design revision, not an editing pass. They are
deliberately **not** applied here: A1/A2 require choosing new tokens and
re-deriving a phase, and A3/A7 require deciding whether to land a consumer -- all
of which change what the spec commits to, and the spec is not ratified.
