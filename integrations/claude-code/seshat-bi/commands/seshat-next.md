---
description: Read Seshat BI readiness state and report the one next allowed action, its blockers, forbidden scope, and stop point.
---

Answer "what should happen next in this Seshat BI project?" from recorded
state only.

1. Run both read-only surfaces (fall back to `python -m retail.cli ...` if
   `seshat` is not on PATH):

   ```bash
   seshat status --format json
   seshat next --format agent
   ```

   If the user named a table ($ARGUMENTS), add `--table <table>` to the
   `next` call.
2. Summarize for the user, in this order:
   - **Stage:** `current_stage` and `readiness_state` (the four categorical
     statuses only -- never invent a percentage or a numeric readiness value).
   - **Blockers:** each `blocking_reasons` entry verbatim.
   - **Next allowed action:** `next_allowed_action`, and what artifact it
     produces.
   - **Forbidden right now:** the `forbidden_scope` items, briefly.
   - **Stop point:** where work must stop and which named human decides next.
3. Do NOT perform the action in this command -- this is a reporting command.
   Offer to proceed with the allowed action as a follow-up, and only that
   action.
