# Adopted Ideas Completion Design

**Date:** 2026-08-25  
**Status:** Approved in owner conversation; implementation remains gated by the
repository's singleton active-spec lifecycle.  
**Scope:** Complete idea-bank candidates c19 and c35 as two sequential,
independently reviewable specs.

## Objective

Close the two remaining ADOPT candidates without inventing a second DAX formula
language, weakening metric governance, or presenting evidence age as a confidence
judgment.

Delivery is sequential:

1. Spec 156 completes c19, closes its active fence, and records it as shipped.
2. Spec 157 then completes c35, closes its active fence, and records it as shipped.
3. Spec 141 remains paused and otherwise byte-unchanged during both increments.

Only one spec may occupy `.specify/feature.json` and the `SPECKIT` fences at a
time. Moving the fence does not itself ratify either implementation spec; each
spec must carry its own named-owner ratification before code or product-template
changes begin.

## Alternatives Considered

### Recommended: contract-aligned reuse

Use the existing `definition.kind: ratio` grammar for actual divided by target,
add the owner-approved `compares_to` contract binding, and validate that the DAX
definition agrees with both bindings. For freshness, introduce explicit source
coverage facts and a reader-facing three-date disclosure with arithmetic only.

This is the smallest design that is both executable and governed. The current
ratio emitter already supports numerator and denominator sources from different
gold tables, and the drift verifier already checks both inline operands.

### Rejected: add `definition.kind: variance`

A new kind would duplicate the existing ratio emitter and make the word
"variance" ambiguous between target attainment (`actual / target`) and relative
variance (`(actual - target) / target`). The shipped pattern defines Net Sales vs
Target % as target attainment, so a second formula vocabulary adds risk without
new capability.

### Rejected: documentation-only closure

Updating only the examples would leave `binds_to`, `compares_to`, and
`definition` free to disagree while both generation and semantic checks reported
success. Likewise, adding freshness prose without an authoritative coverage-end
field would preserve the inference problem that blocked c35.

## Spec 156: Governed Two-Table Ratio Generation (c19)

### Contract shape

`templates/metric-contract.yaml` gains one optional sibling of `binds_to`:

```yaml
compares_to:
  gold_table: "gold.<comparison_fact>"
  columns:
    - "<comparison_column>"
  pii_sensitive: false
```

The block uses the same field shape and governance meaning as `binds_to`.
`binds_to` remains scalar and remains the primary semantic-model table on which
the measure is defined. `compares_to` identifies the second gold table read by a
cross-table metric; it does not create another semantic measure binding.

The field is optional. Existing one-table contracts, including all current base
and ratio contracts, remain valid and behaviorally unchanged.

### Definition shape

The variance-vs-target example uses the existing grammar:

```yaml
definition:
  kind: ratio
  numerator:
    aggregation: sum
    source:
      table: "gold.<actuals_fact>"
      column: "<actuals_amount>"
    filter: []
  denominator:
    aggregation: sum
    source:
      table: "gold.<target_fact>"
      column: "<target_amount>"
    filter: []
```

The generated expression is `DIVIDE(SUM(actuals), SUM(target))`. This represents
target attainment exactly as the shipped feature-095 pattern states. It neither
executes the expression nor authors a target value, target grain, missing-target
ruling, RAG threshold, or approval.

### Shared binding-coherence validation

A new stdlib-only module, `src/seshat/metric_contract_bindings.py`, owns one pure
interface:

```python
def definition_binding_errors(contract: Mapping[str, object]) -> tuple[str, ...]:
    """Return deterministic refusal reasons for contract/definition disagreement."""
```

The validator applies the following rules:

- A definition whose numerator and denominator read different `gold.*` tables
  requires `compares_to`.
- For a two-table ratio, `definition.numerator.source.table` must equal
  `binds_to.gold_table` and `definition.denominator.source.table` must equal
  `compares_to.gold_table`.
- Each side's source column and filter columns must be listed in that side's
  binding `columns`. `count_rows` has no source column but still requires any
  filter columns to be listed.
- Both binding tables must be non-empty `gold.*` strings. Both column collections
  must be non-empty lists of non-empty strings for a two-table ratio.
- `pii_sensitive`, when present, must be boolean.
- A malformed binding or definition returns a refusal reason; it never raises an
  uncaught type error.
- A one-table contract with no `compares_to` follows the existing validation path
  unchanged. This increment does not retroactively tighten unrelated contracts.

The `seshat generate` handler calls the validator on the complete contract before
passing its `definition` to `generate_measure`. Any error produces exit 1, empty
stdout, and a concrete `[refused]` message.

`metric_contract_inventory.load_contract_inventory` calls the same validator
before admitting an approved two-table contract. Consequently `seshat
semantic-check` reports the same disagreement as a binding error rather than
pairing the contract with TMDL and reporting a false pass.

`dax_gen.generate_measure` and `metric_drift.check_measure_drift` retain their
definition-only interfaces. Their responsibility remains formula emission and
formula verification; top-level contract coherence belongs to the new shared
validator.

### Failure behavior

Generation and semantic validation fail closed for missing `compares_to`, table
mismatch, column mismatch, non-gold tables, malformed lists, and malformed
booleans. They do not repair the contract, select a different table, infer a
column, or emit partial DAX.

The generator remains text-only. It does not write into `powerbi/`, connect to a
database, execute DAX, or invoke the Power BI adapter.

### Verification

Test-first coverage must demonstrate:

- a two-table actual/target contract generates `DIVIDE(SUM(...), SUM(...))` and
  round-trips through `check_measure_drift` as `pass`;
- the CLI refuses every named disagreement with empty stdout;
- approved-contract inventory refuses the same disagreements;
- `count_rows` plus filters validates the correct columns;
- existing one-table base and ratio fixtures remain byte-for-byte equivalent in
  output;
- imports preserve the stdlib-only core boundary; and
- the generic template contains no worked-example table, column, target, or RAG
  value.

## Spec 157: Answer Evidence Dates (c35)

### Authoritative source coverage

`templates/source-profile.md` gains an explicit reporting-date coverage block:

```markdown
| Primary reporting-date column | `<column | GAP -- source is non-temporal or not established>` |
| Observed coverage start | `<YYYY-MM-DD | GAP -- not established>` |
| Observed coverage end | `<YYYY-MM-DD | GAP -- not established>` |
| Coverage evidence | `<profile query/result citation | GAP -- not established>` |
```

These are observed profile facts, not freshness judgments. A date may be filled
only from committed profile evidence. A non-temporal source or absent measurement
uses the exact `GAP` posture; the author never substitutes the profile run date for
the data coverage end.

Existing filled source profiles receive this block only from facts already stated
in those same files. If a file lacks a defensible primary date or range, its new
field says `GAP`; this increment performs no live query and fabricates no value.

### Reader-facing disclosure

`templates/handoff/answerability-summary.md` gains an `## Evidence dates` section
near the top with exactly three facts:

1. **Data coverage ends** -- copied from the source profile's observed coverage
   end, with the source-profile path cited.
2. **Readiness last checked** -- copied from `readiness-status.yaml`
   `last_checked_at`, with the readiness-status path cited.
3. **Publish approval recorded** -- copied from the latest shape-valid
   `approvals[]` entry whose stage is `publish_ready`, with the readiness-status
   path cited.

The section then states elapsed calendar days in plain language:

```text
The readiness check is <N> calendar days after the observed data coverage end;
the publish approval is <M> calendar days after that readiness check.
```

This is arithmetic, not evaluation. The section must not use `fresh`, `stale`,
`current`, `outdated`, `acceptable`, `unacceptable`, traffic-light language, a
threshold, a badge, a verdict, or a numeric confidence/health score.

If any source fact is absent, malformed, or not explicitly evidenced, the
corresponding line uses `GAP -- <concrete missing fact>`. Arithmetic involving a
GAP is omitted and replaced by one sentence naming exactly which date difference
cannot be calculated. The author must not parse a date out of arbitrary evidence
prose when the named field is absent.

The answerability summary remains an optional executive companion. These fields
do not create a readiness gate and cannot change any readiness status or approval.

### Documentation and verification

`docs/readiness/publish-ready.md` explains the optional disclosure and its three
authoritative sources. It explicitly distinguishes data coverage, readiness audit,
and owner approval.

Documentation-contract tests must verify:

- all four source-profile coverage rows exist with ISO-or-GAP instructions;
- all three answerability dates cite the correct source fields;
- the elapsed-day sentence is present and conditional on complete dates;
- GAP behavior is explicit;
- prohibited freshness judgments and confidence language are absent from the
  disclosure; and
- generic templates contain no C086/retail-specific dates or schema names.

The tests do not claim that every historical source has temporal coverage. A GAP
is a valid, honest result.

## Delivery and Fence Lifecycle

The implementation sequence is strict:

1. Write, review, and ratify spec 156.
2. Move the singleton fence from paused spec 141 to spec 156.
3. Implement spec 156 with red-green-refactor cycles and complete its acceptance
   record.
4. Record c19 as shipped and close spec 156's fence.
5. Write, review, and ratify spec 157.
6. Move the singleton fence to spec 157.
7. Implement spec 157 with red-green-refactor cycles and complete its acceptance
   record.
8. Record c35 as shipped and close spec 157's fence.
9. Leave spec 141 paused unless the owner separately directs its resumption.

At no point are two feature directories active. A passing static check is
necessary but does not convert either disclosure or generated DAX into live
semantic correctness. No live database or Power BI execution is part of either
increment.

