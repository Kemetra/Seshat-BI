export const meta = {
  name: 'speckit-batch-with-drift-lens',
  description: 'Run speckit-batch over a set of feature ideas (each spec drafted specify->plan->tasks->analyze in its own worktree, auto-answering clarifications with recommended defaults, then a per-spec advisor pass), THEN add a final BIG-PICTURE DRIFT LENS: a cross-cutting sentinel that reads every drafted spec together and confirms none drifted from the roadmap, the readiness spine, the constitution + 9 hard rules, or each other (scope overlap, duplicate stage ownership, a later-tier spec assuming a deferred capability, a generic template absorbing C086 specifics). Wraps the proven speckit-batch script via workflow() so that resume-safe script stays untouched; the drift lens is journaled here. Output: the batch ledger + a drift report with a per-spec verdict and an overall PASS / DRIFT-FOUND.',
  phases: [
    { title: 'Batch draft + advisor (speckit-batch)' },
    { title: 'Big-picture drift lens' },
  ],
}

// =============================================================================
// INPUT (args): SAME shape speckit-batch expects -- an array of feature ideas,
// each { number, name, description }. Passed straight through to the child.
//   args: [ { number:"007", name:"...", description:"..." }, ... ]
//
// AUTO-RECOVERY: this wrapper is itself journaled. Re-invoke with
//   Workflow({ scriptPath:".claude/workflows/speckit-batch-with-drift-lens.js",
//              resumeFromRunId:"<runId>" })
// The child speckit-batch's per-agent calls run UNDER this run's journal (nesting
// is one level), so a resume replays completed child agents from cache and only
// re-runs unfinished work. The child's own Layer-2 idempotency (skip a chain step
// whose output file already exists on the worktree branch) still applies, so even
// a lost journal re-attaches to half-built branches. The drift lens re-runs on
// resume only if it had not completed -- it reads spec files from disk, so it is
// safe to re-run.
// =============================================================================

// args may arrive as a real array OR (in some harness runs) as a JSON-encoded
// STRING -- validate at the boundary and parse-if-string rather than trust it.
function coerceIdeas(a) {
  let v = a
  if (typeof v === 'string') {
    try { v = JSON.parse(v) } catch (e) { return { error: `args was a string that did not JSON.parse: ${String(e)}` } }
  }
  if (!Array.isArray(v)) return { error: `args did not resolve to an array (got ${typeof v})` }
  return { value: v }
}
const coerced = coerceIdeas(args)
if (coerced.error) {
  log(`speckit-batch-with-drift-lens: ${coerced.error}. Pass [{number,name,description}, ...].`)
  return { error: coerced.error }
}
const IDEAS = coerced.value
if (!IDEAS.length) {
  log('speckit-batch-with-drift-lens: no feature ideas in args. Pass [{number,name,description}, ...].')
  return { error: 'no feature ideas provided in args' }
}

const DRIFT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['per_spec', 'cross_spec_findings', 'roadmap_coverage', 'overall', 'summary'],
  properties: {
    per_spec: {
      type: 'array',
      description: 'one entry per drafted spec',
      items: {
        type: 'object', additionalProperties: false,
        required: ['feature', 'intended_stage', 'verdict', 'drift_findings'],
        properties: {
          feature: { type: 'string' },
          intended_stage: { type: 'string', description: 'the readiness stage the roadmap says this feature advances' },
          verdict: { type: 'string', enum: ['on-track', 'minor-drift', 'major-drift'] },
          drift_findings: {
            type: 'array',
            description: 'concrete drift vs roadmap / readiness spine / constitution / hard rules; empty if on-track',
            items: {
              type: 'object', additionalProperties: false,
              required: ['axis', 'finding', 'severity', 'fix'],
              properties: {
                axis: { type: 'string', enum: ['roadmap-stage', 'readiness-spine', 'constitution', 'hard-rule', 'c086-leak', 'fake-confidence', 'scope'] },
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
      description: 'problems visible ONLY across specs: scope overlap, two specs owning the same stage, ordering violation (a later-tier spec assuming a deferred capability), inconsistent vocabulary for the same concept',
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
    roadmap_coverage: {
      type: 'object', additionalProperties: false,
      required: ['expected_features', 'drafted_features', 'missing', 'unexpected'],
      properties: {
        expected_features: { type: 'array', items: { type: 'string' } },
        drafted_features: { type: 'array', items: { type: 'string' } },
        missing: { type: 'array', items: { type: 'string' }, description: 'requested features with no readable spec on disk' },
        unexpected: { type: 'array', items: { type: 'string' }, description: 'specs drafted that were not requested' },
      },
    },
    overall: { type: 'string', enum: ['PASS', 'DRIFT-FOUND'] },
    summary: { type: 'string', description: 'scannable markdown verdict for the human: what passed, what drifted, what to fix before ratifying' },
  },
}

// --- Phase 1: delegate the whole batch to the proven, resume-safe child --------
phase('Batch draft + advisor (speckit-batch)')
log(`Delegating ${IDEAS.length} feature(s) to speckit-batch (isolated worktrees, advisor pass)...`)
const batch = await workflow('speckit-batch', IDEAS)

// --- Phase 2: big-picture drift lens (barrier: needs ALL drafts at once) -------
// This is a genuine sync point -- drift is a whole-batch property. The sentinel
// reads every drafted spec FROM DISK (the worktree branches' committed files) plus
// the governing docs, and judges the batch as a set, not spec-by-spec.
phase('Big-picture drift lens')
const draftsForLens = (batch && Array.isArray(batch.drafts)) ? batch.drafts : []
const reviewsForLens = (batch && Array.isArray(batch.reviews)) ? batch.reviews : []

const drift = await agent(
  `You are the BIG-PICTURE DRIFT SENTINEL for Retail_Tower_analytics -- the final ` +
  `lens after a batch of specs was drafted. Your ONE job: confirm the whole batch ` +
  `stayed coherent and on-direction, and surface any spec that drifted. You judge ` +
  `the batch as a SET, catching problems no per-spec review can see.\n\n` +
  `=== WHAT WAS REQUESTED (the intended roadmap features) ===\n` +
  `${JSON.stringify(IDEAS, null, 2)}\n\n` +
  `=== BATCH OUTPUT (drafts + per-spec advisor reviews) ===\n` +
  `Drafts:\n${JSON.stringify(draftsForLens)}\n\nAdvisor reviews:\n${JSON.stringify(reviewsForLens)}\n\n` +
  `=== READ THESE FROM DISK (ground truth -- do NOT trust the summaries alone) ===\n` +
  `1. The governing direction:\n` +
  `   - docs/roadmap/roadmap.md  (the feature sequence + the 9 HARD DESIGN RULES)\n` +
  `   - docs/readiness/readiness-model.md  (the spine: 7 stages, 4 statuses, NO fake confidence)\n` +
  `   - docs/architecture/readiness-pipeline.md\n` +
  `   - .specify/memory/constitution.md  (Principles, esp. IV agent-first, V human-judgment seams, VIII docs-first)\n` +
  `   - AGENTS.md\n` +
  `2. EACH drafted spec on its worktree branch. For every requested feature, read its\n` +
  `   committed specs/<dir>/spec.md (and plan.md / tasks.md / analysis.md if present).\n` +
  `   The drafts are on per-feature worktree branches (see each draft's 'branch' field);\n` +
  `   read the spec files there. If a spec file is unreadable/missing, record it as\n` +
  `   roadmap_coverage.missing -- do NOT guess its content.\n\n` +
  `=== DRIFT AXES (check every spec against every axis) ===\n` +
  `- roadmap-stage: does the spec ACTUALLY advance the readiness stage the roadmap\n` +
  `  assigns its feature? (e.g. a 'Mapping Ready' feature must not quietly build gold.)\n` +
  `- readiness-spine: does it use the 4 statuses + evidence + blockers correctly, and\n` +
  `  fit the stage-ordering (no stage entered before the prior is pass)?\n` +
  `- constitution / hard-rule: violations of the 9 hard rules, especially:\n` +
  `    #1 agent-first not CLI-first; #2 no source direct to silver; #3 no silver without\n` +
  `    profile+map+grain+resolved questions; #4 no gold to Power BI before validation;\n` +
  `    #5 no dashboard design before metric contracts; #6 no pbi-cli/PBIP automation\n` +
  `    before semantic-model readiness (F016 is LAST -- a spec here must not assume it);\n` +
  `    #7 C086 is a worked example, NOT the schema; #8 docs/templates first; #9 NO fake\n` +
  `    confidence (no numeric score without defined rules + evidence).\n` +
  `- c086-leak: any pharmacy / C086 / ezaby specific value, table, or term baked into a\n` +
  `  spec that is supposed to be generic.\n` +
  `- fake-confidence: any spec inventing a confidence number, % readiness, or score\n` +
  `  without the deferred scoring rules existing.\n` +
  `- scope: a spec ballooning beyond its one-line roadmap scope, or duplicating another.\n\n` +
  `=== CROSS-SPEC (the reason this lens exists) ===\n` +
  `Surface problems visible ONLY across specs: two specs claiming the SAME readiness\n` +
  `stage with overlapping scope (watch F009 vs F010 -- both 'Semantic Model Ready');\n` +
  `a later-tier spec assuming an earlier-tier or DEFERRED capability already exists;\n` +
  `the same concept named differently across specs; a gap where the sequence is broken.\n\n` +
  `=== OUTPUT ===\n` +
  `Be a skeptic. 'on-track' must be earned by reading the actual spec, not assumed.\n` +
  `Fill roadmap_coverage by comparing requested features to specs you could actually\n` +
  `read on disk. overall = 'DRIFT-FOUND' if ANY spec is major-drift OR any high-severity\n` +
  `cross-spec finding exists; else 'PASS'. The summary must be a scannable markdown\n` +
  `verdict the human can act on before ratifying.`,
  { label: 'drift-lens', phase: 'Big-picture drift lens', effort: 'high', schema: DRIFT_SCHEMA }
)

return { batch, drift }
