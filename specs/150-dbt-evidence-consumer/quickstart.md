# Quickstart: dbt evidence governance consumer

## What changes for an agent

Before: a governed dbt build wrote a schema-validated evidence record to
`mappings/<table>/dbt-evidence/`, and no governance surface read it. A build
could fail and the next-action document would route onward as though nothing had
happened.

After: the next-action document carries a caveat when the latest governed dbt
build failed, was blocked, or left an unreadable record.

```
seshat next --table <table>
```

For a table whose latest dbt build failed, the document's action carries a
caveat naming the outcome, the invocation, and the record path -- the same shape
the live-validation caveat already uses for Dagster.

## What does NOT change

Compare a table's readiness surfaces with and without a passing dbt record:

```
seshat next --table <table>
seshat evidence-pack --table <table>
```

Both are identical whether or not a passing dbt record exists. A stage recorded
`blocked` stays `blocked`, and an outstanding named-human approval stays
outstanding. The build is reported as evidence; it grants nothing.

The evidence pack is deliberately untouched by this spec: its documented
10-section contract, its section shapes, and its output are unchanged. A
reviewer-facing dbt section is a separate, later decision.

## Reading the states

| State | Meaning | Caveat |
| --- | --- | --- |
| `absent` | No record. The table has had no governed dbt build, or its evidence was reset. | none -- not having run dbt is not a defect |
| `built` | Latest record parsed; the build succeeded. | none |
| `failed` | Latest record parsed; the build failed. | yes |
| `blocked` | Latest record parsed; the build was blocked, unavailable, or reported an unrecognized outcome. | yes |
| `unreadable` | The selected record is corrupt or missing envelope fields. A defect, not a build failure and not a pass. | yes |

Execution-word translation, so an execution result is never mistaken for a
readiness verdict:

| Execution word | dbt's raw `outcome` |
| --- | --- |
| `built` | `pass` |
| `failed` | `failed` |
| `blocked` | `blocked`, `unavailable`, or anything unrecognized |

## Verifying the guarantee yourself

```
pytest tests/unit/test_evidence_pack.py -q        # unchanged; must stay green
orchestration/dagster/tests                        # the mapping move
```

The truth-separation test is the one that matters: it places a record with
`outcome: pass` next to a fixture whose stage is `blocked` and asserts the stage
is still `blocked`, the approval still outstanding, and the next-action document
unchanged.
