# Run-Next Readiness -- usage and boundary

- **On-disk spec:** `specs/080-run-next-readiness-state-machine/`  **Roadmap feature:** F080
  (the roadmap F-number is authoritative when the two disagree).
- **Status:** Runtime slice shipped: `retail next` wraps the pure read-only helper
  in `src/seshat/run_next.py`.
- **Authority category:** Product Module / `read-only` (F024 Companion Tools
  Architecture -- see `../architecture/product-modules.md`).
- **Skill:** `../../.claude/skills/run-next-readiness/SKILL.md`.
  **Response contract:** `../../specs/080-run-next-readiness-state-machine/contracts/run-next-response.md`.

## What it is

Run-Next Readiness answers one question for ONE table: *what is the single next
allowed action?* It reads that table's Core Authority artifact --
`mappings/<table>/readiness-status.yaml` (ADR 0004) -- walks the seven readiness
stages in fixed order (Source -> Mapping -> Silver -> Gold -> Semantic Model ->
Dashboard -> Publish), finds the earliest non-`pass` stage, and returns exactly
one outcome: a forward `next_action`, a `stop_blocked` (citing `blocking_reasons`
verbatim), an `approval_required` (naming the human authority class), a
`terminal_pass`, or an `input_defect` -- plus any caveats. The agent is the
runtime; it computes the answer and STOPS. It creates no truth, executes nothing,
grants no approval, and emits no numeric score.

## CLI

```bash
retail next --table retail_store_sales
retail next --table bronze.retail_store_sales --format json
```

`--table` may name the `mappings/<table>/` directory, the status file's
`source_id`, or the status file's `table` value. The command is read-only: it
does not run `retail check`, `retail validate`, SQL, Power BI, or any approval
write-back.

## When to use it -- and when to use a neighbor instead

It reads the SAME `readiness-status.yaml` as three neighbors but does a distinct
job:

| Ask | Use |
|-----|-----|
| "What is the ONE next allowed action for THIS table, computed fresh?" | Run-Next Readiness (this tool) |
| "Actually DO the next step and self-heal against the gate" | `retail-orchestrate` (it executes; this tool only decides) |
| "Which stage has EACH table reached, with evidence + approvals timeline?" | Readiness Viewer (F026, renders many tables) |
| "What is broken across all tables, worst-first?" | F012 Data Quality Control Room |
| "Is this file's readiness status internally consistent?" | RS1 in `retail check` (the static linter) |

The genuine deltas: this tool COMPUTES a fresh next action from the seven stage
statuses (the viewer/control-room RENDER the stored `next_action` string
verbatim); it works on ONE table (they aggregate many); it DECIDES only
(`retail-orchestrate` executes); and when the computed action disagrees with the
stored `next_action`, it reports BOTH and flags the disagreement rather than
trusting the stored string.

## The read-only contract

- Reads `readiness-status.yaml` and the `docs/readiness/<stage>-ready.md`
  reference docs; writes NOTHING. The proof is `git status --short` empty after
  any invocation (SC-003).
- Applies the SAME approval-shape rule as the gate
  (`src/seshat/rules/readiness_status.py::_owner_is_valid`) so its notion of
  "approved" agrees with `retail check` -- but it does not call RS1, add a rule
  ID, or require RS1-clean input first (it degrades gracefully on a dirty file).
- Emits no numeric confidence / health / percent-ready score (hard rule #9).
- Never executes the action and never grants an approval (Principle V).

For the exact response field shape and five worked examples, see the response
contract linked above.
