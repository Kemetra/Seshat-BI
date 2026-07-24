# Governed Existing PBIP Adoption

Use this path when a Power BI analyst already has a local PBIP project and
needs a truthful starting point in Seshat BI.

```powershell
seshat adopt-pbip assess --project <PBIP-project-directory> --format text
```

`assess` is offline and read-only. It inventories supported PBIP, TMDL, and
PBIR structure; cites project-relative observations; redacts unsafe literals;
and composes existing governance and readiness surfaces into exactly one next
action. It does not open Power BI Desktop, call a Power BI adapter, query DAX,
connect to a database, create an approval, or mark any readiness stage `pass`.

Structural observations are not business meaning. Source mappings, grain,
metrics, rollups, PII disposition, approvals, and live validation remain owned
by their existing artifacts and named human decisions.

Use JSON when an agent needs the stable machine document:

```powershell
seshat adopt-pbip assess --project <PBIP-project-directory> --format json
```

The output includes an `assessment_digest` and a declared `scaffold_plan`.
Review both. A project outside Git can be assessed, but its next action remains
the explicit version-control prerequisite; the command never runs `git init`.

After a human has reviewed the current digest, and only when the project is a
clean existing Git worktree, create the single optional evidence seam:

```powershell
seshat adopt-pbip scaffold --project <PBIP-project-directory> `
  --accept-assessment <assessment-digest> --format text
```

Success creates only `.seshat/adoption/pbip-adoption.yaml`. It is a fingerprint
baseline containing observations, proposals, blockers, and `approvals: []`; it
is not a readiness file or a second stage engine. A stale digest, dirty input,
unsafe path, existing target, or publication failure writes nothing.

Run `assess` again after committing governance work. It compares current
authoritative inputs to that baseline and surfaces added, removed, or changed
inputs. Existing readiness and approval predicates remain authoritative.

## Measure sync into an adopted model

Once a model has its accepted adoption baseline, approved contract measures
can be upserted into one of its tables without hand-editing TMDL:

```powershell
seshat adopt-pbip measure-sync --repo <governed-repo-root> `
  --model <path-to-.SemanticModel-directory> --table "gold fct_sales" `
  [--metrics-dir mappings] [--dry-run] [--format text|json]
```

The command is file-only (no database, no Power BI Desktop) and fail-closed;
each gate refuses with a distinct, actionable message and a non-zero exit:

- **Adopted models only.** The project's `.seshat/adoption/pbip-adoption.yaml`
  must exist and record the `--model` directory. If it does not, run
  `adopt-pbip assess`, review the digest, then `adopt-pbip scaffold` first.
- **Approved contracts only.** Contracts are loaded through the same
  owner-approval inventory the semantic gate uses (readiness `pass`, evidence,
  a named `semantic_model_ready` approval with `metric_owner` authority naming
  the contract). Every excluded contract is reported with its reason; zero
  approved contracts bound to the table refuses the run.
- **Verified rendering.** Each measure re-generates through the same L3 drift
  check and D1-D11 form rules `seshat generate` uses. One unrenderable
  contract refuses the whole run -- the write is all-or-nothing.
- **Idempotent upsert.** An identical measure block is skipped, a differing one
  is replaced in place (its existing `lineageTag` is preserved), a missing one
  is inserted before the first column/partition block. New measures carry no
  `lineageTag`; Power BI Desktop assigns one on next open. A second run
  reports all `skip` and leaves the file byte-identical.
- **Partition safety.** The partition/M-source region is never edited, never
  echoed into any output, and is proven byte-identical by a post-write
  re-read; any difference rolls the file back and refuses.
- **`--dry-run`** prints the per-measure plan (insert/update/skip) and writes
  nothing.

Syncing grants no approval and marks no readiness stage. The printed next step
is `seshat value-check` -- the governed live verification of each measure
against gold values -- which is deliberately not run here.

## PBIX input

PBIX binaries are deliberately not parsed or modified. Save the file as a Power
BI Project in Power BI Desktop, then assess the resulting PBIP directory.

Static checks remain necessary but do not prove live semantic correctness. Run
the governed live validation at the appropriate readiness stage.
