# Genericity ledger -- pre-flight baseline (task T003)

**Feature**: 137-finance-gl-genericity-proof | **Recorded**: 2026-07-30

The state the finance walk starts from, so a later reader can tell what this feature
changed from what was already true. This file records facts only; it grants nothing and
concludes nothing.

## Repository state at Slice A start

| Fact | Value |
|---|---|
| Branch | `137-finance-gl-genericity-proof` |
| Base commit | `38d4e77` (merge of PR #544, `main`) |
| Working tree at branch creation | clean (`git status --short` empty) |
| Registered worktrees | one (the primary checkout) |
| Spec ratification | Ahmed Shaaban (repo owner), 2026-07-30 |

## Gate state BEFORE any finance artifact existed

```text
python -m seshat.cli check    -> exit 0
[warning] RS1 last_checked_at 2026-06-25 predates latest approval 2026-07-23
          (mappings/retail_store_sales/readiness-status.yaml)

python -m seshat.cli kit-lint -> exit 0, no projection drift
```

The RS1 warning is **pre-existing** and belongs to the retail example. This branch touches
no file under `mappings/retail_store_sales/`, so that warning is neither caused nor cleared
by this feature. It must not be attributed to finance work in any later report.

## Fixture-size baseline (the evidence behind research R3)

| Committed data fixture | Bytes |
|---|---|
| `tests/fixtures/demo/demo_sample_orders.csv` | 1,801 |
| `distribution/synthetic-retail/source.csv` | 447 |
| `benchmark/scenarios/fixtures/synthetic-orders.csv` | 343 |

**Measured after generation** (2026-07-30): the clean finance actuals file is **425,135
bytes / 5,000 rows** -- about **236x** the largest committed fixture -- and the budget file
is 106,143 bytes / 2,688 rows. The plan's decision not to commit them is therefore
confirmed by measurement, not just estimated. Committed instead: the generator plus two
21-line excerpts.

## Clean-fixture digests (seed 20260730)

Recorded so a later regression is attributable. These are the first 16 hex characters of
each file's SHA-256 as generated on 2026-07-30:

| Source | Rows | sha256 (first 16) |
|---|---|---|
| `finance_gl_actuals` | 5,000 | `6a579d50d6c88648` |
| `finance_gl_budget` | 2,688 | `600e45cef9f1936b` |
| `accounts` | 30 | `a007e0e465dba5ec` |
| `departments` | 8 | `5e302ecfb5f8f70a` |
| `fiscal_calendar` | 8 | `aa36f491af4010c6` |

These digests are a convenience record, not the test. Byte identity is verified by
regenerating twice and comparing, in
`tests/unit/test_finance_gl_generator.py::test_regeneration_is_byte_identical`.

## Obstructions encountered during Slice A

**One**, and it is NOT a retail-genericity finding -- it is a tension inside this feature's
own ratified data model, recorded here for transparency and raised to the owner:

| Field | Value |
|---|---|
| `location` | `specs/137-finance-gl-genericity-proof/data-model.md` Section 1.1, validation rules 2 and 5 |
| `observed_problem` | Rule 2 requires every journal entry to balance (sum debits == sum credits); rule 5 restricts the fixture to P&L accounts. A P&L line cannot be balanced by another P&L line in real double-entry bookkeeping -- the offsetting side is normally a balance-sheet account, and balance-sheet grain is out of scope (spec 091). As written, the two rules cannot both hold. |
| `classification` | not a leak -- this is a spec-internal tension, not a retail assumption |
| `existing_rule_or_surface` | none; the kit did not cause it |
| `minimal_resolution` | Each entry pairs its P&L line with one line on a dedicated CLEARING account (`account_type='CLEARING'`, 2 of the 30 accounts). Both rules then hold, no balance is ever derived, and no snapshot fact appears. Excluding clearing accounts from P&L reporting becomes an explicit mapping-stage EXCLUSION DECISION rather than a hidden filter. |
| `core_change_required` | false |
| `evidence` | `tests/fixtures/finance_gl/generate.py` module docstring ("Fixture design note -- the offsetting side"); `tests/unit/test_finance_gl_generator.py::test_every_journal_entry_balances` passes with the pairing in place |

**Owner note**: this resolution was chosen by the agent because it satisfies both ratified
rules without inventing scope, and because it produces a genuine exclusion decision for the
mapping stage. If the owner prefers instead to relax data-model rule 2 (declaring the
fixture a P&L *extract* that need not balance), say so and the generator drops the clearing
pair. Either way the choice belongs in the record, which is why it is here rather than
buried in a code comment.

No retail-specific obstruction was encountered in Slice A -- expected, since Slice A only
generates data and touches no kit template, rule, or skill. The genericity ledger proper
(`docs/worked-examples/finance-gl-genericity-ledger.md`, task T011) opens with Slice C,
where the walk first meets the kit's own artifacts.
