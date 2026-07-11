---
description: Verify the Seshat BI CLI is available, then scaffold a fresh project workspace (never modifies an existing project unexpectedly).
---

Initialize a Seshat BI project safely.

1. **Verify the CLI first.** Run `seshat check --repo .` (or
   `python -m retail.cli check --repo .` if `seshat` is not on PATH). If
   neither works, stop and tell the user how to install:
   `pip install -e ".[dev]"` from a clone of
   https://github.com/ahmed-shaaban-94/Seshat_BI -- do not improvise a
   different install path.
2. **Check the target.** If the current directory already contains a Seshat
   BI project (a `mappings/` directory or `readiness-status.yaml` files), do
   NOT re-initialize or overwrite anything. Report what exists and suggest
   `/seshat-next` instead.
3. **Scaffold a fresh workspace** only when the user asked for a new project:

   ```bash
   seshat init-project <name>
   ```

   ($ARGUMENTS is the workspace name if the user provided one.)
4. Confirm the result with `cd <name> && seshat status --format json` and
   summarize the (empty) starting state plus the first allowed action from
   `seshat next --format agent`.

Never pass `--force` unless the user explicitly asks for it after you have
explained it overwrites the scaffold's own files.
