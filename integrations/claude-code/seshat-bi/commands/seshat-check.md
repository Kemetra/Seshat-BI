---
description: Run the Seshat BI static governance gate and report its findings honestly (exit code is the authority).
---

Run the governance gate and report it without softening.

1. Run (fall back to `python -m retail.cli check --repo .`):

   ```bash
   seshat check --repo .
   ```

2. Report honestly:
   - Exit 0: say the static gate passes -- and remind that a green static
     check is necessary but NOT sufficient (live correctness needs
     `seshat validate` with a configured database).
   - Non-zero: list every finding verbatim (severity, rule id, message,
     locator). Do not summarize findings away, do not call a failing gate
     "mostly clean", and do not disable or work around a rule.
3. If findings exist, map each rule id to its fix location (the repo's
   `docs/glossary.md` catalogs rule ids) and propose the smallest compliant
   fix -- but only apply fixes the user asks for, and only within the scope
   of the current allowed action from `/seshat-next`.
