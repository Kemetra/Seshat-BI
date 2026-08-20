# Quickstart: authorizing integration provisioning

**Feature**: spec 154 / issue #671

## What changed

`seshat integrations setup --apply` used to install software on the strength of
`--yes`. It now requires a committed, named-human approval. `--apply` still means
"I want to install"; it no longer means "I am allowed to".

## 1. An unapproved run refuses (and says why)

```
$ seshat integrations setup --refresh --apply --yes
error: provisioning needs a committed named-human approval -- record a
provisioning approval in contracts/provisioning-approvals.yaml
```

Exit code 2. Nothing installed, nothing written, no index contacted. The same
refusal appears whether the caller passes `--yes`, answers an interactive prompt,
or pipes an answer on stdin: none of those is authority.

## 2. A human records the approval

Edit `contracts/provisioning-approvals.yaml`:

```yaml
approvals:
  - stage: provisioning
    owner: "Ada Lovelace (governance)"
    at: "2026-08-20"
    components: [duckdb, polars, pyarrow]
    note: "silver-layer transformation stack for the retail mart"
```

Then **commit it**. The gate reads HEAD:

```
$ git add contracts/provisioning-approvals.yaml
$ git commit -m "chore: approve provisioning for the transformation stack"
```

An uncommitted edit authorizes nothing — that is the point. It stops the party
requesting the install from also supplying the permission.

## 3. The approved run proceeds

```
$ seshat integrations setup --refresh --apply --yes
...
Integration runtimes and configuration are present.
```

`--yes` still suppresses the prompt. It contributes no authority.

## What the approval does and does not do

**Does**: authorize installing the named components. Standing — retry after a
partial failure, or re-run the same scope, with no new approval. Age never
expires it.

**Does not**:
- authorize a component it does not name (`scope_mismatch`, and the refusal
  prints both the requested and approved sets);
- combine with another row — one row must cover the whole request;
- make anything "ready". A component is ready only when the existing verification
  and discovery surfaces say so. Authorization is not verification.

## Withdrawing an approval

Add `revoked: true` to the row and commit, or remove the row. Revocation is
reported distinctly from absence, so the remedy differs: re-approve versus record
a first approval.

## Who may approve

The `governance` authority class only — the named human project-governance
authority for external environment and tool changes. An `analyst` or
`data_owner` row is shape-valid but refused with `wrong_authority`. No agent may
write this file: recording an approval is a named-human action (Constitution
Principle V), and the gate only ever reads.
