export const meta = {
  name: 'speckit-finish-chain',
  description: 'Finish the Spec-Kit chain for EXISTING specs that already have spec.md + plan.md + tasks.md but no analysis. Per spec, in its own git worktree: run an EXPLICIT advisor-driven /speckit-clarify (the agent reasons through each ambiguity, picks the RECOMMENDED answer, records it in the spec\'s ## Clarifications section -- never auto-answering a Principle-V judgment call), then idempotently fill any missing plan/tasks, then run the read-only /speckit-analyze and capture its report into analysis.md. Finally a BIG-PICTURE CONSISTENCY SENTINEL reads every finished spec together and confirms the batch stayed coherent (cross-spec scope overlap, duplicate stage ownership, vocabulary drift, a later spec assuming a deferred capability, C086 leak into a generic artifact). Output: a per-spec ledger (clarifications chosen + analyze verdict) + an overall CONSISTENT / DRIFT-FOUND. Resume-safe: re-invoke with resumeFromRunId; completed agents replay from the journal and finished chain steps skip because their output files already exist on the worktree branch.',
  phases: [
    { title: 'Finish chain (per spec, isolated)' },
    { title: 'Big-picture consistency' },
  ],
}

// =============================================================================
// INPUT (args): either
//   - an ARRAY of { number, name } for the specs to finish, e.g.
//       [ { number:"018", name:"companion-tools-architecture" }, ... ]
//   - OR an OBJECT { date:"YYYY-MM-DD", specs:[ {number,name}, ... ] } so the
//     clarify step can stamp the ## Clarifications "### Session <date>" heading
//     (workflow scripts cannot call new Date(); the date MUST be passed in).
// args may arrive as a real value OR a JSON-encoded STRING in some harness runs --
// parse-if-string at the boundary (see memory: workflow-args-stringified).
//
// AUTO-RECOVERY: this workflow is journaled. Re-invoke with
//   Workflow({ scriptPath:".claude/workflows/speckit-finish-chain.js",
//              resumeFromRunId:"<runId>" })
// Each per-spec subagent ALSO skips any chain step whose output already exists on
// its worktree branch and commits after each step, so even a lost journal
// re-attaches to a half-finished branch and only does the missing steps.
// =============================================================================

function coerce(a) {
  let v = a
  if (typeof v === 'string') {
    try { v = JSON.parse(v) } catch (e) { return { error: `args was a string that did not JSON.parse: ${String(e)}` } }
  }
  return { value: v }
}
const c = coerce(args)
if (c.error) { log(`speckit-finish-chain: ${c.error}`); return { error: c.error } }
let DATE = null
let SPECS = []
if (Array.isArray(c.value)) {
  SPECS = c.value
} else if (c.value && Array.isArray(c.value.specs)) {
  SPECS = c.value.specs
  DATE = typeof c.value.date === 'string' ? c.value.date : null
} else {
  const msg = 'pass an array of {number,name}, or {date, specs:[{number,name}]}'
  log(`speckit-finish-chain: ${msg}`); return { error: msg }
}
for (const s of SPECS) {
  if (!s || !s.number || !s.name) return { error: `each spec needs {number,name}; got ${JSON.stringify(s)}` }
}
if (!SPECS.length) { log('speckit-finish-chain: no specs in args.'); return { error: 'no specs provided' } }
// If no date supplied, the clarify step is told to OMIT a dated session heading
// rather than invent a date (it cannot call new Date()).
const DATE_NOTE = DATE
  ? `Use "### Session ${DATE}" as the Clarifications session heading.`
  : `No date was supplied; use "### Session (date pending)" and note in the ledger that the heading date must be filled in by the operator -- do NOT invent a date.`

const FINISH_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['feature', 'branch', 'spec_dir', 'status', 'steps_done', 'clarifications', 'open_for_human', 'analyze_verdict', 'analyze_critical', 'analyze_high', 'notes'],
  properties: {
    feature: { type: 'string' },
    branch: { type: 'string' },
    spec_dir: { type: 'string' },
    status: { type: 'string', enum: ['finished', 'partial', 'failed'] },
    steps_done: {
      type: 'array', items: { type: 'string', enum: ['clarify', 'plan', 'tasks', 'analyze'] },
      description: 'chain steps that produced/verified output this run (pre-existing plan/tasks count as done)',
    },
    clarifications: {
      type: 'array',
      description: 'every ambiguity the clarify step resolved by CHOOSING the recommended answer',
      items: {
        type: 'object', additionalProperties: false,
        required: ['question', 'recommended_answer', 'reasoning', 'reversible'],
        properties: {
          question: { type: 'string' },
          recommended_answer: { type: 'string' },
          reasoning: { type: 'string', description: 'the advisor reasoning that made this the recommended choice' },
          reversible: { type: 'string', enum: ['easy', 'costly', 'irreversible'] },
        },
      },
    },
    open_for_human: {
      type: 'array', items: { type: 'string' },
      description: 'ambiguities REFUSED auto-answer (Principle V: grain, PII publish-safety, business rollup/segment, product identity) -- recorded, never invented',
    },
    analyze_verdict: { type: 'string', enum: ['clean', 'findings', 'not-run'], description: 'result of the read-only /speckit-analyze pass' },
    analyze_critical: { type: 'number', description: 'count of CRITICAL findings from analyze' },
    analyze_high: { type: 'number', description: 'count of HIGH findings from analyze' },
    notes: { type: 'string' },
  },
}

phase('Finish chain (per spec, isolated)')
log(`Finishing the Spec-Kit chain for ${SPECS.length} existing spec(s) in isolated worktrees...`)

// pipeline: each spec flows clarify -> analyze independently (NO barrier between
// specs). The single per-spec agent runs the whole chain so the worktree + its
// own .specify/feature.json stay consistent within one isolated checkout.
const finished = await pipeline(
  SPECS,
  (spec) => agent(
    `You are FINISHING the Spec-Kit chain for ONE existing spec, in an ISOLATED git worktree ` +
    `(you were launched with worktree isolation -- you have your own checkout and your own ` +
    `.specify/feature.json). Repo: Seshat_BI.\n\n` +
    `FEATURE: ${spec.number}-${spec.name}\nSPEC DIR: specs/${spec.number}-${spec.name}/\n\n` +
    `This spec ALREADY HAS spec.md, plan.md, and tasks.md. Your job is to FINISH the chain: an ` +
    `explicit advisor-driven clarify, then (only if missing) plan/tasks, then the read-only analyze.\n\n` +
    `=== STEP 0: point .specify/feature.json at this feature ===\n` +
    `Write {"feature_directory":"specs/${spec.number}-${spec.name}"} to .specify/feature.json on ` +
    `THIS worktree so check-prerequisites.ps1 resolves to this feature. (Each worktree has its own copy.)\n\n` +
    `=== STEP 1: /speckit-clarify -- EXPLICIT, ADVISOR-DRIVEN, RECOMMENDED-ANSWER ===\n` +
    `Run the real /speckit-clarify process on specs/${spec.number}-${spec.name}/spec.md. For EACH ` +
    `ambiguity the taxonomy surfaces (max 5, highest Impact*Uncertainty first):\n` +
    `  1. THINK like the advisor: analyze all candidate options against this repo's constitution ` +
    `(Principles I-IX), the readiness spine, RC1-RC16 cleaning defaults, the roadmap stage this ` +
    `feature advances, and best practice. Determine the single MOST SUITABLE option with 1-2 ` +
    `sentences of reasoning.\n` +
    `  2. CHOOSE that recommended answer (this is the batch equivalent of the operator replying ` +
    `"recommended"). Record it: question + recommended_answer + reasoning + reversibility.\n` +
    `  3. WRITE it into the spec exactly as /speckit-clarify specifies: ensure a "## Clarifications" ` +
    `section exists; under it a "### Session" subheading (${DATE_NOTE}); append "- Q: <question> -> ` +
    `A: <answer>"; THEN apply the clarification to the right section (Functional Requirements / ` +
    `User Stories / Success Criteria / Edge Cases / terminology) with no contradictory leftover text. ` +
    `Save after each integration.\n` +
    `  HARD CARVE-OUT (Principle V -- do NOT choose an answer; put in open_for_human and record the ` +
    `question only): grain/uniqueness, PII publish-safety, business rollup/segment mappings, ` +
    `product identity. These are the repo author's calls; a default here is a disguised human judgment.\n` +
    `  If /speckit-clarify finds NO material ambiguity, record zero clarifications and continue -- do ` +
    `not invent questions to look busy.\n\n` +
    `=== STEP 2: plan / tasks -- IDEMPOTENT (skip if present) ===\n` +
    `plan.md and tasks.md already exist for this spec; verify they exist and COUNT them as done ` +
    `WITHOUT rewriting them. Only if a clarify answer MATERIALLY changed the spec in a way that ` +
    `invalidates the plan/tasks, note that in 'notes' (do NOT silently rewrite them -- flag for the ledger).\n\n` +
    `=== STEP 3: /speckit-analyze -- READ-ONLY, capture report ===\n` +
    `Run the real /speckit-analyze cross-artifact consistency pass over spec.md + plan.md + tasks.md. ` +
    `It is STRICTLY READ-ONLY -- it modifies none of those three. Capture its full Markdown report into ` +
    `specs/${spec.number}-${spec.name}/analysis.md (this capture is the ONLY write analyze produces, ` +
    `and it is our repo convention, not part of the read-only contract). Record analyze_verdict ` +
    `(clean if 0 CRITICAL and 0 HIGH; else findings), analyze_critical, analyze_high.\n\n` +
    `=== COMMIT DISCIPLINE (durable, resume-safe) ===\n` +
    `Commit on THIS worktree branch after each step that wrote a file (P2 forbids a docs(NNN) scope -- the number goes in the description): "docs: clarify (${spec.number})" ` +
    `after step 1 (spec.md changed), "docs: analyze (${spec.number})" after step 3 (analysis.md added). ` +
    `If a step's output already exists from a prior run, SKIP it and count it in steps_done. Do NOT ` +
    `merge, push, or touch main -- leave commits on the worktree branch.\n\n` +
    `=== CONSTRAINTS ===\n` +
    `ASCII + UTF-8 no BOM (Principle IX -- no em-dash, smart quote, arrow glyph, emoji; use -- and ->). ` +
    `Generic artifacts stay generic (no C086/pharmacy specifics; rule 7). Align every clarification to ` +
    `docs/roadmap/roadmap.md and the readiness stage this feature advances. Never fabricate a confidence ` +
    `score (rule 9). Never self-grant a readiness pass.\n\n` +
    `status: 'finished' if clarify ran and analyze produced analysis.md; 'partial' if some step ` +
    `remains for a later resume; 'failed' if the chain could not run.`,
    { label: `finish:${spec.number}-${spec.name}`, phase: 'Finish chain (per spec, isolated)', isolation: 'worktree', schema: FINISH_SCHEMA, effort: 'high' }
  )
)
const live = finished.filter(Boolean)

// --- Big-picture consistency sentinel (BARRIER: needs ALL finished specs at once) ---
// Consistency is a whole-batch property: the sentinel reads every finished spec
// FROM DISK (the worktree branches' committed files) plus the governing docs and
// judges the set, catching cross-spec problems no single-spec analyze can see.
phase('Big-picture consistency')

const CONSISTENCY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['per_spec', 'cross_spec_findings', 'clarification_consistency', 'overall', 'summary'],
  properties: {
    per_spec: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['feature', 'stage', 'verdict', 'findings'],
        properties: {
          feature: { type: 'string' },
          stage: { type: 'string', description: 'the readiness stage the roadmap says this feature advances' },
          verdict: { type: 'string', enum: ['consistent', 'minor-drift', 'major-drift'] },
          findings: {
            type: 'array',
            items: {
              type: 'object', additionalProperties: false,
              required: ['axis', 'finding', 'severity', 'fix'],
              properties: {
                axis: { type: 'string', enum: ['roadmap-stage', 'readiness-spine', 'constitution', 'hard-rule', 'c086-leak', 'fake-confidence', 'scope', 'clarification'] },
                finding: { type: 'string' },
                severity: { type: 'string', enum: ['low', 'medium', 'high'] },
                fix: { type: 'string' },
              },
            },
          },
        },
      },
    },
    cross_spec_findings: {
      type: 'array',
      description: 'problems visible ONLY across specs: scope overlap, two specs owning the same readiness stage, a later spec assuming a deferred capability (e.g. F016), the same concept named differently, a clarification in one spec that contradicts another',
      items: {
        type: 'object', additionalProperties: false,
        required: ['features', 'finding', 'severity', 'fix'],
        properties: {
          features: { type: 'array', items: { type: 'string' } },
          finding: { type: 'string' },
          severity: { type: 'string', enum: ['low', 'medium', 'high'] },
          fix: { type: 'string' },
        },
      },
    },
    clarification_consistency: {
      type: 'string',
      description: 'did the per-spec clarify steps choose answers that are mutually consistent across the batch (same default for the same kind of question)? note any divergence',
    },
    overall: { type: 'string', enum: ['CONSISTENT', 'DRIFT-FOUND'] },
    summary: { type: 'string', description: 'scannable markdown verdict the human can act on before ratifying' },
  },
}

const sentinel = await agent(
  `You are the BIG-PICTURE CONSISTENCY SENTINEL for Seshat_BI, run AFTER finishing the ` +
  `Spec-Kit chain on a batch of EXISTING specs. Your ONE job: judge the batch as a SET and surface any ` +
  `spec that drifted or any cross-spec incoherence -- including incoherence introduced by the per-spec ` +
  `clarify answers. You catch what no single-spec /speckit-analyze can see.\n\n` +
  `=== THE BATCH (per-spec finish records: clarifications chosen + analyze verdict) ===\n` +
  `${JSON.stringify(live)}\n\n` +
  `=== READ FROM DISK (ground truth -- do NOT trust the records alone) ===\n` +
  `1. Governing direction:\n` +
  `   - docs/roadmap/roadmap.md (feature sequence + the 9 HARD DESIGN RULES)\n` +
  `   - docs/readiness/readiness-model.md (the spine: 7 stages, 4 statuses, NO fake confidence)\n` +
  `   - .specify/memory/constitution.md (Principles I-IX, esp. II depend-never-fork, V judgment seams, VII C086-is-example, VIII docs-first, IX ASCII)\n` +
  `   - docs/superpowers/specs/2026-06-25-companion-modules-adapters-audit.md (the audit that authored 018-027: the binding 'Core Authority owns truth' rule + the F024 five categories)\n` +
  `2. EACH finished spec on its worktree branch: read the committed specs/<dir>/spec.md (esp. the new ` +
  `## Clarifications section) and analysis.md. The specs are on per-feature worktree branches (see each ` +
  `record's 'branch'). If a file is unreadable/missing, say so -- do NOT guess.\n\n` +
  `=== AXES (check every spec) ===\n` +
  `- roadmap-stage: does the spec actually advance the readiness stage the roadmap assigns it?\n` +
  `- readiness-spine: 4 statuses + evidence + blockers used correctly; stage ordering respected.\n` +
  `- constitution / hard-rule: violations of Principles or the 9 rules. Watch rule 5 (design needs ` +
  `contracts), rule 6 (no Power BI execution/publish before F016 -- a spec must not ASSUME F016 exists), ` +
  `rule 7 (C086 is an example, not the schema), rule 9 (no fake confidence).\n` +
  `- c086-leak: any pharmacy/C086 specific baked into a spec meant to be generic.\n` +
  `- fake-confidence: any invented confidence number / % readiness / score without defined rules.\n` +
  `- scope: a spec ballooning beyond its one-line roadmap scope, or duplicating another.\n` +
  `- clarification: a clarify answer that is WRONG for this repo, is a disguised Principle-V judgment ` +
  `call that should have been left open, or CONTRADICTS a clarify answer in another spec.\n\n` +
  `=== CROSS-SPEC (the reason this sentinel exists) ===\n` +
  `Surface problems visible ONLY across specs: two specs claiming the SAME readiness stage with ` +
  `overlapping scope; a later spec assuming an earlier/DEFERRED capability already exists; the same ` +
  `concept named differently across specs; the F024 five-category vocabulary used inconsistently; a ` +
  `clarification default chosen one way in spec A and the opposite way in spec B for the same question.\n\n` +
  `=== OUTPUT ===\n` +
  `Be a skeptic -- 'consistent' must be earned by reading the actual spec, not assumed. clarification_` +
  `consistency must explicitly assess whether the batch's clarify answers cohere. overall = 'DRIFT-FOUND' ` +
  `if ANY spec is major-drift OR any high-severity cross-spec finding exists; else 'CONSISTENT'. The ` +
  `summary must be a scannable markdown verdict the human can act on before ratifying.`,
  { label: 'consistency-sentinel', phase: 'Big-picture consistency', effort: 'high', schema: CONSISTENCY_SCHEMA }
)

return { finished: live, sentinel }
