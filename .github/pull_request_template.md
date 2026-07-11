<!-- Keep the headings; fill in each section. Delete guidance comments. -->

## What changed and why

<!-- One or two sentences. Link the issue or starter lane if there is one. -->

## Readiness stage touched

<!-- Which of the seven stages (source_ready ... publish_ready) does this
     affect, or "none / tooling only"? A change may not skip a stage or
     grant an approval on anyone's behalf. -->

## Scope

<!-- Files/areas intentionally touched. If you claimed a starter lane, name
     it and confirm you stayed within its owned files. -->

## Tests and verification

<!-- Commands you ran and their result, e.g.:
     - ruff format --check src tests / ruff check src tests
     - pytest -m unit
     - retail check / retail semantic-check --repo .
     - lane-specific verification (see contribution-lanes.yaml) -->

## Evidence

<!-- What a reviewer can inspect to confirm the change does what it claims:
     test names, generated artifacts, before/after output. Statuses are
     evidence-backed here -- never a score. -->

## Human decisions

<!-- Any judgment call (grain, PII, business meaning, approval) this change
     surfaces or depends on, and the named human who owns it. "None" is a
     valid answer. -->

## Secret and data safety

- [ ] No secrets, real connection strings, or credentials are added.
- [ ] No real client data or PII is added; fixtures are synthetic.
- [ ] No machine-local absolute paths are committed.
