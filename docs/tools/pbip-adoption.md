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

## PBIX input

PBIX binaries are deliberately not parsed or modified. Save the file as a Power
BI Project in Power BI Desktop, then assess the resulting PBIP directory.

Static checks remain necessary but do not prove live semantic correctness. Run
the governed live validation at the appropriate readiness stage.
