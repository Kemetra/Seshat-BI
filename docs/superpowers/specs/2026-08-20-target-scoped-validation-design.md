# Target-scoped post-write validation

**Date**: 2026-08-20
**Status**: Draft — awaiting owner review
**Closes**: #661 (gaps 1–2), #663 (gap 3)
**Feature**: spec 149 / F016 slice 5 — the approval-gated Power BI MCP write adapter

## The question

One design question underlies all three gaps:

> What corpus, and which validators, does a given write target imply — while still
> proving that the authorized target was actually examined?

#661 and #663 were filed separately but say the same thing in their own words:
"new surface, not a fix" and "a design change rather than a flag". Answering the
question once is the point of treating them as one slice.

## What is broken today

`pbi_mcp_adapter/validation.py` runs exactly one validator — `seshat
semantic-check --require-inputs` — over the **whole repository**. Three
consequences, each measured:

1. **A pre-existing error in an untouched model blocks a good write** (#663 gap 3).
   Reproduced: a repo with `Target.SemanticModel` (clean) and
   `Other.SemanticModel` (an unapproved measure) exits 1, and the adapter
   returns `blocking=True` with rollback guidance for `Target.SemanticModel` —
   a rollback that cannot fix an error in `Other.SemanticModel`.

2. **Binding validation never runs** (#661 gap 1). A measure rename or delete can
   orphan a visual's binding; nothing checks this after a write.

3. **Value validation never runs** (#661 gap 2). `value-check` ships as a real CLI
   verb but is never invoked, so a write that changes an approved result still
   reports `materialized`.

### Two constraints discovered by measurement, not assumption

**`semantic-check` cannot be scoped through its existing interface.** Its options
are `--repo`, `--metrics-dir`, `--include-untracked`, `--require-inputs` — no path
filter. Pointing `--repo` at the model subdirectory discovers *nothing*:
`_semantic_files` anchors on `git rev-parse --show-toplevel` and explicitly
raises "semantic repository is a subdirectory of another Git root". With
`--require-inputs` that correctly exits 1 — safe, but useless: it validates
nothing.

**Findings are parseable.** `runner._format` renders every finding as
`[severity] rule_id message (locator)`. The whole line is a stable identity key.
This is what makes a baseline diff possible without modifying a shipped CLI verb.

## Decisions

| # | Decision | Rationale | Who decided |
|---|----------|-----------|-------------|
| D1 | **Baseline diff**, not a new scoping flag | Zero change to the shipped `semantic-check` verb, which CI and other callers depend on. Attributes findings to *this* write. | Owner |
| D2 | Missing data leg → **degraded, non-blocking** | Matches the shipped `retail validate` posture (`[PENDING LIVE PROFILE]`). "No data leg" must never read as "validated". | Owner |
| D3 | Unreadable `definition.pbir` → **recorded skip**, not a block | One consistent degraded shape rather than two. The stricter options let an unrelated malformed artifact block a write to a model it has nothing to do with — the same defect gap 3 exists to remove. | Delegated |

## Architecture

Selection and judgment are split, because validator *selection* is the new surface
and must be testable without spawning a subprocess.

```
plan_validators(repo_root, target_path) -> ValidationPlan      # pure, no I/O
    semantic : always
    bindings : tuple[Path, ...]              report dirs paired via definition.pbir
    value    : bool                          a contract pins a value for this target
    skipped  : tuple[tuple[str, str], ...]   (check, reason) — never silently empty

run_plan(plan, baseline) -> ValidationOutcome                  # existing type
```

### `ValidationOutcome` — extended, invariants intact

Gains one field:

```python
checks_skipped: tuple[tuple[str, str], ...] = ()   # (check_name, reason)
```

Both existing invalid-state guards are preserved unchanged:

- `passed` requires a non-empty `artifacts_examined` — a vacuous pass stays
  unrepresentable.
- `failed` requires non-empty `rollback_guidance` — a failure nobody can undo
  stays unrepresentable.

A skip is **recorded with a reason**, never inferred from absence. An empty
`checks_skipped` means "nothing was skipped", not "we did not look".

## Gap 3 — the baseline diff (D1)

```
baseline = semantic_findings(repo)      # BEFORE the mutation
...mutation...
current  = semantic_findings(repo)      # AFTER
regressions = current - baseline        # set difference on rendered finding lines
```

Only `regressions` block. Pre-existing findings are carried in the record as
`pre_existing` — reported, never silently dropped, never blocking.

### The fail-open this must close

If the baseline run cannot be obtained, the two possible defaults are not
symmetric:

- an **empty** baseline makes every finding look new — noisy, but safe;
- a baseline that silently captured everything makes every finding look
  pre-existing — which hides the exact regression this check exists to catch.

Therefore an unobtainable baseline is a **recorded blocker**
(`PBIMCP-VAL-04` — the next free id; 01–03 are in use), not an empty set. Fails closed.

### Cost

Two `semantic-check` subprocess runs per apply instead of one. Each already
carries `VALIDATION_TIMEOUT_SECONDS = 300`; the baseline runs before any
mutation, so a baseline timeout costs nothing but a refusal.

## Gap 1 — binding validation, paired from the artifact (D3)

`pbir_validate_bindings.validate_bindings(report_dir=, model_dir=)` is directly
importable — no subprocess, no CLI parsing.

A report is **in scope** when its `definition.pbir` names the mutated model. That
link is read from the artifact, not guessed: `definition.pbir` carries a relative
model reference, which rule R1 (`check_pbir_relative_reference`) already
validates.

Unreadable or absent `definition.pbir` → that report is added to `skipped` with
the reason. It does not block (D3).

## Gap 2 — value-check, degraded (D2)

Runs only when **both** hold:

1. a metric contract pins an expected value for the touched model, and
2. a DSN resolves.

Otherwise → `skipped` with `[PENDING LIVE PROFILE]` and the reason, non-blocking.

DSN resolution reuses `value-check`'s own path rather than reimplementing it:
`applied_dotenv(repo)` for workspace `.env`, then `_ensure_driver` /
`_make_runner` (themselves shared with the `validate` leg). No second credential
path is introduced, and no DSN value reaches evidence, stdout, or a blocker
string.

Note the existing fail-closed contract this inherits: a contract with **no**
`expected_value` block is skipped, but a **malformed** block is an ERROR, never a
silent skip. The adapter must preserve that distinction — a malformed expectation
is a finding, not a degraded check.

## What does NOT change

- **`_target_was_examined` is untouched.** It reads the artifact directly and is
  independent of which validators ran, so scoping cannot weaken it. A scoped run
  that examined nothing still cannot report `passed`. This is the invariant the
  whole slice must preserve.
- **The five-value outcome vocabulary stays closed.** No new outcome token; a
  degraded check is a `checks_skipped` entry, not a new verdict.
- **Authority.** Nothing here grants an approval, moves a readiness stage, or
  writes `approvals[]`. Evidence remains derived-only.

## FR-013 correction

FR-013 currently requires "the `seshat check` R-family". That family
(`rules/pbir.py`) is report-layer only — R1 iterates `*.Report/definition.pbir`,
R2 `*.Report/definition/report.json`. This feature mutates the **semantic model**
(TMDL), which neither corpus contains, so the named validator would examine zero
bytes of the thing that changed and report clean.

FR-013 is corrected to name what actually validates a semantic-model write:
`semantic-check` (regression-diffed), binding validation where a report is in
scope, and value validation where a value is pinned and a data leg resolves.

New requirements recorded alongside it:

- **FR-013a** — post-write semantic validation blocks only on findings this write
  introduced; pre-existing findings are reported, not blocking.
- **FR-013b** — an unobtainable baseline is a blocker, never an empty baseline.
- **FR-013c** — every validator not run is recorded with a reason; absence is
  never a pass.

## Testing

TDD: every behaviour below gets a failing test first.

| Proof | Why it matters |
|-------|----------------|
| a pre-existing finding in an untouched model does **not** block | the #663 gap-3 defect |
| a finding introduced by the write **does** block, with rollback guidance | the check still works |
| an unobtainable baseline **blocks** | the fail-open above |
| a paired report is validated; an unpaired one is recorded as skipped | D3 |
| no DSN → loud skip, never a pass | D2 |
| `_target_was_examined` still fails closed on a destroyed target | the preserved invariant |
| no DSN or secret-shaped value reaches evidence or stdout | both redaction layers |

Each guard is proved load-bearing by weakening it and watching its test go red,
using a `try/finally` + durable-backup harness (a previous slice's harness
crashed mid-run and left a fix reverted under its own new docstring).

## Files

| File | Change |
|------|--------|
| `src/seshat/pbi_mcp_adapter/validation.py` | plan/verdict split; `checks_skipped`; baseline diff |
| `src/seshat/pbi_mcp_adapter/orchestrate.py` | capture the baseline before the mutation |
| `src/seshat/pbi_mcp_adapter/evidence.py` | carry `checks_skipped` into the record |
| `specs/149-pbi-mcp-write-adapter/spec.md` | FR-013 correction + FR-013a/b/c |
| `docs/integrations/pbi-mcp-adapter.md` | document the validator set and degraded reporting |
| tests | per the table above |

## Sequencing

This branch is **rebased onto `663-git-read-and-ignored-scope`** (PR #672, open and
green), not onto `main`. #672 rewrites `_snapshot` / `_list_files` in
`orchestrate.py` — the same function this slice extends — so building on top of it
avoids the conflict rather than resolving it twice.

Consequence: **#672 must merge before this one.** If #672 is ever abandoned, this
branch needs re-basing onto `main` and the baseline-capture hook re-sited against
the older `_snapshot`.
