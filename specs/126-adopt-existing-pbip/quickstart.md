# Quickstart: Governed Existing PBIP Adoption

## 1. Assess without changing the project

```powershell
seshat adopt-pbip assess --project C:\work\SalesAnalytics --format text
```

Expected result: a coverage boundary, cited facts, existing governance findings,
concrete blockers, one next step, and an assessment digest. The project has no
new or changed file.

For an agent-readable result:

```powershell
seshat adopt-pbip assess --project C:\work\SalesAnalytics --format json
```

Review the `scaffold_plan.writes` list and `next_step`. A PBIP project with no
source/readiness evidence stays at Source Ready even if it already has measures
and report pages.

## 2. Handle a non-Git project

Assessment is still useful, but its one next step tells you to initialize version
control. Do that yourself, review the files, and reassess:

```powershell
git -C C:\work\SalesAnalytics init
seshat adopt-pbip assess --project C:\work\SalesAnalytics --format text
```

The adoption feature never runs `git init`, stages, commits, or pushes.

## 3. Explicitly accept the current scaffold plan

Copy the 64-character digest from the assessment you reviewed:

```powershell
seshat adopt-pbip scaffold `
  --project C:\work\SalesAnalytics `
  --accept-assessment <assessment-digest> `
  --format text
```

Success creates only
`.seshat/adoption/pbip-adoption.yaml`. If any assessed input changed, the digest
is stale and nothing is written; reassess and review again. If the target already
exists, the command refuses rather than overwriting it.

## 4. Review and commit the evidence seam

```powershell
git -C C:\work\SalesAnalytics diff -- .seshat/adoption/pbip-adoption.yaml
git -C C:\work\SalesAnalytics add .seshat/adoption/pbip-adoption.yaml
git -C C:\work\SalesAnalytics commit -m "chore: record Seshat PBIP adoption baseline"
```

This is a human Git action. The manifest contains observations and proposals,
not approvals or readiness passes.

## 5. Reassess after governance work

```powershell
seshat adopt-pbip assess --project C:\work\SalesAnalytics --format text
```

Changed PBIP/governance inputs are surfaced against the accepted baseline. The
next step is recomputed through existing readiness rules; follow only that stage.

## 6. PBIX input

```powershell
seshat adopt-pbip assess --project C:\work\Legacy.pbix --format text
```

The command does not open or extract the binary. It returns a supported stop:
open the file in Power BI Desktop, save it as a Power BI Project (PBIP), then
assess the saved project directory.

## Verification checklist

- Run the assessment twice and confirm substantive JSON is identical.
- Compare file hashes before/after assessment; every input remains identical.
- Confirm text and JSON list the same facts, blockers, evidence, and next step.
- Seed a stale digest or target collision and confirm `written` is empty.
- Run `seshat check` after committing the new manifest; remember that a green
  static gate does not claim live semantic correctness.
