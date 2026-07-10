---
description: Inspect Seshat BI readiness evidence read-only and recommend the next safe action -- edits nothing.
---

Review the project's readiness evidence and recommend -- without editing.

1. Gather the recorded state (fall back to `python -m retail.cli ...`):

   ```bash
   seshat status --format json
   seshat next --format agent
   ```

2. For the focus table (or $ARGUMENTS if the user named one), open and read
   the cited evidence: `mappings/<table>/readiness-status.yaml`, the
   `evidence` paths it lists (source profile, source map, migrations,
   metric contracts), and any `blocking-reasons.md` /
   `unresolved-questions.md`.
3. Report:
   - what each recorded stage's evidence actually shows (cite the files),
   - any recorded `pass` whose evidence list is empty or unreadable (flag
     it -- never paper over it),
   - open blockers and which named human owns each decision,
   - the one next safe action, taken from `next_allowed_action`.
4. This command is **read-only**: do not edit, create, or delete any file,
   do not run migrations, and do not grant or record any approval. If the
   user wants changes, they will ask explicitly -- then only the next
   allowed action applies.
