# Phase 0 Research: Secure integration provisioning approval

**Feature**: `specs/154-secure-provisioning-approval/` | **Date**: 2026-08-20

Every finding below was verified against the repository or by running code, not
reasoned from naming.

## R1 -- Approval artifact path: `contracts/provisioning-approvals.yaml`

**Settled.** Evidence:

- `.seshat/integrations/` is **gitignored** (`.gitignore:127`), as are
  `.seshat/watch/`, `.seshat/dagster/`, `/.seshat/dbt/`. An approval recorded
  there could never satisfy `is_tracked_and_clean`, so the gate would refuse
  forever. DISQUALIFIED -- that tree is machine-local installer state by design.
- `git check-ignore contracts/provisioning-approvals.yaml` -> not ignored.
- `contracts/` is tracked on `origin/main` and already holds governed contract
  state: `contracts/knowledge/approval-authority.yaml`,
  `contracts/pbi-mcp-write-targets.yaml`.

**Near-exact prior art found.** `contracts/pbi-mcp-write-targets.yaml`'s own
header documents the identical argument for #671:

> "The read-only preflight family accepts `--allow` on argv, which is fine when
> the allowlist only gates *validation*. As a *write* precondition it authorizes
> nothing: the party requesting the mutation would be supplying the list that
> permits it. So the write gate reads THIS path, fixed in code as
> `gate.TARGET_ALLOWLIST_RELPATH`, and reads it from HEAD via
> `gitstate.committed_text` -- an uncommitted widening is invisible to the gate."

This feature follows that established pattern rather than inventing one: a
relpath constant fixed in code, read from HEAD, with no flag able to redirect it.

## R2 -- Scope identity

**Decision**: an approval row names its scope as **explicit component ids**, and
the gate authorizes a request only when every requested component id is named by
a single approval row.

Rationale, from the prior art at `gate.py:350` (`_authorizing_approval`):

> "Both token checks on the SAME row. They must not be satisfiable by different
> rows: two narrow approvals would otherwise combine into one wider authority no
> human granted."

Applied here: an approval covering `{A, B}` and another covering `{C}` MUST NOT
combine to authorize `{A, B, C}`. One row must cover the whole request.

**"Materially identical" (FR-012a/FR-012c)** = the requested component-id set is
a subset of one approval row's named set. A superset approval authorizes a subset
request (spec edge case). Adding a component id not in that row is a material
change and refuses (FR-012c). Profile names are NOT the scope unit: a profile's
membership can change in the catalog without the human re-approving, which would
silently widen authority.

## R3 -- Reusing `approval_is_shape_valid` (no fork)

**It is directly importable** and already reused by the Power BI MCP write gate:

```python
from seshat.rules.readiness_status import approval_is_shape_valid   # gate.py:33
```

It takes a plain dict and requires `stage`, `owner` (named decider + authority
class), and a parseable ISO `at`. The `stage` field is **just a keying string**,
not readiness-coupled -- a provisioning record supplies `stage: provisioning`.
No fork, no second validator, no promotion of private helpers needed. FR-003 is
satisfied by import.

### CRITICAL finding -- the validator does NOT check WHICH authority class

Probed directly:

| Row | `approval_is_shape_valid` |
|---|---|
| `stage: provisioning`, `owner: Ahmed Shaaban (governance)`, `at:` | **True** |
| same but `owner: Ahmed Shaaban (analyst)` | **True** |
| `owner: governance` (bare role as name) | False |
| `owner: Ahmed Shaaban` (no class) | False |
| no `at:` | False |
| `date:` instead of `at:` | False |
| no `stage` | False |

So **FR-004a (`governance` only) is NOT covered by shape validation** -- any of
the five classes passes. The gate MUST check the class itself, in addition to
calling the validator. Had this been assumed rather than probed, T014 would have
been a vacuous test that passed while the requirement was unenforced.

## R4 -- `gitstate` helpers

`from seshat.gitstate import committed_text, is_tracked_and_clean, run_git`
(`gate.py:32`) -- already imported by a sibling adapter package, so no cycle
importing them from `seshat.integrations`. Semantics confirmed by
`gate.py:283` (`_load_committed_yaml`): `is_tracked_and_clean` first, then
`committed_text`, then a **guarded** `yaml.safe_load` -- absent, unparseable, and
unreadable all fail closed and none is distinguishable as a pass. That guarded
wrapping is deliberate: `dagster_adapter/gate.py` calls `safe_load` unguarded, so
a malformed record raises out of the reader instead of becoming a typed refusal.
This feature copies the guarded form.

## R5 -- Revocation representation

**Decision**: revocation is **absence or replacement**, plus an explicit
`revoked: true` marker on a row.

- A removed row -> `absent` (no authority).
- A row with `revoked: true` -> `revoked`, reported distinctly from `absent` so a
  human can tell "withdrawn" from "never recorded" (FR-014's next action differs:
  re-approve vs. record a first approval).
- A replaced row is just the new row's scope governing; the old row does not
  re-widen authority.

Append-only remains the norm: `_shape_valid_approvals` returns EVERY matching row
precisely so an audit trail grows rather than being rewritten. Revocation
therefore adds a marker; it never rewrites history.

## R6 -- Extending the approval-authoring surfaces

approval-console (F027) and approval-evidence-pack (F035) both write per-table
`mappings/<table>/readiness-status.yaml` `approvals[]`. Both are
**skill/template surfaces with no runtime code** (F027 status: "Authored (skill +
two templates + one docs page; no runtime code)").

**Consequence**: there is no Python write path to extend or duplicate, so FR-017
is satisfied by documenting the project-scoped target in those skills rather than
by code. The gate this feature builds is **read-only** and writes no approval,
so it cannot itself become a second write path.

## Net design

- Constant `PROVISIONING_APPROVALS_RELPATH = "contracts/provisioning-approvals.yaml"`
  fixed in code; no flag may redirect it.
- Gate reads HEAD only: `is_tracked_and_clean` -> `committed_text` -> guarded
  `yaml.safe_load`.
- Row shape: `stage: provisioning`, `owner: "Name (governance)"`, `at: ISO`,
  `components: [ids]`, optional `revoked: true`.
- Validity = `approval_is_shape_valid(row)` AND class is `governance` AND the
  requested component set is a subset of one row's `components`.
- Verdicts: `authorized`, `absent`, `invalid_shape`, `wrong_authority`,
  `scope_mismatch`, `uncommitted`, `unparseable`, `revoked`.
