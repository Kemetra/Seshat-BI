export const meta = {
  name: 'speckit-batch',
  description: 'Batch-draft N specs in parallel, each in its own git worktree: run the Spec-Kit chain (specify -> plan -> tasks -> analyze) auto-answering clarifications with recommended defaults, then an advisor pass reviews every auto-decision. Output is review-ready spec drafts on isolated branches + a decision ledger for the human to ratify. AUTO-RECOVERY: resume-safe -- on a usage-limit hit, re-invoke with resumeFromRunId and it continues from the first unfinished step (completed agents replay from the journal; finished chain steps skip because their output files already exist on the branch).',
  phases: [
    { title: 'Draft chain (per spec, isolated)' },
    { title: 'Advisor review' },
    { title: 'Synthesize ledger' },
  ],
}

// =============================================================================
// INPUT (args): an array of feature ideas. Pass as a real JSON array:
//   args: [
//     { number: "007", name: "business-meaning-registry",
//       description: "A generic business-term registry + Arabic<->English retail dictionary ..." },
//     { number: "008", name: "grain-confidence-reviewer", description: "..." },
//   ]
// EXPLICIT numbers REQUIRED: parallel worktrees branch from the same main and would
// otherwise all auto-pick the same next NNNN (the speckit numbering race).
//
// AUTO-RECOVERY (resume after a usage-limit hit, WITHOUT restarting):
//   Two layers, both already designed in:
//   1. Harness journal: re-run Workflow({scriptPath, resumeFromRunId:"<runId>"}). Every
//      agent() call below is journaled; the longest unchanged prefix returns cached
//      results instantly, and execution resumes at the first call that had not finished.
//      Same script + same args => clean replay. (Do NOT edit the script between runs, or
//      the edited call and everything after it re-runs.)
//   2. Idempotent chain steps: each per-spec subagent SKIPS any chain step whose output
//      file already exists on its worktree branch (spec.md / plan.md / tasks.md / the
//      analyze report) and commits after EACH step. So even a brand-new process that lost
//      the journal re-attaches to the half-built branch and only does the missing steps --
//      it never re-writes a completed artifact or loses drafted work.
//   See .claude/workflows/speckit-batch.md for the operator recovery protocol.
// =============================================================================

// args may arrive already-parsed (array) OR as a JSON-encoded string (known
// Workflow serialization gotcha) -- normalize both to an array.
let IDEAS = []
if (Array.isArray(args)) {
  IDEAS = args
} else if (typeof args === 'string' && args.trim()) {
  try { const parsed = JSON.parse(args); if (Array.isArray(parsed)) IDEAS = parsed } catch (e) { /* leave empty -> guard below */ }
}
if (!IDEAS.length) {
  log('speckit-batch: no feature ideas in args. Pass [{number,name,description}, ...].')
  return { error: 'no feature ideas provided in args' }
}
for (const it of IDEAS) {
  if (!it || !it.number || !it.name || !it.description) {
    return { error: `each idea needs {number,name,description}; got ${JSON.stringify(it)}` }
  }
}

const DECISION_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['feature', 'branch', 'spec_dir', 'status', 'steps_done', 'auto_decisions', 'open_for_human', 'notes'],
  properties: {
    feature: { type: 'string' },
    branch: { type: 'string' },
    spec_dir: { type: 'string' },
    status: { type: 'string', enum: ['drafted', 'partial', 'failed'] },
    steps_done: {
      type: 'array', items: { type: 'string', enum: ['specify', 'plan', 'tasks', 'analyze'] },
      description: 'which chain steps produced/verified their output file this run (idempotent: pre-existing steps count as done)',
    },
    auto_decisions: {
      type: 'array',
      description: 'every clarification the chain auto-answered with a recommended default',
      items: {
        type: 'object', additionalProperties: false,
        required: ['question', 'auto_answer', 'rationale', 'reversible'],
        properties: {
          question: { type: 'string' },
          auto_answer: { type: 'string' },
          rationale: { type: 'string' },
          reversible: { type: 'string', enum: ['easy', 'costly', 'irreversible'] },
        },
      },
    },
    open_for_human: {
      type: 'array', items: { type: 'string' },
      description: 'decisions the chain REFUSED to auto-answer (Principle V: grain, PII, business rollup, identity)',
    },
    notes: { type: 'string' },
  },
}

const ADVISOR_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['feature', 'verdicts', 'must_change', 'overall'],
  properties: {
    feature: { type: 'string' },
    verdicts: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['question', 'verdict', 'recommendation'],
        properties: {
          question: { type: 'string' },
          verdict: { type: 'string', enum: ['confirm', 'change', 'flag-for-human'] },
          recommendation: { type: 'string' },
        },
      },
    },
    must_change: { type: 'array', items: { type: 'string' } },
    overall: { type: 'string', enum: ['ready-for-human-ratify', 'needs-rework', 'blocked'] },
  },
}

// --- Phase 1: per-spec chain, each in its OWN worktree; IDEMPOTENT + checkpointed ---
phase('Draft chain (per spec, isolated)')
const drafts = await parallel(IDEAS.map(idea => () => agent(
  `You are drafting ONE spec via the Spec-Kit chain in an ISOLATED git worktree (you were ` +
  `launched with worktree isolation). Repo: Seshat_BI.\n\n` +
  `FEATURE: ${idea.number}-${idea.name}\nDESCRIPTION: ${idea.description}\n` +
  `SPEC DIR: specs/${idea.number}-${idea.name}/\n\n` +
  `=== IDEMPOTENT / RESUME-SAFE EXECUTION (do this exactly) ===\n` +
  `This run may be a RESUME after an interruption. Before each chain step, CHECK whether its ` +
  `output already exists on this branch and SKIP it if so -- never overwrite a completed ` +
  `artifact, never restart from scratch:\n` +
  `  - specify -> specs/${idea.number}-${idea.name}/spec.md\n` +
  `  - plan    -> specs/${idea.number}-${idea.name}/plan.md\n` +
  `  - tasks   -> specs/${idea.number}-${idea.name}/tasks.md\n` +
  `  - analyze -> the analyze findings (record into specs/${idea.number}-${idea.name}/analysis.md)\n` +
  `For each step whose file is MISSING: run it, then COMMIT immediately on the worktree branch ` +
  `(one commit per step, message "docs: <step> (${idea.number})" -- P2 forbids a docs(NNN) scope) so progress is durable if the ` +
  `next step is interrupted. For each step whose file EXISTS: count it in steps_done and move on.\n\n` +
  `Run order: specify -> plan -> tasks -> analyze. Use SPECIFY_FEATURE_DIRECTORY=` +
  `specs/${idea.number}-${idea.name} and the explicit Number ${idea.number} (override auto-numbering ` +
  `so parallel worktrees do not collide).\n\n` +
  `=== CLARIFICATION POLICY ===\n` +
  `- When a step would STOP to ask a clarifying question, AUTO-ANSWER with the RECOMMENDED default ` +
  `for this repo (constitution Principles, RC1-RC16, the readiness spine) and RECORD it as an ` +
  `auto_decision (question + auto_answer + rationale + reversibility).\n` +
  `- EXCEPTION (Principle V -- do NOT auto-answer; put in open_for_human): grain, PII publish-safety, ` +
  `business-rollup/segment mappings, product-identity. Record the question; do not invent the answer.\n` +
  `- Artifacts: ASCII + UTF-8 no BOM; generic (no C086/pharmacy specifics); aligned to ` +
  `docs/roadmap/roadmap.md and the readiness stage this feature advances.\n` +
  `- Do NOT merge, push, or touch main. Leave commits on the worktree branch.\n\n` +
  `Return the decision record. status: 'drafted' if all four output files now exist, 'partial' if ` +
  `some remain (a later resume will finish them), 'failed' if the chain could not start.`,
  { label: `draft:${idea.number}-${idea.name}`, phase: 'Draft chain (per spec, isolated)', isolation: 'worktree', schema: DECISION_SCHEMA }
)))
const liveDrafts = drafts.filter(Boolean)

// --- Phase 2: advisor reviews every auto-decision (adversarial) ---
phase('Advisor review')
const reviews = await parallel(liveDrafts.map(d => () => agent(
  `You are the ADVISOR reviewing a batch-drafted spec's auto-answered clarifications for ` +
  `Seshat_BI. Be a skeptic -- the chain auto-answered with defaults; catch any that ` +
  `are wrong, risky, or a disguised human judgment call.\n\n` +
  `Draft decision record:\n${JSON.stringify(d)}\n\n` +
  `For EACH auto_decision: verdict = confirm | change (give the better answer) | flag-for-human ` +
  `(actually a Principle-V judgment call). An 'irreversible'/'costly' auto-decision should rarely ` +
  `be a silent confirm. list must_change for anything to revisit before the spec proceeds. ` +
  `overall: ready-for-human-ratify | needs-rework | blocked.`,
  { label: `advise:${d.feature}`, phase: 'Advisor review', schema: ADVISOR_SCHEMA, effort: 'high' }
)))
const liveReviews = reviews.filter(Boolean)

// --- Phase 3: consolidated ledger for the human advisor (you) to ratify ---
phase('Synthesize ledger')
const ledger = await agent(
  `Produce a concise, scannable DECISION LEDGER for the human advisor (the repo author, final ` +
  `authority) to ratify, from these batch-drafted specs + advisor reviews.\n\n` +
  `Drafts:\n${JSON.stringify(liveDrafts)}\n\nAdvisor reviews:\n${JSON.stringify(liveReviews)}\n\n` +
  `Markdown, ASCII only: (1) one-line status per feature (branch, spec_dir, status, steps_done, ` +
  `overall); (2) "MUST RATIFY" -- every decision the advisor said change/flag-for-human or that is ` +
  `costly/irreversible; (3) "confirmed defaults" FYI summary; (4) open_for_human per feature ` +
  `(Principle V calls never auto-answered); (5) next steps to ratify (enter each worktree branch, ` +
  `apply changes, open the PR); (6) RESUME note: if any feature status is 'partial', re-invoke the ` +
  `workflow with resumeFromRunId to finish the missing chain steps (idempotent -- done steps skip).`,
  { label: 'ledger', phase: 'Synthesize ledger', effort: 'high' }
)

return { drafts: liveDrafts, reviews: liveReviews, ledger }
