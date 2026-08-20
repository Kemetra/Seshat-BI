# Data Model: Secure integration provisioning approval

**Feature**: `specs/154-secure-provisioning-approval/` | **Date**: 2026-08-20

Written from the shipped implementation (`src/seshat/integrations/approval.py`),
not from intentions.

## ProvisioningApproval (the committed record)

One row under `approvals:` in `contracts/provisioning-approvals.yaml`.

| Field | Required | Meaning |
|---|---|---|
| `stage` | yes | `provisioning`. A keying token, NOT a readiness stage. Rows keyed to anything else are ignored. |
| `owner` | yes | `"<Person Name> (governance)"`. A named human WITH an authority class. |
| `at` | yes | ISO `YYYY-MM-DD`. Audit metadata; **not** an expiry clock. |
| `components` | yes | The component ids this row authorizes. |
| `note` | no | Free text. Never echoed into a refusal (FR-015). |
| `revoked` | no | `true` withdraws this row's authority. |

Validity is a conjunction, and the two halves come from different places:

1. `approval_is_shape_valid(row)` -- the ONE canonical definition
   (`seshat.rules.readiness_status`), reused by import, never re-implemented.
2. the authority class is `governance` -- **this gate's own check**, because the
   canonical validator accepts any of the five classes (verified by probe; see
   `research.md` R3). Delegating alone would have left the requirement
   unenforced.

## ApprovedScope

The `components` set of a single row. Two rules:

- **One row must cover the whole request.** Two narrower rows never combine.
  Following `_authorizing_approval` in the Power BI write gate: combining them
  would grant an authority no human recorded.
- **Superset authorizes subset.** A request within a row's set is materially what
  the human approved; a request adding an id outside it is a material scope
  change and refuses.

"Materially identical" (FR-012a) is therefore: *the requested id set is a subset
of one live row's set.* Profile names are deliberately NOT the scope unit -- a
profile's catalog membership can change without the human re-approving, which
would silently widen authority.

## ApprovalVerdict

Frozen dataclass. `reason` is categorical so callers branch and tests assert
without matching prose; `next_action` is the human remedy.

| `reason` | Cause | Next action names |
|---|---|---|
| `authorized` | a live governance row covers the request | — (empty) |
| `absent` | no file, or no `provisioning` row | record an approval |
| `uncommitted` | file exists but is untracked or differs from HEAD | commit it |
| `unparseable` | YAML error, or top level is not a mapping | repair the YAML |
| `invalid_shape` | no row passes the canonical validator | the required row shape |
| `wrong_authority` | shape-valid but the class is not `governance` | the required class |
| `scope_mismatch` | authority established, request not covered | requested AND approved sets |
| `revoked` | the covering row carries `revoked: true` | record a new approval |

`authorized=True` occurs on exactly one path. No caller-supplied value reaches it:
`evaluate(repo_root, components)` takes no boolean, no default, and both arguments
are derived — the component set comes from the plan's rows, never from argv.

## Reading discipline

`is_tracked_and_clean` → `committed_text` → **guarded** `yaml.safe_load`.

The guard is deliberate: `dagster_adapter/gate.py` calls `safe_load` unguarded, so
a malformed record raises out of the reader instead of becoming a typed refusal.
Absent, unparseable, and unreadable all fail closed, and none is reported in a way
that could be mistaken for a pass.
