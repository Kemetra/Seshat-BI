---
name: seshat-bi
description: >
  Guarded operating procedure for driving the Seshat BI readiness system with
  Claude Code. Use whenever working in a Seshat BI project (a repo with
  mappings/<table>/readiness-status.yaml, the seshat/retail CLI, and the
  seven-stage readiness spine) -- onboarding a table, mapping a source,
  building silver/gold SQL, defining metrics, designing dashboards, or
  preparing a publish handoff. The agent inspects first, reads readiness
  state, performs ONLY the next allowed action, validates with seshat check,
  and stops at every human gate. It never skips a readiness stage, never
  self-grants an approval, and never commits, pushes, or opens a PR unless
  explicitly asked.
---

# Seshat BI -- guarded agent workflow

Seshat BI answers one question safely: *is this retail source ready to become
trusted Power BI analytics?* Data advances through seven gated stages
(Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard ->
Publish), and nothing advances without recorded evidence and a passed gate.
Your job is to prepare evidence and stop at gates -- never to grant them.

All state lives in the repo; the CLI is the single source of truth. Do not
duplicate or re-derive its logic.

## The loop (always, in this order)

1. **Inspect first (read-only).** Look at `mappings/` and the committed
   artifacts. Do not edit anything yet.
2. **Read `AGENTS.md`** -- the repo's operating contract and hard stops.
3. **Read the recorded state:**

   ```bash
   seshat status --format json
   ```

4. **Ask for the one allowed action:**

   ```bash
   seshat next --format agent
   ```

   The output names: `current_stage`, `readiness_state`, `evidence`,
   `blocking_reasons`, `next_allowed_action`, `forbidden_scope`,
   `validation_commands`, `stop_point`.
5. **Perform ONLY `next_allowed_action`.** Everything in `forbidden_scope`
   is off-limits, even if the user asked for it -- explain the gate instead.
6. **Validate after changes:**

   ```bash
   seshat check
   ```

   Exit 0 is necessary, not sufficient; report any finding honestly.
7. **Stop at `stop_point`.** Report what you produced, what is blocked, and
   which named human must decide next.

If `seshat` is not on PATH, every verb also runs as
`python -m retail.cli <verb>` from the repo root.

## Hard rules (never cross these)

- **Never skip a readiness gate.** No silver SQL before Mapping Ready
  passes; no gold before Silver Ready; no dashboard work before metric
  contracts / Semantic Model Ready; no publish work before handoff /
  Publish Ready.
- **Never self-grant an approval.** Approvals (grain, PII publish-safety,
  business rollups, metric definitions, publish) are named-human actions
  recorded in `readiness-status.yaml`.
- **Never fabricate readiness.** Missing evidence means the conservative
  evidence-first action (profile, record status) -- never an assumed pass,
  never an invented number.
- **Never write secrets** (DSNs, hosts, passwords) into tracked files; live
  values missing means `[PENDING LIVE PROFILE]`.
- **Git discipline:** stop before commit / push / PR unless the user
  explicitly requests it. Never use `git add -A`. Never stage files
  unrelated to the one action you performed.

## When the user asks for a forbidden jump

Do not comply silently and do not refuse rudely. Run `seshat next`, show the
recorded blocker or missing gate, name the human decision that unblocks it,
and offer the allowed action instead.
