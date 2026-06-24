# speckit-batch -- operator runbook

Batch-draft several specs at once. Each feature runs the Spec-Kit chain
(`specify -> plan -> tasks -> analyze`) in its **own git worktree** (so the shared
`.specify/feature.json` singleton never collides), auto-answering clarifications
with recommended defaults, then an **advisor pass** reviews every auto-decision.
Output: review-ready spec drafts on isolated branches + a **decision ledger** for
you (the human advisor) to ratify. Nothing is merged or pushed automatically.

Script: `.claude/workflows/speckit-batch.js`.

## Invoke

```
Workflow({
  name: "speckit-batch",
  args: [
    { number: "007", name: "business-meaning-registry",
      description: "Generic business-term registry + Arabic<->English retail dictionary; advances Source Ready. No C086 specifics." },
    { number: "008", name: "grain-confidence-reviewer",
      description: "Grain-uniqueness confidence + mapping-version diff reviewer; advances Mapping Ready." }
  ]
})
```

- **`number` is REQUIRED and must be explicit + unique.** Parallel worktrees all
  branch from `main` and would otherwise auto-pick the same next `NNNN` (the
  speckit numbering race). Use the roadmap ids (`docs/roadmap/roadmap.md`).
- Keep each `description` generic and tied to the readiness stage it advances.

## What you get back

1. **Drafts** on per-feature worktree branches (committed, one commit per chain
   step -- never pushed, never merged).
2. **A decision ledger** (the workflow's final output) with:
   - status per feature (branch, spec_dir, steps_done, overall),
   - **MUST RATIFY** -- every auto-decision the advisor flagged change /
     flag-for-human, or that is costly/irreversible: YOUR call,
   - confirmed-defaults FYI, and the **open_for_human** Principle-V questions the
     chain refused to auto-answer (grain, PII, business rollup, identity).

You ratify by entering each worktree branch, applying the changes you decide, then
opening the PR.

## AUTO-RECOVERY -- resume after a usage-limit hit (no restart)

The workflow is **resume-safe by design** -- a limit hit does NOT lose work or
restart from the beginning. Two layers:

**Layer 1 -- harness journal (the resume primitive).**
Every `agent()` call is journaled. To resume:

```
Workflow({ scriptPath: ".claude/workflows/speckit-batch.js", resumeFromRunId: "<runId>" })
```

- The `runId` is printed when the workflow launches (and in `/workflows`).
- The longest unchanged prefix of `agent()` calls **replays from cache instantly**;
  execution resumes at the first call that had not finished. Same script + same
  `args` => clean replay.
- **Do NOT edit the script between runs** -- the first edited call and everything
  after it re-runs. (Editing `args` also invalidates the prefix.)

**Layer 2 -- idempotent chain steps (survives even a lost journal).**
Each per-spec subagent **skips any chain step whose output file already exists** on
its worktree branch (`spec.md` / `plan.md` / `tasks.md` / `analysis.md`) and
**commits after each step**. So even a brand-new process with no journal re-attaches
to the half-built branch and only does the missing steps -- a `partial` feature is
finished, never re-written, on the next run.

### Hands-off auto-resume (optional)

If a limit reset time is known, schedule the resume so you do not babysit it:

- Use `ScheduleWakeup` / `/loop` with a delay past the reset, firing a step that
  re-invokes `Workflow({ scriptPath, resumeFromRunId })`. Pick a delay matched to
  the reset window (the harness clamps 60-3600s; for a multi-hour reset, fire a
  long fallback and let the notification re-invoke you).
- The resume is safe to fire repeatedly: if everything already completed, every
  `agent()` replays from cache and the workflow returns its ledger immediately.

## Design notes (why it is shaped this way)

- **Sequential within a spec, parallel across specs.** specify->plan->tasks->analyze
  each consumes the prior step's file; the only parallelism is running N independent
  specs at once -- which is exactly what worktree isolation enables.
- **Auto-answer + advisor + you.** Headless subagents cannot stop for a human, so
  they auto-answer with recommended defaults BUT record every decision; the advisor
  pass reviews them; you ratify. Principle V is honored -- grain/PII/rollup/identity
  are never auto-answered, they go to `open_for_human`.
- **No merge, no push, no main writes.** Drafts stay on worktree branches until you
  ratify and open the PR.

## See also

- The chain skills: `.claude/skills/speckit-*`.
- The readiness stages each feature advances: `docs/readiness/`,
  `docs/roadmap/roadmap.md`.
- Agent rules: `AGENTS.md`. Constitution: `.specify/memory/constitution.md`.
