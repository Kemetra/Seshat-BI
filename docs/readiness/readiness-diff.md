# Readiness diff

Read-only comparison of committed readiness state between two git revisions.

`seshat status` answers "where is this table **now**". `seshat impact-map` answers
"what does **this approved decision** touch". Neither answers the question a
reviewer actually has on a pull request:

> **Did readiness move, and did anything go backwards?**

`seshat readiness-diff` answers exactly that, and nothing more.

## Usage

```bash
seshat readiness-diff main..HEAD
seshat readiness-diff --base main --head HEAD
seshat readiness-diff main..HEAD --format json
```

Give **either** the `BASE..HEAD` range **or** the `--base`/`--head` pair -- never
both. Passing both is refused rather than silently preferring one.

## What it reports

| Reported | Meaning |
|----------|---------|
| `tables_added` / `tables_removed` | a `mappings/<table>/readiness-status.yaml` appeared or disappeared |
| `current_stage_changes` | a table's `current_stage` moved, and whether that move was backwards |
| `stage_changes` | a per-stage `status` changed, and whether that change was backwards |
| `blockers_added` / `blockers_removed` | `blocking_reasons[]` entries gained or cleared, per table and stage |
| `approvals_added` / `approvals_removed` | a recorded named-human approval appeared or disappeared |
| `has_regression` | a single **boolean** -- true when any of the above went backwards |

## What counts as a regression

Regression is **asymmetric on purpose**:

- `pass -> blocked` is a regression. `blocked -> pass` is ordinary forward progress.
- `current_stage` moving earlier in the seven-stage spine is a regression; moving
  later is progress.
- **A removed approval is a regression.** An approval disappearing means the
  evidence a stage rested on is gone. Reporting that as a neutral edit would let a
  reviewer merge away a named-human signature without noticing.

An **unrecognized** status (a malformed committed file) is reported as a *change*
but never as a regression -- guessing a rank for an unknown value would fabricate
a verdict out of a broken file.

`has_regression` is a boolean, never a count or a score. There is no severity
axis: the reviewer's question is "is something wrong here", and a number would
invite ranking that committed state cannot support (hard rule #9, Principle V).

## Boundaries

- **Read-only.** It writes nothing, opens no database, and makes no network call.
- **Not a gate.** Exit code is `0` for any successfully rendered comparison,
  *including one reporting a regression*. It registers no `seshat check` rule and
  adds no `blocking_reasons[]` entry. A boundary failure (unknown revision, unsafe
  range, unreadable repo) exits `1`.
- **Grants no approval** and never sets a readiness stage. It is evidence for a
  human review.
- **Reads the revisions, not the worktree.** Content comes from
  `git show <rev>:<path>`, so the answer follows what a reviewer would fetch -- a
  local uncommitted scribble can neither manufacture nor revoke a reported change.
- **Core is GitHub-free.** PR comments, checks, Markdown summaries, and SARIF are
  deliberately out of scope; this command is the primitive they would build on.
- **Best-effort per table.** One malformed committed document contributes nothing
  rather than aborting the run, so a single bad file cannot blind a reviewer to
  every other table's changes.

## See also

- `readiness-model.md` -- the four statuses and the no-fake-confidence rule.
- `readiness-pipeline.md` -- the seven-stage sequence the stage lattice follows.
- `../../src/seshat/readiness_diff.py` -- the comparison math (git-free, pure).
