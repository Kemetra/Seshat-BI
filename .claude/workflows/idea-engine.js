export const meta = {
  name: 'idea-engine',
  description: 'Idea generator for Seshat BI. Ground maps the real repo with five subsystem explorers + a reconcile-verify pass; Memory reads the prior bank so shipped/settled ideas are not regenerated; six role lenses (creative / BI analyst / technical / design / business-consumer / newcomer-operator) generate in parallel, then cross-pollinate; a completeness critic finds blind spots and triggers one targeted fill pass; a synthesizer merges; an adversarial skeptic challenges EVERY candidate (default-refuted); a four-standpoint reviewer PANEL scores value/feasibility and rules eligibility; a pure-JS aggregate takes the median, gates eligibility, and applies a demote-only clamp. Each idea is tagged with WHO it serves (end_user / operator / tool_internal) so a run heavy on tool-internal self-checking is a visible signal, not hidden. Model is matched to each stage: the idea-originating and verdict stages (Interpret / Generate / Completeness / Synthesize / Skeptic / Panel) run on Opus at xhigh effort; the context-gathering and reaction stages (Ground / Memory / Cross-pollinate / dissent / Rescue) run on Sonnet at high effort -- faster and cheaper without weakening any verdict. Output: a ranked NOW/HORIZON idea BANK, rendered deterministically -- exploratory inspiration, not a roadmap or commitment.',
  whenToUse: 'When you want a deep, exhaustive, rigorously vetted, history-aware idea bank for the project -- OR when you want to hand the engine your OWN rough/half-formed idea(s) to expand into a reviewable shape and run through the same skeptic + reviewer panel. Opus-xhigh on the idea/verdict stages + Sonnet-high on the gather/react stages, multi-round, multi-explorer, panel-reviewed -- thorough (many agents/tokens/time, though lighter than all-Opus). Re-runnable; pass a focus string, or {focus,sinceRef,date,ascii}, or {ideas:["rough words","another"]} / {seed:"rough words"} to review your own ideas (a bare string is treated as both focus AND a single seed idea). When ideas are supplied they are expanded, tagged origin:user, reviewed like any idea, and surfaced in a "Your Ideas" lane at the top. Output is an idea bank, never a plan.',
  phases: [
    { title: 'Ground',         detail: '5 subsystem explorers map the repo in parallel; JS merge + reconcile-verify', model: 'sonnet' },
    { title: 'Memory',         detail: 'read prior bank + Ground ship-status: label shipped/settled ideas (no re-litigation)', model: 'sonnet' },
    { title: 'Interpret',      detail: 'expand the USER\'S own rough idea(s) into reviewable shape + surface the chosen/rejected readings (only when ideas supplied)', model: 'opus' },
    { title: 'Generate',       detail: 'creative / BI / technical / design / consumer / operator lenses propose in parallel (round 1)', model: 'opus' },
    { title: 'Cross-pollinate',detail: 'each lens reacts to the others; surface cross-disciplinary ideas', model: 'sonnet' },
    { title: 'Completeness',   detail: 'critic finds blind spots -> one more targeted generation pass', model: 'opus' },
    { title: 'Synthesize',     detail: 'merge + dedupe into one candidate set', model: 'opus' },
    { title: 'Verify',         detail: 'adversarial skeptic challenges EVERY candidate (default-refuted)', model: 'opus' },
    { title: 'Panel-review',   detail: '4 independent reviewers (principle / shipped-dup / value-feasibility / design-foundation) score the set', model: 'opus' },
    { title: 'Aggregate',      detail: 'pure-JS median + eligibility gate + demote-only clamp; tiny prose agent for dissent', model: 'sonnet' },
    { title: 'Rescue',         detail: 'steelman the not-adopted ideas (reason only, never a re-score); skipped if none', model: 'sonnet' },
    { title: 'Render',         detail: 'pure-JS: render the idea-backlog markdown (no agent); orchestrator writes' },
  ],
}
const S = (...c) => String.fromCharCode(...c)

// Shared title-normalizer (module scope so the render stage can re-assert user-idea origin by
// title, using the SAME canonical identity aggregatePanel groups on -- a leading #N/N. number if
// present, else lowercased punctuation/whitespace-normalized prose). Keeping one definition means
// the render-side re-assert and the panel-side grouping can never drift apart.
const normKey = t => {
  const s = String(t || '').trim()
  const m = s.match(/^#?\s*(\d+)\s*[.:)]/)          // "#41.", "41.", "41)", "41:"
  if (m) return 'n' + m[1]
  return s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()   // fallback: normalized prose
}
// proseKey: user-idea matching ONLY. normKey collapses a numbered title ("#41. Foo") to "n41"
// for PANEL GROUPING -- correct there (reviewers keep the number, reword the trailing title), but
// WRONG for matching a survived user idea back to its interpreter title (which carries no number
// and normalizes to prose). proseKey STRIPS any leading list number, then normalizes prose, so a
// numbered candidate and the un-numbered interpreter title compare equal. Must NOT replace normKey
// in aggregatePanel (that would resurrect the number-collision over-count the file warns about).
const proseKey = t => String(t || '').trim()
  .replace(/^#?\s*\d+\s*[.:)]\s*/, '')                 // drop a leading "#41." / "41)" / "41:" prefix
  .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()

// Device-portable: never hardcode a machine path. The agents that consume REPO resolve
// the real repo root themselves at runtime (`git rev-parse --show-toplevel`), so this works
// from any device / user / worktree. The literal below is only a human-readable fallback hint.
const REPO = 'the repo root (resolve with `git rev-parse --show-toplevel`)'

// ---- args boundary (one coerce, shared by every fortification) ----
// args : undefined
//      | "<focus string>"                                      // back-compat: bare string = FOCUS
//      | { focus?, sinceRef?:"<a..b>", date?:"YYYY-MM-DD", ascii?:bool }
//      | a JSON-encoded STRING of the object above
// NOTE: unlike speckit-finish-chain's coerce (which THROWS on non-JSON), this one
// treats a non-JSON string as a bare focus -- so `args: "KPI coverage"` works.
function coerce(a) {
  if (typeof a !== 'string') return { value: a }       // already object/undefined
  const s = a.trim()
  if (!s) return { value: null }
  try { return { value: JSON.parse(s) } }              // JSON object/array
  catch { return { value: s } }                        // NOT JSON -> whole string is FOCUS
}
const _c = coerce(args)
const _A = (_c.value && typeof _c.value === 'object' && !Array.isArray(_c.value)) ? _c.value : {}
const FOCUS = typeof _c.value === 'string' ? _c.value.trim()
  : (typeof _A.focus === 'string' ? _A.focus.trim() : null)
// sinceRef: a git range "a..b" for the future ship-delta explorer (PR3). Validated
// here; consumed later. Absent -> roadmap markers only, never invent a range.
const SINCE_REF = (typeof _A.sinceRef === 'string'
  && /^[A-Za-z0-9_./~^-]+\.\.[A-Za-z0-9_./~^-]+$/.test(_A.sinceRef)) ? _A.sinceRef : null
// date: stamped into the rendered backlog (PR2). Scripts cannot call new Date();
// absent/malformed -> "(date pending)" placeholder for the human to fill.
const DATE = (typeof _A.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(_A.date)) ? _A.date : null
// ascii: normalize rendered output to ASCII (-- and ->). Default true (Principle IX).
const ASCII = typeof _A.ascii === 'boolean' ? _A.ascii : true
// USER IDEAS: the user's own rough/half-formed idea(s) to expand + review. Accepts
// args.ideas (array of strings) OR args.seed (single string) OR -- as a convenience --
// a bare string arg is treated as BOTH the focus AND a single seed idea (a user who
// types one idea shouldn't have to learn the object form). Trimmed, empties dropped,
// capped at 8 so a paste can't fan the pipeline out unbounded. Absent/empty -> null,
// and the Interpret stage is skipped (workflow behaves exactly as before).
const USER_IDEAS = (() => {
  const out = []
  if (Array.isArray(_A.ideas)) for (const s of _A.ideas) if (typeof s === 'string' && s.trim()) out.push(s.trim())
  if (typeof _A.seed === 'string' && _A.seed.trim()) out.push(_A.seed.trim())
  // bare-string arg: it is FOCUS already; also treat it as a single seed idea to review.
  if (!out.length && typeof _c.value === 'string' && _c.value.trim()) out.push(_c.value.trim())
  const seen = new Set()
  const dedup = out.filter(s => { const k = s.toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true })
  return dedup.length ? dedup.slice(0, 8) : null
})()
const HAS_USER_IDEAS = !!(USER_IDEAS && USER_IDEAS.length)
const FOCUS_LINE = FOCUS
  ? `\nFOCUS for this run (bias ideas toward this, but don\u0027t ignore strong off-theme ideas): ${FOCUS}\n`
  : ''

const PROJECT = `
PROJECT: Seshat BI (package alias Seshat_BI; formerly \u0022Tower BI Agent Kit\u0022). An AGENT-FIRST
Retail BI readiness system. It guides agents from raw retail sources through 7 readiness
stages -- Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish -- using
documented gates, evidence, and human approvals. The agent is the interface; CLI gates
(retail check, retail validate) are helpers it calls, never the product.

HARD PRINCIPLES (any idea that violates these is INELIGIBLE):
- Reasoning/knowledge layers NEVER execute (no running queries/DAX/Python, no DB touch).
- DEFINE vs CHECK vs APPROVE are separate; agents never self-grant a human approval.
- Generic-only: C086 (pharmacy) is one worked EXAMPLE, never a universal schema.
- No fabricated confidence: readiness = status + evidence + blockers, never a made-up score.
- Secrets only in gitignored .env; gold-only metric binding; never bypass readiness gates.
- YAGNI: add the seam, not speculative implementation, unless asked.

WHAT EXISTS (grounding):
- 5 router-first knowledge layers under skills/: bi-sql-knowledge (table grain),
  bi-dax-knowledge (filter context), bi-python-knowledge (dataframe grain, seed),
  bi-bigdata-knowledge (execution topology / distributed), retail-kpi-knowledge
  (business KPI meaning, seed -- newest, PR #58).
- Power BI design FOUNDATION under skills/powerbi-dashboard-design: a router+vocabulary over
  four surfaces (report visuals / external background / theme JSON / handoff). It DEFINES and
  CHECKS the presentation layer only -- it never authors a PBIP/PBIR, never generates DAX,
  never invents a metric (report execution/authoring is deferred F016).
- Roadmap F005-F015 SHIPPED; F016 (Power BI Execution Adapter) is the ONLY unbuilt core
  feature (deferred, execution-only, gated on semantic-model readiness). Tier 5 companion
  modules/adapters (F024-F034) are PARTLY shipped.
- Docs spine: docs/readiness/ (the stage model), docs/knowledge-map.md (the router),
  COMPASS.md + AGENTS.md (entry contract), docs/metrics/ (F009 metric-contract store +
  retail-kpi-catalog menu), docs/quality/agent-routing-smoke-test.md.

OUTPUT IS AN IDEA BANK, NOT A ROADMAP. Nothing generated here is planned, scheduled, or
approved. Verdicts/scores are a triage opinion only. Ideas advance only through the normal
spec/feature process with a human decision.
${FOCUS_LINE}`

// ---- model tiers (model matched to what the stage DECIDES) ----
// The rule: a stage that ORIGINATES or JUDGES an idea runs on Opus xhigh -- those
// outputs ARE the product and a weak model there makes the rigor decorative. A stage
// that only GATHERS context or reacts/rephrases runs on Sonnet high -- reliable code
// reading + reasoning, far faster/cheaper than Opus, and it decides no verdict.
// User directive: the non-Opus tier is Sonnet at HIGH effort (not medium/low) -- a
// quality safety-margin on the retrieval/reaction stages.
//   GATHER  -> Ground explorers, Ground reconcile, Memory, Cross-pollinate, Aggregate-dissent, Rescue
//   CREATE  -> Interpret, Generate, Completeness (originate ideas / read user intent)  [UNTOUCHABLE Opus]
//   JUDGE   -> Synthesize, Skeptic, Panel (decide verdicts / protect user ideas)       [UNTOUCHABLE Opus]
const GATHER = { model: 'sonnet', effort: 'high' }   // retrieval + reaction, decides no verdict
const CREATE = { model: 'opus',   effort: 'xhigh' }  // originates ideas / reads user intent -- the ideas themselves
const JUDGE  = { model: 'opus',   effort: 'xhigh' }  // synthesize / skeptic / panel -- the verdicts (the goal)
// Back-compat aliases so any un-repointed call still resolves; new calls use the tier names.
const SCOUT = GATHER
const LEAD  = JUDGE

const IDEA_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['lens', 'ideas'],
  properties: {
    lens: { type: 'string' },
    ideas: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'pitch', 'horizon', 'why_it_fits', 'rough_shape', 'strengthens_layer', 'serves'],
        properties: {
          title: { type: 'string' },
          pitch: { type: 'string', description: '2-3 sentences: what it is and the value' },
          horizon: { type: 'string', enum: ['NOW', 'HORIZON'] },
          why_it_fits: { type: 'string' },
          rough_shape: { type: 'string', description: 'the seam it touches, not full impl' },
          // WHO this idea ultimately serves -- the meta-bloat signal. 'end_user' = a business
          // reader/analyst gets analytical value; 'operator' = someone running/adopting the kit
          // gets a lower ramp; 'tool_internal' = the kit checks/maintains ITSELF (reconcilers,
          // self-audits, wiring gates). A run heavy on tool_internal is over-producing bookkeeping
          // -- selfMetrics tallies this so the ratio is a durable, self-correcting signal. Judged
          // honestly by the lens; never assigned by index. Mirrors strengthens_layer's rails.
          serves: { type: 'string', enum: ['end_user', 'operator', 'tool_internal'], description: 'who the idea ultimately serves: business reader (end_user), kit runner/adopter (operator), or the kit itself (tool_internal)' },
          // Which knowledge layer / spine this idea would strengthen -- surfaces layer
          // starvation in self-metrics. The lens JUDGES this; nothing is assigned by index.
          // 'design-system' = the Power BI presentation FOUNDATION (theme tokens, background/
          // canvas conventions, layout blueprints, accessibility/contrast, design-review
          // evidence) -- governance of the design layer, never report authoring.
          strengthens_layer: { type: 'string', enum: ['bi-sql', 'bi-dax', 'bi-python', 'bi-bigdata', 'retail-kpi', 'docs-spine', 'design-system', 'none'], description: 'the knowledge layer this most strengthens, or none' },
        },
      },
    },
  },
}

// The INTERPRET stage shape: it EXPANDS the user's rough words into fully-shaped ideas
// AND surfaces the reading it chose + the readings it rejected -- so a misread is visible,
// not silent (this recovers the value of pick-from-readings WITHOUT interrupting the run).
// Each expanded idea carries the full IDEA fields plus the accountability note. These ideas
// are injected into the candidate pool tagged origin:user and reviewed like any other.
const INTERPRET_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['expanded'],
  properties: {
    expanded: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'pitch', 'horizon', 'why_it_fits', 'rough_shape', 'strengthens_layer', 'serves', 'original_words', 'chosen_reading', 'rejected_readings', 'eligible_guess'],
        properties: {
          title: { type: 'string' },
          pitch: { type: 'string', description: '2-3 sentences: what it is and the value' },
          horizon: { type: 'string', enum: ['NOW', 'HORIZON'] },
          why_it_fits: { type: 'string' },
          rough_shape: { type: 'string', description: 'the seam it touches, not full impl' },
          strengthens_layer: { type: 'string', enum: ['bi-sql', 'bi-dax', 'bi-python', 'bi-bigdata', 'retail-kpi', 'docs-spine', 'design-system', 'none'] },
          serves: { type: 'string', enum: ['end_user', 'operator', 'tool_internal'] },
          original_words: { type: 'string', description: 'the user raw words, verbatim -- the accountability anchor' },
          chosen_reading: { type: 'string', description: 'one sentence: how you read the rough words to shape this idea' },
          rejected_readings: { type: 'array', items: { type: 'string' }, description: 'other plausible readings you did NOT pick, so the user can see if you misread them' },
          eligible_guess: { type: 'boolean', description: 'honest first guess whether it respects the hard principles; the panel rules for real' },
        },
      },
    },
  },
}

// Disposition enum keeps the repo's existing vocabulary minus 'not-challenged' (the
// "I didn't look" hole) -- 'killed' is KEPT (it is already in the committed backlog's
// triage history; renaming it to 'refuted' would silently break that record).
const DISPOSITION_ENUM = ['survived', 'weakened', 'killed']
const VERDICT_ENUM = ['ADOPT', 'CONSIDER', 'PARK', 'REJECT', 'SHIPPED']

const VERIFY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['challenged', 'skeptic_summary'],
  properties: {
    skeptic_summary: { type: 'string' },
    challenged: {
      type: 'array',
      description: 'EVERY candidate idea, each with a genuine refutation attempt',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'strongest_objection', 'objection_holds', 'disposition', 'why'],
        properties: {
          title: { type: 'string' },
          strongest_objection: { type: 'string' },
          objection_holds: { type: 'boolean' },
          disposition: { type: 'string', enum: DISPOSITION_ENUM },
          why: { type: 'string' },
        },
      },
    },
  },
}

const PANEL_REVIEWER_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['reviewer_standpoint', 'scored_ideas', 'summary'],
  properties: {
    reviewer_standpoint: { type: 'string' },
    summary: { type: 'string' },
    scored_ideas: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'horizon', 'eligible', 'ineligibility_reason', 'consistency', 'value_score', 'feasibility_score', 'verdict', 'survived_verification', 'prior_status', 'relitigation', 'rationale', 'strengthens_layer', 'serves', 'origin'],
        properties: {
          title: { type: 'string' },
          horizon: { type: 'string', enum: ['NOW', 'HORIZON'] },
          strengthens_layer: { type: 'string', enum: ['bi-sql', 'bi-dax', 'bi-python', 'bi-bigdata', 'retail-kpi', 'docs-spine', 'design-system', 'none'], description: 'carried from the idea: the knowledge layer it most strengthens' },
          serves: { type: 'string', enum: ['end_user', 'operator', 'tool_internal'], description: 'carried from the idea: who it ultimately serves (the meta-bloat signal)' },
          origin: { type: 'string', enum: ['user', 'engine'], description: 'carried from the idea: user = the human proposed it, engine = a lens generated it' },
          eligible: { type: 'boolean' },
          ineligibility_reason: { type: 'string', description: 'named principle, or "" if eligible' },
          consistency: { type: 'string', enum: ['consistent', 'minor-tension', 'conflict'] },
          value_score: { type: 'integer', minimum: 1, maximum: 10 },
          feasibility_score: { type: 'integer', minimum: 1, maximum: 10 },
          verdict: { type: 'string', enum: VERDICT_ENUM },
          survived_verification: { type: 'string', enum: DISPOSITION_ENUM },
          prior_status: { type: 'string', enum: ['new', 'shipped', 'rejected-settled', 'open-prior'] },
          relitigation: { type: 'string', enum: ['n/a', 'settled', 'materially-new'] },
          rationale: { type: 'string' },
          first_step: { type: 'string' },
        },
      },
    },
  },
}

const DISSENT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['dissent_by_title', 'portfolio_summary'],
  properties: {
    portfolio_summary: { type: 'string' },
    dissent_by_title: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'dissent'],
        properties: {
          title: { type: 'string' },
          dissent: { type: 'string' },
        },
      },
    },
  },
}

// aggregatePanel: PURE JS. Matches ideas by title across the 3 reviewer records and
// reduces to one verdict per idea. Median scores; eligibility gate (pass/fail/split);
// demote-only clamp (fail -> REJECT, split -> at most CONSIDER); majority verdict else
// the MORE CAUTIOUS of the tie. No Date/random; deterministic.
function aggregatePanel(panel, expectedReviewers, verifyRec) {
  const live = (panel || []).filter(Boolean)
  // A panelist that died (null) is a gate-integrity problem, not a smaller panel: if the
  // strict principle auditor fails, the remaining reviewers must not be treated as a
  // complete eligibility ruling. Track the shortfall so the gate can refuse to pass.
  const expected = Number.isFinite(expectedReviewers) ? expectedReviewers : live.length
  const panel_failed = Math.max(0, expected - live.length)
  // STABLE GROUPING KEY. The four reviewers all reference an idea by its leading number
  // (e.g. "#41. Symptom Concierge (which-layer-owns-this-symptom router)" vs "41. Symptom
  // Concierge -- cross-layer ... router") but PHRASE the trailing title differently. Grouping
  // on the raw free-text title therefore SPLIT one idea into 2-3 rows with divergent scores
  // (the 62-vs-42 over-count). groupKey() collapses each title to its canonical identity: the
  // leading #N / N. number when present, else a lowercased, punctuation/whitespace-normalized
  // form so near-identical prose still merges. Display keeps the first-seen human title.
  // Defined BEFORE challengedTitles so the skeptic set is normalized on the same key -- else
  // the coverage clamp would mis-fire on the skeptic's differently-phrased titles.
  const groupKey = normKey   // panel grouping uses the number-aware key; user-match uses proseKey
  // The skeptic's "challenge EVERY candidate" contract is enforced HERE in JS, not by the
  // schema (which only requires an array) or the prompt (a request). An idea the skeptic
  // silently omitted from challenged[] is treated as if it FAILED the gate: marked killed
  // and demoted out of ADOPT, mirroring the demote-only eligibility clamp. Unchallenged !=
  // safe -- it means coverage was not proven, so it must not read as a survived ADOPT.
  // Keyed via groupKey so the skeptic's title phrasing matches the reviewers' grouping.
  const challengedTitles = new Set(((verifyRec && Array.isArray(verifyRec.challenged) ? verifyRec.challenged : []))
    .map(ch => ch && ch.title).filter(Boolean).map(groupKey))
  let uncovered = 0
  // union of ideas by stable key, first-seen order preserved (reviewer 0 then 1 then 2). Carry
  // each reviewer's standpoint DOWN onto its rows so attribution survives grouping, and keep the
  // first-seen title as the row group's DISPLAY title.
  const order = []                 // stable keys, in first-seen order
  const seen = new Set()
  const byTitle = {}               // key -> reviewer rows
  const displayTitle = {}          // key -> first-seen human-readable title
  for (const reviewer of live) {
    const standpoint = reviewer.reviewer_standpoint || reviewer._key || 'reviewer'
    for (const si of (reviewer.scored_ideas || [])) {
      if (!si || !si.title) continue
      const key = groupKey(si.title)
      if (!seen.has(key)) { seen.add(key); order.push(key); displayTitle[key] = si.title }
      ;(byTitle[key] = byTitle[key] || []).push({ ...si, reviewer_standpoint: si.reviewer_standpoint || standpoint })
    }
  }
  const median = nums => {
    const a = nums.filter(n => Number.isFinite(n)).slice().sort((x, y) => x - y)
    if (!a.length) return 1
    const m = Math.floor(a.length / 2)
    return a.length % 2 ? a[m] : Math.round((a[m - 1] + a[m]) / 2)
  }
  // higher = wins a no-majority tie. SHIPPED is a CLOSED outcome (already-shipped, do not
  // relitigate) and must outrank the open verdicts: when the shipped-duplication auditor
  // alone recognizes a duplicate and the other two split on open verdicts, the candidate
  // closes as SHIPPED, not an open section. REJECT still tops it (a hard-principle kill
  // beats "we already shipped it").
  const cautionRank = { REJECT: 5, SHIPPED: 4, PARK: 3, CONSIDER: 2, ADOPT: 1 }
  const dispRank = { killed: 3, weakened: 2, survived: 1 }                       // worst-seen wins

  const ideas = order.map(key => {
    const rows = byTitle[key]
    const title = displayTitle[key]
    const n = rows.length
    const eligibleCount = rows.filter(r => r.eligible === true).length
    // A row count short of the expected panel means a reviewer (possibly the principle
    // auditor) never ruled -> this is NOT a clean pass. Unanimous-eligible among a SHORT
    // panel is downgraded to 'split' (needs human review) so a missing auditor can never
    // let an idea through the gate as if fully cleared.
    const fullPanel = n >= expected
    let eligibility_gate = eligibleCount === n ? 'pass' : (eligibleCount === 0 ? 'fail' : 'split')
    if (eligibility_gate === 'pass' && !fullPanel) eligibility_gate = 'split'

    const value_score = median(rows.map(r => r.value_score))
    const feasibility_score = median(rows.map(r => r.feasibility_score))
    const vs = rows.map(r => r.value_score).filter(Number.isFinite)
    const fs = rows.map(r => r.feasibility_score).filter(Number.isFinite)
    const score_spread = Math.max(
      vs.length ? Math.max(...vs) - Math.min(...vs) : 0,
      fs.length ? Math.max(...fs) - Math.min(...fs) : 0
    )

    // majority verdict if 2+ agree; else the MORE CAUTIOUS of those present.
    const counts = {}
    for (const r of rows) counts[r.verdict] = (counts[r.verdict] || 0) + 1
    let verdict = null, best = 0
    for (const v of Object.keys(counts)) if (counts[v] > best) { best = counts[v]; verdict = v }
    if (best < 2) {  // no majority -> most cautious present
      verdict = rows.map(r => r.verdict).sort((a, b) => (cautionRank[b] ?? 2) - (cautionRank[a] ?? 2))[0]
    }
    // demote-only clamp by the eligibility gate (can only move toward caution).
    // fail = all reviewers ineligible -> REJECT outright (a hard-principle failure does
    // not get to sit in PARK; the contract is fail -> REJECT). split = mixed/short panel
    // -> at most CONSIDER, never ADOPT.
    if (eligibility_gate === 'fail' && verdict !== 'REJECT') verdict = 'REJECT'
    if (eligibility_gate === 'split' && verdict === 'ADOPT') verdict = 'CONSIDER'

    // worst disposition any reviewer recorded
    let survived_verification = rows.map(r => r.survived_verification)
      .sort((a, b) => (dispRank[b] || 0) - (dispRank[a] || 0))[0] || 'survived'

    // skeptic-coverage clamp: an idea the adversarial skeptic never challenged has UNPROVEN
    // coverage -> treat it as killed and demote it out of ADOPT (mirrors the eligibility
    // clamp; demote-only, never promotes). This is what actually enforces the every-candidate
    // contract -- without it an omitted idea could ride through as a survived ADOPT.
    if (!challengedTitles.has(key)) {
      uncovered++
      survived_verification = 'killed'
      if (verdict === 'ADOPT') verdict = 'CONSIDER'
    }

    // most cautious consistency present
    const consRank = { conflict: 3, 'minor-tension': 2, consistent: 1 }
    const consistency = rows.map(r => r.consistency)
      .sort((a, b) => (consRank[b] || 0) - (consRank[a] || 0))[0] || 'consistent'

    // first non-empty first_step; horizon = majority/first
    const first_step = (rows.map(r => r.first_step).find(s => s && String(s).trim())) || 'None.'
    const horizon = rows.map(r => r.horizon).find(Boolean) || 'NOW'
    const strengthens_layer = rows.map(r => r.strengthens_layer).find(Boolean) || 'none'
    const serves = rows.map(r => r.serves).find(Boolean) || 'tool_internal'
    const origin = rows.map(r => r.origin).find(Boolean) || 'engine'
    // rationale: concatenate each reviewer's one-liner with its standpoint
    const rationale = rows.map(r => `[${r.reviewer_standpoint || S(114,101,118,105,101,119,101,114)}] ${r.rationale || S()}`.trim()).join(' ')

    return {
      title, horizon, consistency, value_score, feasibility_score, score_spread,
      eligibility_gate, verdict, survived_verification, first_step, rationale, strengthens_layer, serves, origin,
      _per_reviewer: rows.map(r => ({ standpoint: r.reviewer_standpoint, eligible: r.eligible, verdict: r.verdict, v: r.value_score, f: r.feasibility_score })),
    }
  })
  const splits = ideas.filter(i => i.eligibility_gate === 'split' || i.score_spread >= 4).map(i => i.title)
  return { ideas, splits, panel_failed, reviewers_seen: live.length, reviewers_expected: expected, uncovered_by_skeptic: uncovered }
}

// ===================== 1. GROUND (multi-agent explore + JS merge + verify) =====================
// One explorer could carry a blind spot into every downstream stage (it already did:
// the engine grounded on "4 knowledge layers" when there are 5). Five subsystem
// explorers read in parallel; a pure-JS merge unions + flags contradictions; one
// reconcile-verify agent re-opens cited evidence and downgrades unbacked claims.
phase('Ground')

// Shared status vocabulary -- used by submap ship-status, the reconcile ruling, and
// (later) cross-run memory. UNVERIFIED is the safe default: the gate treats it as
// "not shipped" so an unbacked claim can never read as a settled capability.
const STATUS_ENUM = ['SHIPPED', 'DEFERRED', 'PARTIAL', 'PLANNED', 'REJECTED-INELIGIBLE', 'UNVERIFIED']

const SUBMAP_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['subsystem', 'capability_notes', 'tensions', 'ship_status', 'unreadable'],
  properties: {
    subsystem: { type: 'string', enum: ['knowledge', 'src', 'docs', 'roadmap', 'ship-delta'] },
    capability_notes: { type: 'array', items: { type: 'string' }, description: 'factual capability statements, each citing a file/feature' },
    tensions: { type: 'array', items: { type: 'string' }, description: 'incomplete/duplicated/awkward seams -- idea fuel' },
    ship_status: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['feature_id', 'status', 'evidence_path'],
        properties: {
          feature_id: { type: 'string', description: 'F-number or named capability' },
          status: { type: 'string', enum: STATUS_ENUM },
          evidence_path: { type: 'string', description: 'the file/PR backing this status' },
        },
      },
    },
    unreadable: { type: 'array', items: { type: 'string' }, description: 'paths the explorer could not read (say so, do not guess)' },
  },
}

const MERGED_MAP_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['capability_map', 'tensions', 'ship_status', 'reconciliation_ledger', 'missing_subsystems', 'principles', 'verification_notes'],
  properties: {
    capability_map: { type: 'string', description: 'merged prose map by readiness stage -- the narrative substrate downstream lenses build on' },
    tensions: { type: 'array', items: { type: 'string' } },
    ship_status: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['feature_id', 'status', 'evidence_path', 'verifier_opened_evidence'],
        properties: {
          feature_id: { type: 'string' },
          status: { type: 'string', enum: STATUS_ENUM },
          evidence_path: { type: 'string' },
          // The verifier asserts it OPENED the cited file -- it does not certify its
          // own DEFINE. status==UNVERIFIED is treated as "not shipped" downstream.
          verifier_opened_evidence: { type: 'boolean' },
        },
      },
    },
    reconciliation_ledger: {
      type: 'array',
      description: 'each contradiction the explorers disagreed on, and how it was ruled by re-reading',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['feature_id', 'conflicting_claims', 'ruling', 'winning_evidence'],
        properties: {
          feature_id: { type: 'string' },
          conflicting_claims: { type: 'array', items: { type: 'string' } },
          ruling: { type: 'string', enum: STATUS_ENUM },
          winning_evidence: { type: 'string' },
        },
      },
    },
    missing_subsystems: { type: 'array', items: { type: 'string' }, description: 'explorers that died/returned null -- a verification signal, not a silent gap' },
    principles: { type: 'array', items: { type: 'string' } },
    verification_notes: { type: 'string' },
  },
}

// The 5 subsystem explorers. Each pins opus xhigh explicitly (never the Explore
// agentType Haiku default) and is read-only.
// NOTE: this clause is hoisted out of the ship-delta brief and built with string
// concatenation (NOT a nested `${cond ? `a` : `b`}` template). The Workflow loader's
// parser does not recurse into ${} interpolation, so a backtick nested inside one
// desyncs its tokenizer and the whole script fails to load. Keep template literals here
// to simple ${var} interpolation only.
const SHIP_DELTA_RANGE = SINCE_REF
  ? ' over range ' + SINCE_REF
  : ' (no range supplied -- use roadmap SHIPPED markers only; do NOT invent a range)'
const EXPLORERS = [
  { key: 'knowledge', label: 'explore:knowledge', brief: `Map skills/: each knowledge layer\u0027s SKILL.md + INDEX.md. COUNT the layers exactly (there are FIVE: bi-sql, bi-dax, bi-python, bi-bigdata, retail-kpi -- do not assume four) and note which are seed vs mature. Capture what each layer routes and its two-hop contract.` },
  { key: 'src', label: 'explore:src', brief: `Map src/retail/**: the rule families in rules/*.py (each @register), cli.py, runner.py, registry. Cross-check the rule count against EXPECTED_RULE_IDS in tests/unit/test_rules_wiring.py (the wiring test is the source of truth). Note the never-execute / stdlib-only discipline as you see it in code.` },
  { key: 'docs', label: 'explore:docs', brief: `Map the docs spine: COMPASS.md, AGENTS.md, docs/knowledge-map.md, docs/readiness/, docs/metrics/, docs/quality/. Capture the readiness stage model (7 stages, 4 statuses), the router, the metric-contract store, and any quality/smoke-test docs.` },
  { key: 'roadmap', label: 'explore:roadmap', brief: `Map docs/roadmap/roadmap.md as the canonical F-number ledger AND read docs/roadmap/idea-backlog.md for context. For roadmap.md, record each F-number\u0027s status using the shared enum. This subsystem owns the roadmap\u0027s own SHIPPED/DEFERRED/PARTIAL markers.` },
  { key: 'ship-delta', label: 'explore:ship-delta', brief: `Establish ship-status from REPO TRUTH ONLY: git log subjects${SHIP_DELTA_RANGE} plus the roadmap\u0027s SHIPPED markers. Do NOT read prior idea-backlog titles -- those are engine OUTPUT, not repo truth (reading them is a statefulness leak; that is cross-run memory\u0027s job, not grounding\u0027s). Your ship_status describes only \u0022what the repo contains.\u0022` },
]

const submaps = await parallel(EXPLORERS.map(e => () =>
  agent(
    `${PROJECT}

YOU ARE A SUBSYSTEM EXPLORER for Seshat BI. FIRST resolve the repo root with \`git rev-parse --show-toplevel\` (do NOT assume any machine path), then read the real repo there and map ONLY your
subsystem. Do NOT propose ideas. Do NOT execute anything (read-only). Cite a file/feature for
every capability and every ship-status row. If a path is unreadable, list it in \u0027unreadable\u0027 --
never guess.

YOUR SUBSYSTEM: ${e.brief}

Return capability_notes (each citing a file), tensions (incomplete/duplicated/awkward seams),
ship_status (feature_id + status from the shared enum + evidence_path), and unreadable[].`,
    { label: e.label, phase: 'Ground', agentType: 'Explore', schema: SUBMAP_SCHEMA, ...GATHER }
  ).then(r => r ? { ...r, _key: e.key } : null)
))

// Pure-JS merge: union notes/tensions (dedupe by exact string), collect ship-status
// by feature_id, flag contradictions, and record dead explorers. No Date/random;
// deterministic order by explorer index.
function mergeSubmaps(maps) {
  const live = maps.filter(Boolean)
  const expected = EXPLORERS.map(e => e.key)
  const got = new Set(live.map(m => m._key))
  const missing_subsystems = expected.filter(k => !got.has(k))

  const dedupe = arr => [...new Set(arr)]
  const capability_notes = dedupe(live.flatMap(m => m.capability_notes || []))
  const tensions = dedupe(live.flatMap(m => m.tensions || []))
  const unreadable = dedupe(live.flatMap(m => m.unreadable || []))

  // group ship-status rows by feature_id to surface disagreements
  const byFeature = {}
  for (const m of live) {
    for (const row of (m.ship_status || [])) {
      if (!row || !row.feature_id) continue
      ;(byFeature[row.feature_id] = byFeature[row.feature_id] || []).push({ ...row, _from: m._key })
    }
  }
  const contradictions = []
  for (const fid of Object.keys(byFeature)) {
    const statuses = new Set(byFeature[fid].map(r => r.status))
    if (statuses.size > 1) contradictions.push({ feature_id: fid, rows: byFeature[fid] })
  }
  return { capability_notes, tensions, unreadable, byFeature, contradictions, missing_subsystems }
}
const merged = mergeSubmaps(submaps)

// Reconcile-verify: one agent re-opens cited evidence, rules each contradiction by
// re-reading, downgrades any unbacked claim to UNVERIFIED, and SUBTRACTS hallucinations
// (never invents capability). It transcribes any quoted source text to ASCII.
const explore = await agent(
  `${PROJECT}

YOU ARE THE RECONCILE-VERIFIER for Seshat BI grounding. Five subsystem explorers produced
submaps; a pure-JS merge unioned them and flagged contradictions. Your job is to produce ONE
verified MERGED MAP that downstream idea generation trusts. You read the repo (read-only, no
execution) to CONFIRM claims -- you SUBTRACT hallucinations, you never invent capability.

DO:
- Write capability_map as merged PROSE by readiness stage (Source -> Mapping -> Silver -> Gold
  -> Semantic Model -> Dashboard -> Publish), the narrative substrate the lenses build on.
- For ship_status: re-open each cited evidence_path. If it backs the claim, keep the status and
  set verifier_opened_evidence true. If you cannot back it, downgrade status to UNVERIFIED.
- Rule EACH flagged contradiction by re-reading the files; record feature_id + the conflicting
  claims + your ruling (shared enum) + the winning evidence in reconciliation_ledger.
- Independently scan for the same capability appearing under two different feature_ids (a naming
  collision) and note it in verification_notes.
- Sanity-check headline counts you can verify: the knowledge-layer count (should be 5) and the
  registered-rule count vs EXPECTED_RULE_IDS in tests/unit/test_rules_wiring.py.
- Carry missing_subsystems through verbatim from the merge (a dead explorer is a signal).
- ASCII only: transcribe any quoted source text with -- and ->, never paste a Unicode glyph.
- Restate the hard PRINCIPLES an idea must respect, in your own words.

=== MERGED SUBMAPS (JSON: notes, tensions, ship-status grouped by feature, contradictions) ===
${JSON.stringify({
    capability_notes: merged.capability_notes,
    tensions: merged.tensions,
    unreadable: merged.unreadable,
    ship_status_by_feature: merged.byFeature,
    contradictions: merged.contradictions,
    missing_subsystems: merged.missing_subsystems,
  }, null, 2)}`,
  { label: 'ground:reconcile-verify', phase: 'Ground', schema: MERGED_MAP_SCHEMA, ...GATHER }
)

// If the reconcile-verifier failed (null / schema miss), do NOT continue with an empty,
// ungrounded map -- that would silently produce a normal-looking but baseless idea bank.
// Fall back to the raw merged submap FACTS (unverified, every status forced to UNVERIFIED)
// and mark the run degraded. A degraded grounding is honest; an empty one is dangerous.
const groundFailed = !explore || typeof explore !== 'object'
const explore_map = groundFailed
  ? {
      capability_map: '(reconcile-verifier did not return -- this map is the RAW union of the subsystem explorers, UNVERIFIED. Treat every claim with suspicion.)\n' + merged.capability_notes.map(n => `- ${n}`).join('\n'),
      tensions: merged.tensions,
      ship_status: Object.keys(merged.byFeature).map(fid => { const r = merged.byFeature[fid][0]; return { feature_id: fid, status: 'UNVERIFIED', evidence_path: (r && r.evidence_path) || 'unknown', verifier_opened_evidence: false } }),
      reconciliation_ledger: [],
      missing_subsystems: merged.missing_subsystems.concat(['reconcile-verify']),
      principles: [],
      verification_notes: 'DEGRADED: reconcile-verify agent returned null; downstream ran on the raw unverified submap union.',
    }
  : explore

// renderMap: turn the structured MERGED MAP back into the prose+table substrate the
// downstream stages interpolate (they used a single prose string before). Deterministic.
function renderMap(m) {
  if (!m || typeof m !== 'object') return String(m || '')
  const lines = []
  lines.push('=== CAPABILITY MAP ===', m.capability_map || '', '')
  if (Array.isArray(m.tensions) && m.tensions.length) {
    lines.push('=== TENSIONS / FRICTION ===')
    m.tensions.forEach(t => lines.push(`- ${t}`))
    lines.push('')
  }
  if (Array.isArray(m.ship_status) && m.ship_status.length) {
    lines.push('=== SHIP STATUS (feature -> status [evidence]) ===')
    m.ship_status.forEach(r => lines.push(`- ${r.feature_id}: ${r.status} [${r.evidence_path}]${r.verifier_opened_evidence ? S() : S(32,40,85,78,86,69,82,73,70,73,69,68,45,101,118,105,100,101,110,99,101,41)}`))
    lines.push('')
  }
  if (Array.isArray(m.reconciliation_ledger) && m.reconciliation_ledger.length) {
    lines.push('=== RECONCILED CONTRADICTIONS ===')
    m.reconciliation_ledger.forEach(r => lines.push(`- ${r.feature_id}: ruled ${r.ruling} (${r.winning_evidence})`))
    lines.push('')
  }
  if (Array.isArray(m.missing_subsystems) && m.missing_subsystems.length) {
    lines.push(`=== DEGRADED: missing subsystem explorers: ${m.missing_subsystems.join(S(44,32))} ===`, '')
  }
  if (Array.isArray(m.principles) && m.principles.length) {
    lines.push('=== PRINCIPLES (an idea must respect) ===')
    m.principles.forEach(p => lines.push(`- ${p}`))
    lines.push('')
  }
  if (m.verification_notes) lines.push('=== VERIFICATION NOTES ===', m.verification_notes)
  return lines.join('\n')
}
const exploreMap = renderMap(explore_map)

// ===================== 1b. MEMORY (read prior bank; do NOT re-read git) =====================
// History-aware: the engine reads its prior output + Ground's verified ship-status so it
// stops regenerating ideas that already SHIPPED and stops re-litigating settled REJECTs.
// It LABELS and de-emphasizes; it never deletes a genuinely-new idea (that carve-out lives
// in the panel). Memory consumes Ground's ship_status -- it does NOT read git itself
// (single owner of ship-status = Ground), and it never writes the roadmap (no auto-promote).
phase('Memory')
const MEMORY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['prior_ideas', 'git_corroborated', 'notes'],
  properties: {
    prior_ideas: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['prior_id', 'prior_title', 'prior_verdict', 'current_state', 'verdict_citation', 'state_citation'],
        properties: {
          prior_id: { type: 'string', description: 'the prior heading id, e.g. A1, F6' },
          prior_title: { type: 'string' },
          prior_verdict: { type: 'string', enum: ['ADOPT', 'CONSIDER', 'PARK', 'REJECT', 'UNKNOWN'] },
          current_state: { type: 'string', enum: ['shipped', 'rejected-settled', 'open'] },
          verdict_citation: { type: 'string', description: 'verbatim heading line + the section header it sits under' },
          state_citation: { type: 'string', description: 'Ground ship_status row / PR / file, or "none-found"' },
        },
      },
    },
    git_corroborated: { type: 'boolean', description: 'always false here -- Ground owns git; recorded for honesty' },
    notes: { type: 'string' },
  },
}
// Ground's verified ship-status, compacted for the memory reader (its sole state source).
const shipStatusForMemory = JSON.stringify(
  (explore_map && Array.isArray(explore_map.ship_status) ? explore_map.ship_status : [])
    .map(r => ({ feature_id: r.feature_id, status: r.status, evidence_path: r.evidence_path })),
  null, 2
)
const memory = await agent(
  `${PROJECT}

YOU ARE THE MEMORY READER for Seshat BI. You do NOT propose ideas. You read the prior idea bank
and label each prior idea with its CURRENT state, so this run does not regenerate shipped work or
re-litigate settled rejections. You are given Ground\u0027s VERIFIED ship-status table -- that is your
authoritative source for what shipped. Do NOT re-read git (Ground owns that).

STEPS:
1. Resolve the repo root with \`git rev-parse --show-toplevel\` (do NOT assume any machine path), then read the prior bank at <repo-root>/docs/roadmap/idea-backlog.md from disk. If it does not exist or
   has no idea headings, return prior_ideas: [] and say so in notes (a first run is normal).
2. Parse each idea heading (e.g. \u0022### A1. Machine-Checkable Route Registry\u0022). For EACH: capture
   prior_id, prior_title, the verdict SECTION it sits under (## ADOPT/CONSIDER/PARK/REJECT) as
   prior_verdict, and -- as verdict_citation -- the VERBATIM heading line plus the verbatim section
   header, so any misparse is a quotable artifact a human can catch.
2b. ALSO parse the \u0022## SHIPPED / SETTLED (prior ideas, for the record)\u0022 appendix if present: its
   entries are BULLETS, not headings, of the form \u0022- **<id> <title>** -- SHIPPED. <citation>\u0022 or
   \u0022-- SETTLED (rejected). <citation>\u0022. For each bullet, emit a prior_ideas entry with prior_id,
   prior_title, prior_verdict (ADOPT/REJECT/UNKNOWN as best inferred from the tag), current_state
   (\u0022shipped\u0022 for SHIPPED, \u0022rejected-settled\u0022 for SETTLED), verdict_citation = the verbatim bullet,
   and state_citation = the bullet\u0027s trailing citation. This is the round-trip: closed ideas live
   in that appendix as bullets, so they MUST be re-read here or they vanish from memory next run.
2c. ALSO read the structured ledger at <repo-root>/docs/roadmap/shipped-ideas.yaml if present (IL1).
   It is a YAML mapping of idea-id to { status: shipped|settled, pr_sha: evidence, f_row: label-or-none }.
   ABSENT or EMPTY file: skip this step (not an error; the prose appendix + ship_status still apply).
   PRESENT but MALFORMED (invalid YAML, an entry missing a required key, or a status other than
   shipped/settled): STOP and report a clear error in notes -- do NOT silently proceed as if no
   history existed. For each well-formed entry emit or merge a prior_ideas entry: prior_id = the key,
   current_state = \u0022shipped\u0022 for status shipped or \u0022rejected-settled\u0022 for status settled, and
   state_citation built from pr_sha (append the f_row when it is not \u0022none\u0022). This ledger is
   HUMAN-CURATED known-history, NOT a git read -- you still never re-read git (Ground owns that).
   It is AUTHORITATIVE on conflict: if the ledger and the prose appendix disagree on an idea-id
   state, use the LEDGER value and record the disagreement in notes as a memory-integrity signal;
   never silently rewrite either source. The ledger is read-only evidence: never write it, and
   never treat an f_row value as permission to place anything on the roadmap (a human places F-rows).
3. Set current_state by matching the idea against Ground\u0027s ship_status:
   - \u0022shipped\u0022 ONLY if a ship_status row marks an equivalent capability SHIPPED -- cite that row
     (feature_id + evidence_path) in state_citation.
   - \u0022rejected-settled\u0022 if the prior verdict was REJECT/INELIGIBLE and nothing changed -- cite the
     prior rationale line.
   - \u0022open\u0022 otherwise. If you cannot back a shipped/settled claim with a citation, it is \u0022open\u0022.
4. NEVER guess that something shipped. No citation -> open. git_corroborated is always false
   (Ground owns git). You never execute anything and you never write the roadmap.

=== GROUND VERIFIED SHIP-STATUS (your only state source) ===
${shipStatusForMemory}`,
  { label: 'memory:read-prior', phase: 'Memory', schema: MEMORY_SCHEMA, ...GATHER }
)

// Rendered ledger injected into the generation + review prompts. Lists shipped + settled
// so lenses don't re-propose them as new (but MAY extend, if materially different).
function renderMemoryLine(mem) {
  const prior = (mem && Array.isArray(mem.prior_ideas)) ? mem.prior_ideas : []
  const shipped = prior.filter(p => p.current_state === 'shipped')
  const settled = prior.filter(p => p.current_state === 'rejected-settled')
  if (!shipped.length && !settled.length) return ''  // first run / nothing to remember
  const fmt = arr => arr.map(p => `${p.prior_id} ${p.prior_title}`).join('; ')
  const parts = ['\n=== KNOWN HISTORY (do NOT re-propose as new) ===']
  if (shipped.length) parts.push(`ALREADY SHIPPED (cite + extend only if materially different): ${fmt(shipped)}.`)
  if (settled.length) parts.push(`REJECTED-as-settled (do not re-litigate unless materially new -- and say how it differs): ${fmt(settled)}.`)
  parts.push('You MAY propose in the same area ONLY IF materially different (new mechanism/seam/value), and you MUST state how it differs. Do not pad the list by restating shipped work.')
  return parts.join('\n')
}
const MEMORY_LINE = renderMemoryLine(memory)
// A dead memory:read-prior agent (null/schema miss) makes renderMemoryLine return "" --
// indistinguishable from a genuine first run, silently re-allowing shipped/settled ideas
// to be re-proposed with no DEGRADED flag. Symmetric to groundFailed: a failed memory read
// is an HONEST degraded run, not an invisible "no history". (Folded into run_health below.)
const memoryFailed = !memory || typeof memory !== 'object'

// ===================== 1c. INTERPRET (expand + review the USER'S own ideas) =====================
// Runs ONLY when the user supplied idea(s) (args.ideas / args.seed / a bare string). It grows
// each rough/half-formed idea into ONE fully-shaped idea (the strongest reading) and records the
// reading it chose + the readings it rejected -- so a misread is visible, not a silent failure.
// The expanded ideas are injected into the candidate pool tagged origin:user; they then flow
// through cross-pollinate/synthesize/verify/panel like any idea and are gated identically (a user
// idea can be ruled INELIGIBLE/REJECT -- the interpreter never approves or bypasses a gate). When
// no user ideas are supplied this whole block is skipped and the workflow behaves exactly as before.
let interpreted = null
let userIdeas = []            // shaped ideas, origin:user, injected into the pool
let userNotesByTitle = {}     // title -> { original_words, chosen_reading, rejected_readings } for render
// De-nested numbered list of the user's raw ideas (a backtick nested inside ${...} desyncs the
// Workflow loader; build the string with plain concatenation outside the template -- see the
// loader-trap note above). Empty string when no user ideas (the block below is skipped anyway).
const USER_IDEAS_NUMBERED = HAS_USER_IDEAS
  ? USER_IDEAS.map((s, i) => (i + 1) + '. ' + s).join('\n')
  : ''
if (HAS_USER_IDEAS) {
  phase('Interpret')
  interpreted = await agent(
    `${PROJECT}

YOU ARE THE IDEA INTERPRETER for Seshat BI. A human handed you their OWN idea(s) -- often rough,
half-formed, or hard to put into words. Your job is to GROW each into ONE fully-shaped, reviewable
idea, choosing the STRONGEST reading, and to make your interpretation VISIBLE so the human can catch
a misread. You are generous and imaginative in expansion, but HONEST: you never inflate a weak idea,
and you never quietly turn it into a different idea than they meant.

FOR EACH user idea below, return one expanded entry with:
- original_words: their raw words, VERBATIM (the accountability anchor).
- chosen_reading: one sentence -- how you read those words to shape the idea.
- rejected_readings: other plausible ways to read the same words that you did NOT pick (so they can
  tell you if you misread them). If the words were unambiguous, say so with a single-item list.
- title / pitch / horizon / why_it_fits / rough_shape (the seam it touches, not full impl).
- strengthens_layer + serves (judge honestly, same meanings as the generation lenses).
- eligible_guess: your honest first guess whether it respects the hard principles (the review panel
  rules for real -- do not soften a genuine violation; if their idea would need an executor, bypass a
  gate, invent a metric, or fabricate confidence, say eligible_guess false and shape the closest
  eligible variant you can while keeping their intent).

Do NOT generate any ideas of your own beyond expanding theirs. Do NOT merge two of their ideas into
one. One expanded entry per user idea (you MAY note in why_it_fits if two of theirs overlap).

=== THE USER'S RAW IDEA(S) ===
${USER_IDEAS_NUMBERED}
${MEMORY_LINE}

=== REPO MAP ===
${exploreMap}`,
    { label: 'interpret:user-ideas', phase: 'Interpret', schema: INTERPRET_SCHEMA, ...CREATE }
  )
  const expanded = (interpreted && Array.isArray(interpreted.expanded)) ? interpreted.expanded : []
  userIdeas = expanded.map(e => ({
    title: e.title, pitch: e.pitch, horizon: e.horizon, why_it_fits: e.why_it_fits,
    rough_shape: e.rough_shape, strengthens_layer: e.strengthens_layer || 'none',
    serves: e.serves || 'end_user', source_lens: 'user', origin: 'user',
  }))
  for (const e of expanded) userNotesByTitle[e.title] = {
    original_words: e.original_words || '', chosen_reading: e.chosen_reading || '',
    rejected_readings: Array.isArray(e.rejected_readings) ? e.rejected_readings : [],
    eligible_guess: e.eligible_guess,
  }
}
// A supplied-but-failed interpretation is a degraded run, not a silent no-op: the user asked for
// their idea to be reviewed and it never entered the pool. Surfaced in run_health below.
const interpretFailed = HAS_USER_IDEAS && (!interpreted || !userIdeas.length)
// PARTIAL-expansion detection (Codex P2): a count check (userIdeas.length < USER_IDEAS.length)
// is not enough -- two expansions of seed A + zero of seed B still totals the input count and
// would slip through. The interpreter copies each seed VERBATIM into original_words, so we check
// COVERAGE: every supplied seed must be echoed by some expansion's original_words (matched on
// proseKey, or a normalized-substring either direction for a lightly-reworded anchor). Any seed
// with no covering expansion was silently dropped -- named in a loud banner (run_health below).
const _expandedAnchors = (interpreted && Array.isArray(interpreted.expanded) ? interpreted.expanded : [])
  .map(e => proseKey(e && e.original_words)).filter(Boolean)
const uncoveredSeeds = HAS_USER_IDEAS
  ? USER_IDEAS.filter(seed => {
      const k = proseKey(seed)
      if (!k) return false
      return !_expandedAnchors.some(a => a === k || a.includes(k) || k.includes(a))
    })
  : []
// True when SOME (but not necessarily all) seeds were dropped, even though the run produced ideas.
const interpretPartial = HAS_USER_IDEAS && !interpretFailed && uncoveredSeeds.length > 0
// Rendered into the generation prompts so the lenses SEE the user's ideas and can build on them
// (cross-pollination), without re-proposing them as their own.
// De-nested (no backtick inside ${...}): build the bullet list with plain concatenation first.
const USER_IDEAS_BULLETS = userIdeas.map(i => '- ' + i.title + ': ' + i.pitch).join('\n')
const USER_IDEAS_LINE = userIdeas.length
  ? '\n=== THE USER OWN IDEAS (already in the candidate pool; you MAY build on/extend them as cross-disciplinary ideas, but do NOT restate them as your own) ===\n' + USER_IDEAS_BULLETS + '\n'
  : ''

// ===================== 2. GENERATE (round 1) =====================
phase('Generate')
const LENSES = [
  { key: 'creative', label: 'gen:creative', role: `a CREATIVE PROGRAMMER lens. Generate inventive, original ideas -- features, agent capabilities, DX wins, novel uses of the knowledge layers, surprising combinations. Favor imagination and delight.` },
  { key: 'bi',       label: 'gen:bi-analyst', role: `a PROFESSIONAL BI ANALYST lens (15+ yrs retail). Generate ideas that increase ANALYTICAL VALUE -- KPI/metric coverage, decision-support, forecasting, anomaly/exception surfacing, business-question coverage, things a real merchandiser/finance owner needs.` },
  { key: 'technical',label: 'gen:technical', role: `a PROFESSIONAL TECHNICAL ARCHITECT lens. Generate ideas that strengthen the system -- architecture, testing/CI gates, performance, the router/two-hop contract, knowledge-layer tooling, drift/reconciliation, adapter design, observability, agent-eval harnesses. Buildable in-repo. COUNTERWEIGHT (important): this kit already OVER-PRODUCES tool-internal bookkeeping (route/rule-count/stale-marker reconcilers, wiring meta-gates, self-audits). Do NOT pad the bank with another self-check unless it clearly unblocks user-facing value. Prefer ideas whose beneficiary is the end BI user or the operator; when you do propose a tool-internal idea, justify why it is worth the added ceremony. Set serves honestly (mostly tool_internal for this lens -- do not mislabel bookkeeping as end_user).` },
  { key: 'design',   label: 'gen:design', role: `a PROFESSIONAL BI DASHBOARD DESIGNER lens (data-viz + design-systems background). Generate ideas that strengthen the PRESENTATION FOUNDATION as a GOVERNED, principle-safe layer -- theme-token contracts, background/canvas asset conventions, layout blueprints, accessibility/contrast checkers, colour + sentiment-colour governance, visual-hierarchy linters, design-review evidence records, screenshot-QA harnesses, mobile-layout conventions. Reason WITH the powerbi-dashboard-design skill's four surfaces (report visuals / external background / theme JSON / handoff) and its discipline: DEFINE and CHECK the design foundation, NEVER author a PBIP/PBIR, NEVER generate DAX, NEVER invent a metric, NEVER bake a KPI value into a background or business meaning into a theme. Design ideas must be static/read-only reasoning plus authoring-of-conventions, buildable in-repo today (report execution/authoring is deferred F016 -- do not propose it). Set strengthens_layer to design-system for these.` },
  { key: 'consumer', label: 'gen:consumer', role: `a BUSINESS DECISION-MAKER / DASHBOARD CONSUMER lens (a store/finance/merchandising owner who READS dashboards to decide, and is NOT technical). You are NOT the BI analyst -- you do not build, explore, or model. You want ONE thing: to get a clear, trustworthy ANSWER to a real business question with the least friction ("can I even answer 'why did margin drop in the north region?' with what this kit produces, and can I trust it?"). Generate ideas that increase ANSWERABILITY and CLARITY for a non-technical reader -- decision-question coverage, plain-language readiness/handoff summaries, "which visual answers which question" maps, trust/provenance signals a business owner can read, exception/what-changed alerts phrased for a decision-maker. Distinguish yourself HARD from the analyst lens: if an idea helps someone BUILD or EXPLORE, it is not yours; yours helps someone DECIDE. Respect every hard principle (no executor, no invented metric, no fabricated confidence). Set serves to end_user for these.` },
  { key: 'operator', label: 'gen:operator', role: `a NEWCOMER / OPERATOR lens (someone who just inherited this kit and must run it cold, without the author's head-knowledge of F-numbers, the 7 stages, the router, or the 40+ rules). Generate ideas that lower the RAMP and reduce what a person must memorize before they are productive -- onboarding/first-hour flows, legible "where am I / what is the one next action" surfaces, self-explaining errors and gate failures, discoverability of the right skill/verb, cold-start worked-example runs, reducing the cognitive load of the readiness spine. Reinforce (do not duplicate) the existing first-hour-compass. This is an ADOPTION/HANDOFF lens: ask "could a stranger use this without me?" Respect every hard principle. serves is typically operator; use end_user only if the ramp win is genuinely for the business reader.` },
]
function genPrompt(role, extra='') {
  return `You are ${role}\nGenerate 6-8 ideas for Seshat BI. Each MUST respect the hard principles (no executor, no gate bypass, generic-only, no fabricated confidence). Mix NOW and HORIZON. For each idea set strengthens_layer to the ONE knowledge layer it most strengthens (bi-sql / bi-dax / bi-python / bi-bigdata / retail-kpi / docs-spine / design-system), or \u0027none\u0027 if it strengthens the engine/CLI/gates rather than a knowledge layer -- judge honestly, do not force a layer (design-system = the Power BI presentation FOUNDATION: theme tokens, background/canvas conventions, layout blueprints, accessibility, design-review evidence -- governance, never report authoring). ALSO set serves to WHO the idea ultimately benefits, judged honestly (do NOT mislabel to look good): end_user (a business reader/analyst gains analytical value or a clearer answer), operator (someone running/adopting the kit gains a lower ramp / less to memorize), or tool_internal (the kit checks or maintains ITSELF -- reconcilers, self-audits, wiring gates, rule-count/route/stale-marker checks). tool_internal is legitimate but this kit already OVER-PRODUCES it, so only propose one when it clearly unblocks user-facing value. ${extra}${MEMORY_LINE}${USER_IDEAS_LINE}\n\n=== REPO MAP ===\n${exploreMap}`
}
// classify a lens result: 'failed' = agent returned null (schema/death), 'empty' =
// a valid response with no ideas, 'ok' = real ideas. This separates a FAILURE from a
// lens that legitimately had nothing -- they used to both vanish via .filter(Boolean).
// (Honest scope: we cannot know WHY a null came back, only that one did -> 'failed'.)
function classify(r, key) {
  if (!r) return { _key: key, _status: 'failed', ideas: [] }
  const ideas = Array.isArray(r.ideas) ? r.ideas : []
  return { ...r, _key: key, _status: ideas.length ? 'ok' : 'empty' }
}
const round1 = await parallel(LENSES.map(l => () =>
  agent(genPrompt(l.role), { label: `${l.label}:r1`, phase: 'Generate', schema: IDEA_SCHEMA, ...CREATE })
    .then(r => classify(r, l.key))
))

// ===================== 3. CROSS-POLLINATE =====================
phase('Cross-pollinate')
const round1Json = JSON.stringify(round1.filter(r => r._status === 'ok').map(r => ({ lens: r.lens || r._key, ideas: r.ideas })), null, 2)
const crossRound = await parallel(LENSES.map(l => () =>
  agent(
    genPrompt(l.role,
      `You have now SEEN what the other lenses proposed (below). React to them: combine a strong idea from another lens with your own perspective, fill a gap they left, or push a half-idea further. Generate 3-5 NEW cross-disciplinary ideas (do NOT repeat ideas already listed). The best ideas live at the seams between disciplines.\n\n=== ALL ROUND-1 IDEAS ===\n${round1Json}`),
    { label: `${l.label}:cross`, phase: 'Cross-pollinate', schema: IDEA_SCHEMA, ...GATHER }
  ).then(r => classify(r, l.key))
))

// ===================== 4. COMPLETENESS CRITIC -> targeted pass =====================
phase('Completeness')
const sofar = [...round1, ...crossRound].filter(r => r._status === 'ok')
const sofarJson = JSON.stringify(sofar.map(r => ({ lens: r.lens || r._key, ideas: (r.ideas||[]).map(i => i.title) })), null, 2)
const gaps = await agent(
  `You are a COMPLETENESS CRITIC. Below are all idea TITLES generated so far for Seshat BI, plus the repo map. Your job is to find what\u0027s MISSING -- readiness stages with few ideas, repo gaps/tensions nobody addressed, idea TYPES underrepresented (e.g. all features and no DX, or all technical and no business value), and obvious adjacent ideas no lens reached. List 5-10 specific missing angles as short prompts (\u0022nobody proposed anything for X / for the Y gap\u0022). Do not generate full ideas -- just name the blind spots precisely.\n\n=== REPO MAP ===\n${exploreMap}\n\n=== IDEA TITLES SO FAR ===\n${sofarJson}`,
  { label: 'critic:gaps', phase: 'Completeness', ...CREATE }
)
// one targeted fill pass aimed at the named gaps
const fillRound = await parallel(LENSES.map(l => () =>
  agent(genPrompt(l.role,
    `A completeness critic identified these BLIND SPOTS in the ideas generated so far. From YOUR lens, generate 2-4 ideas that specifically fill the gaps most relevant to you (do not repeat existing ideas).\n\n=== BLIND SPOTS ===\n${gaps}`),
    { label: `${l.label}:fill`, phase: 'Completeness', schema: IDEA_SCHEMA, ...CREATE }
  ).then(r => classify(r, l.key))
))

// The user's expanded ideas lead the pool (origin:user) so they are visible to the synthesizer
// FIRST; every lens-generated idea is tagged origin:engine. Both flow through the same gate.
const engineIdeas = [...round1, ...crossRound, ...fillRound].filter(r => r._status === 'ok').flatMap(r =>
  (r.ideas || []).map(i => ({ ...i, source_lens: r.lens || r._key, origin: 'engine' }))
)
const allIdeas = [...userIdeas, ...engineIdeas]

// ---- run health (census): expected vs survived lens headcount per round, with a
// fail-loud DEGRADED banner. A dead/empty lens used to vanish silently. ----
function census(label, expected, arr) {
  const failed = arr.filter(r => r._status === 'failed').length
  const empty = arr.filter(r => r._status === 'empty').length
  const ok = arr.filter(r => r._status === 'ok').length
  return { label, expected, ok, empty, failed }
}
// Built now over the generation rounds; the REVIEW PANEL census is folded in after the
// panel runs (a failed reviewer is also a degraded run -- see the panel-failure fold below).
const run_health = (() => {
  const rounds = [
    census('generate', LENSES.length, round1),
    census('cross-pollinate', LENSES.length, crossRound),
    census('fill', LENSES.length, fillRound),
  ]
  const anyFailed = rounds.some(r => r.failed > 0)
  const anyShort = rounds.some(r => r.ok < r.expected)
  const degraded = anyFailed || anyShort || groundFailed || memoryFailed || interpretFailed || interpretPartial
  const parts = rounds.filter(r => r.ok < r.expected).map(r => {
    const failedSuffix = r.failed ? ' (' + r.failed + ' failed)' : ''   // de-nested: no `` inside ${}
    return `${r.label} ${r.ok}/${r.expected} lenses ok${failedSuffix}`
  })
  // interpretFailed is a HARD failure for this run's purpose: the user asked for their idea to be
  // reviewed and it never entered the pool. Announce it loud, not silent (symmetric to groundFailed).
  if (interpretFailed) parts.unshift('interpret:user-ideas returned null/empty -- YOUR supplied idea(s) were NOT expanded or reviewed this run; re-run with a few more words')
  // interpretPartial: SOME seeds expanded, others silently dropped. Name the uncovered ones so the
  // user knows which of THEIR ideas was not reviewed (a count check alone would miss this).
  else if (interpretPartial) parts.unshift('interpret:user-ideas expanded only SOME of your ideas -- these were NOT reviewed this run: ' + uncoveredSeeds.join(S(59,32)) + ' (re-run them with more distinctive wording)')
  if (groundFailed) parts.unshift('grounding reconcile-verify returned null -- the repo map is the RAW UNVERIFIED submap union')
  if (memoryFailed) parts.unshift('memory:read-prior returned null -- prior shipped/settled ideas are UNKNOWN this run; lenses may re-propose closed work')
  const banner = degraded ? `DEGRADED RUN: ${parts.join(S(59,32))}. Treat this bank as partial.` : ''
  return { rounds, degraded, banner }
})()

// ===================== 5. SYNTHESIZE =====================
phase('Synthesize')
const synthesis = await agent(
  `You are the SYNTHESIZER. Many ideas were generated across six lenses over three rounds
(initial, cross-pollination, gap-fill). Merge into ONE clean candidate set.
- DEDUPE near-duplicates (keep the strongest framing; note where lenses/rounds converged -- convergence is a strength signal).
- GROUP into themes.
- Keep each idea\u0027s title, pitch, horizon, why_it_fits, rough_shape, strengthens_layer, serves, origin, source_lens(es).
- USER IDEAS ARE PROTECTED: any idea with origin "user" is the human OWN idea. NEVER merge it away,
  drop it, or rename it into a machine idea. Keep every origin:user idea as its OWN distinct row with
  its origin:user tag preserved. If a machine idea converges with a user idea, NOTE the convergence on
  the USER idea (a strength signal) rather than absorbing the user idea into the machine one. The user
  must be able to find their own idea in the output -- losing it is a failure.
- Do NOT score (the reviewer does). Do NOT invent new ideas; only merge/clarify.
- Flag any idea that might violate a hard principle (the reviewer rules).
- If a candidate matches a prior idea KNOWN to have SHIPPED (see history below), KEEP it but
  tag it \u0022prior_state: shipped\u0022 with the citation -- do NOT drop it (a materially-new variant
  and the convergence signal both matter). Dropping would hide a genuine extension.
${MEMORY_LINE}

=== REPO MAP ===\n${exploreMap}\n\n=== ALL RAW IDEAS (JSON) ===\n${JSON.stringify(allIdeas, null, 2)}

Output a clean candidate list grouped by theme, each idea with its fields (INCLUDING its origin tag --
user or engine) + source lens(es) + a convergence note where applicable. Every origin:user idea must
still be present and clearly marked as the user's own.`,
  { label: 'synthesize:merge', phase: 'Synthesize', ...JUDGE }
)

// ===================== 6. ADVERSARIAL VERIFY (universal coverage) =====================
phase('Verify')
// Every idea is challenged -- no "only the tempting ones" escape hatch. Default
// disposition is refuted; an idea earns 'survived' only if its hardest objection fails.
const verify = await agent(
  `You are an ADVERSARIAL SKEPTIC. For EVERY idea in the synthesized candidate set below you MUST
attempt a refutation -- there is no \u0022skip the ones that look fine.\u0022 The default disposition of
every idea is that it does NOT survive; an idea earns \u0027survived\u0027 only if your hardest objection
provably fails. Killing nothing is a RED FLAG that you did not really try.

For EACH idea, find the strongest objection: does it secretly violate a hard principle? does it
duplicate a feature the ship-status says is already SHIPPED? is the \u0022feasible\u0022 framing hiding a
missing dependency (a gold source, a runtime consumer, a human ruling)? would it quietly turn a
reasoning layer into an executor or a stats engine? Then rule it survived / weakened / killed
with one line of why.

=== SHIP STATUS (for the duplicate-of-shipped check) ===\n${JSON.stringify((explore_map && explore_map.ship_status) || [], null, 2)}
=== SYNTHESIZED CANDIDATES ===\n${synthesis}`,
  { label: 'verify:skeptic', phase: 'Verify', schema: VERIFY_SCHEMA, ...JUDGE }
)

// ===================== 7. PANEL REVIEW (3 independent standpoints) =====================
// Three reviewers judge the SAME set from distinct standpoints, in a parallel barrier
// that collects exactly 3 records (zero-arg thunks closing over the reviewer -- no index).
// A single reviewer was one point of judgment; the panel surfaces eligibility disagreement.
phase('Panel-review')
const PANELISTS = [
  { key: 'principle-auditor', label: 'review:principle-auditor', standpoint:
    `the HARD-PRINCIPLE AUDITOR. Judge ELIGIBILITY only and presume an idea INELIGIBLE until it proves it touches ONLY reasoning/static/read-only seams. Name the violated principle for anything that executes, bypasses a gate, fabricates confidence, self-grants approval, or is C086-specific. Be the strictest of the three.` },
  { key: 'shipped-duplication-auditor', label: 'review:shipped-duplication-auditor', standpoint:
    `the SHIPPED-DUPLICATION AUDITOR. Judge CONSISTENCY with shipped work using the ship-status table + history. PENALIZE an idea that merely RESTATES shipped work; do NOT penalize a genuine extension that builds ON shipped work -- but it must name the shipped feature and say which it is. An idea matching settled-rejected history should not be ADOPT unless it is materially new.` },
  { key: 'value-feasibility-realist', label: 'review:value-feasibility-realist', standpoint:
    `the VALUE/FEASIBILITY REALIST. Judge value and feasibility honestly: is \u0022feasible\u0022 hiding a missing gold source, a runtime consumer that does not exist yet, or an unmade human ruling? Reward genuine analytical/system value; discount ideas whose feasibility depends on something deferred (e.g. F016).` },
  { key: 'design-foundation-reviewer', label: 'review:design-foundation-reviewer', standpoint:
    `the DESIGN-FOUNDATION REVIEWER. Judge design/presentation ideas on real design value (visual hierarchy, accessibility, theme consistency, layout reuse, design-review rigour) AND on eligibility within the four-surface discipline: an idea that authors a PBIP/PBIR, generates DAX, invents a metric, or bakes data into a static background/theme is INELIGIBLE (surface-blending or F016 execution). Reward governance/linting/evidence seams that make the design layer checkable; discount purely cosmetic ideas with no durable seam. For non-design ideas outside your expertise, defer (score conservatively, flag low confidence) rather than distort the panel.` },
]
// NOTE: two statements, NOT `const panel = (await parallel(...)).filter(Boolean)`. The
// Workflow loader's parser cannot match a `(`-wrapped multi-line expression whose closing
// `)` is followed by a `.method()` (e.g. `).filter(Boolean)`); it desyncs and the whole
// script fails to load (node --check passes -- the loader is stricter). Splitting the
// wrapper into a plain `await` assignment + a separate `.filter` line avoids the trigger.
const panelRaw = await parallel(PANELISTS.map(p => () =>
  agent(
    `You are ${p.standpoint}

You are ONE of four independent reviewers scoring the SAME synthesized idea set for Seshat BI.
Score from YOUR standpoint; the other three cover the other angles. Default to caution. This is a
triage opinion for an IDEA BANK, never a build decision -- you never promote anything to the roadmap.

For EACH idea set: horizon (NOW/HORIZON); eligible (bool) + ineligibility_reason (named principle
or \u0027\u0027); consistency (consistent/minor-tension/conflict); value_score & feasibility_score (1-10);
verdict (ADOPT/CONSIDER/PARK/REJECT/SHIPPED -- use SHIPPED only if it matches a shipped feature);
survived_verification (survived/weakened/killed, weighed from the skeptic); prior_status
(new/shipped/rejected-settled/open-prior from the history); relitigation (n/a/settled/materially-new);
rationale; first_step for ADOPT/CONSIDER. An idea the skeptic KILLED should not be ADOPT.
CARRY the origin tag (user/engine) UNCHANGED onto every scored idea -- it is not yours to re-decide.
Score an origin:user idea (the human's own) by the SAME standard as any other -- neither inflate it
to flatter the human nor dismiss it for being rough; it was already expanded into a fair form. If a
user idea is genuinely ineligible or weak, say so plainly (that honest verdict IS the review they
asked for), and the steelman stage will look for a narrower eligible seam.

=== SHIP STATUS ===\n${JSON.stringify((explore_map && explore_map.ship_status) || [], null, 2)}${MEMORY_LINE}
=== SYNTHESIZED CANDIDATES ===\n${synthesis}
=== ADVERSARIAL SKEPTIC\u0027S CHALLENGES ===\n${verify ? JSON.stringify(verify) : S(40,115,107,101,112,116,105,99,32,112,114,111,100,117,99,101,100,32,110,111,116,104,105,110,103,41)}`,
    { label: p.label, phase: 'Panel-review', schema: PANEL_REVIEWER_SCHEMA, ...JUDGE }
  ).then(r => r ? { ...r, _key: p.key } : null)
))
const panel = panelRaw.filter(Boolean)

// ===================== 8. AGGREGATE (pure JS gate + clamp; tiny prose agent) =====================
// The arithmetic, the eligibility gate, and the demote-only clamp are PURE JS -- never an
// LLM sampling pass (an LLM cannot miscompute a median or call a 2-1 split a "majority").
// The clamp only DEMOTES toward caution, so it is orchestration, not self-approval.
phase('Aggregate')
const aggregated = aggregatePanel(panel, PANELISTS.length, verify)   // verify threaded for the skeptic-coverage clamp

// Fold the review-panel census into run_health: a dead reviewer (esp. the principle
// auditor) is a degraded run, even if every generation lens reported. This makes a
// short panel fail loud in the banner, not just silently downgrade per-idea gates.
if (aggregated.panel_failed > 0) {
  const note = `review panel ${aggregated.reviewers_seen}/${aggregated.reviewers_expected} reviewers ok (${aggregated.panel_failed} failed) -- eligibility rulings are incomplete; affected ideas downgraded to needs-review`
  run_health.degraded = true
  run_health.banner = run_health.banner
    ? `${run_health.banner} Also: ${note}.`
    : `DEGRADED RUN: ${note}. Treat this bank as partial.`
  run_health.rounds.push({ label: 'panel-review', expected: aggregated.reviewers_expected, ok: aggregated.reviewers_seen, empty: 0, failed: aggregated.panel_failed })
}
// Skeptic-coverage gap: ideas the adversarial skeptic never challenged were JS-clamped
// (killed + demoted out of ADOPT); announce it loud rather than only clamping silently.
if (aggregated.uncovered_by_skeptic > 0) {
  const note = `adversarial skeptic did not challenge ${aggregated.uncovered_by_skeptic} candidate(s) -- those were clamped (killed, demoted from ADOPT) for unproven coverage`
  run_health.degraded = true
  run_health.banner = run_health.banner ? `${run_health.banner} Also: ${note}.` : `DEGRADED RUN: ${note}. Treat this bank as partial.`
}
// USER-IDEA SURVIVAL GUARD (the feature's core promise, enforced in JS -- not left to prose).
// The synthesizer is schema-less and told to merge; the panel echoes origin. If either drops or
// reworded a user idea, it would silently vanish from the "Your Ideas" lane -- the one outcome
// this feature exists to prevent. We hold the ground truth (userIdeas), so we enforce with it:
//   - lostUserIdeas: any user title with NO normalized match among the aggregated titles was
//     dropped/reworded by synthesis. A re-assert cannot recover a row that no longer exists, so
//     this is announced LOUD (same idiom as uncovered_by_skeptic / panel_failed).
//   - userKeySet: the normalized keys we DO force back to origin:user at render (fix #1 below),
//     so a mislabel (origin flipped to 'engine' by an LLM hop) cannot empty the lane.
const userKeySet = new Set(userIdeas.map(u => proseKey(u.title)))
const aggregatedKeySet = new Set(aggregated.ideas.map(i => proseKey(i.title)))
const lostUserIdeas = userIdeas.filter(u => !aggregatedKeySet.has(proseKey(u.title))).map(u => u.title)
if (lostUserIdeas.length) {
  const note = `YOUR idea(s) may have been merged or renamed away by synthesis and could not be matched back: ${lostUserIdeas.join(S(59,32))} -- check the bank body; re-run with more distinctive wording if they are missing`
  run_health.degraded = true
  run_health.banner = run_health.banner ? `${run_health.banner} Also: ${note}.` : `DEGRADED RUN: ${note}. Treat this bank as partial.`
}

// One tiny agent writes ONLY the dissent prose + portfolio summary; it touches no number.
// It is a NON-CRITICAL prose step -- the verdicts/scores are already final in JS -- so a null
// return (schema miss / agent failure) must NOT abort the run after the panel succeeded. We
// coalesce null to a safe default (matching the defensive null-handling on the lens/panel
// agents) so the deterministic renderer still emits the aggregated scores.
const FALLBACK_DISSENT = { dissent_by_title: [], portfolio_summary: aggregated.ideas.length ? '(panel summary unavailable -- the dissent clerk did not return; verdicts and scores below are final.)' : 'No ideas reached the panel.' }
const dissentRaw = aggregated.ideas.length ? await agent(
  `You are the PANEL CLERK. Write human-facing PROSE only -- you change NO scores and NO verdicts
(those are already computed). (1) For each idea flagged with a panel split below, write a one- to
two-sentence \u0027dissent\u0027 explaining the disagreement (e.g. \u00222 reviewers ADOPT; the principle auditor
ruled it ineligible for X\u0022). (2) Write a \u0027portfolio_summary\u0027: a scannable paragraph a human can act
on. Return dissent keyed by idea title, plus the summary. Do not invent ideas or numbers.

=== AGGREGATED IDEAS (verdicts/scores already final; splits flagged) ===
${JSON.stringify(aggregated.ideas.map(i => ({ title: i.title, verdict: i.verdict, eligibility_gate: i.eligibility_gate, value_score: i.value_score, feasibility_score: i.feasibility_score, score_spread: i.score_spread, per_reviewer: i._per_reviewer })), null, 2)}`,
  { label: 'aggregate:dissent-prose', phase: 'Aggregate', schema: DISSENT_SCHEMA, ...GATHER }
) : null
const dissentAgent = dissentRaw || FALLBACK_DISSENT

// Stitch the JS-computed ideas + the agent prose into the review-shaped object the
// deterministic renderer (PR2) already consumes. scored_ideas keeps the same field
// names the renderer reads (title/horizon/eligible/consistency/value_score/
// feasibility_score/verdict/rationale/first_step) PLUS dissent.
const dissentMap = {}
for (const d of (dissentAgent.dissent_by_title || [])) dissentMap[d.title] = d.dissent
const review = {
  summary: dissentAgent.portfolio_summary || '',
  scored_ideas: aggregated.ideas.map(i => ({
    title: i.title,
    horizon: i.horizon,
    eligible: i.eligibility_gate === 'pass',   // ONLY a full clean pass reads as eligible
    eligibility_gate: i.eligibility_gate,      // pass | fail | split -- renderer shows all three
    consistency: i.consistency,
    value_score: i.value_score,
    feasibility_score: i.feasibility_score,
    verdict: i.verdict,
    rationale: i.rationale,
    survived_verification: i.survived_verification,
    first_step: i.first_step,
    strengthens_layer: i.strengthens_layer,
    serves: i.serves,
    // Re-assert origin from JS ground truth: if this title matches a known user idea, it IS
    // origin:user regardless of what the two LLM hops (synthesizer, panel) echoed. A flipped tag
    // cannot empty the "Your Ideas" lane (the filter is i.origin === 'user').
    origin: userKeySet.has(proseKey(i.title)) ? 'user' : (i.origin || 'engine'),
    dissent: dissentMap[i.title] || '',
  })),
}

// ===================== 8b. RESCUE (steelman the rejected) =====================
// One agent reads ONLY the PARK/REJECT/ineligible ideas and attempts a good-faith
// rescue REASON -- a reframing or seam-narrowing that MIGHT make an idea eligible, or
// a clear "no rescue exists" with the irreducible blocker. It NEVER re-scores: the
// schema has no verdict/eligible field, so it cannot launder an idea back past the gate
// (the gate already ran). Zero cost on a clean run: skipped entirely if nothing rejected.
phase('Rescue')
const rejected = review.scored_ideas.filter(i =>
  i.verdict === 'PARK' || i.verdict === 'REJECT' || i.eligible === false)
const RESCUE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['rescues'],
  properties: {
    rescues: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        // NO verdict / eligible field by design -- this stage produces a REASON, never a
        // re-score. Re-judging is a future run's panel job, not this agent's.
        required: ['title', 'rescue_possible', 'reframed_pitch', 'narrowed_seam', 'residual_blocker'],
        properties: {
          title: { type: 'string' },
          rescue_possible: { type: 'boolean', description: 'is there a plausible reframing that could make it eligible later?' },
          reframed_pitch: { type: 'string', description: 'the rescued framing, or "" if none' },
          narrowed_seam: { type: 'string', description: 'the smaller eligible seam, or "" if none' },
          residual_blocker: { type: 'string', description: 'the irreducible reason it stays rejected (the durable signal for next run)' },
        },
      },
    },
  },
}
const rescue = rejected.length ? await agent(
  `You are the STEELMAN. Below are ONLY the ideas the panel did not adopt (PARK / REJECT /
INELIGIBLE), each with the reviewers\u0027 rationale. For EACH, attempt one good-faith rescue: is there
a reframing or a NARROWER seam that would make it eligible and worth a closer look later (e.g. a
std-dev anomaly KIND -> an owner-set absolute threshold; a feature needing a missing gold source ->
the authorable contract-with-blocking-reason seam)? If yes, give the reframed_pitch + narrowed_seam.
If no, state the irreducible residual_blocker plainly -- that reason is the durable signal the next
run inherits so it stops re-litigating.

YOU DO NOT RE-SCORE. You output a reason, never a verdict or eligibility -- the gate has already
ruled. A rescue is a suggestion for a HUMAN to consider in a future run, never an override. Respect
every hard principle: a \u0022rescue\u0022 that still executes, bypasses a gate, or fabricates confidence is
NOT a rescue -- say rescue_possible false and name the principle.

=== NOT-ADOPTED IDEAS (title, verdict, eligibility, rationale) ===
${JSON.stringify(rejected.map(i => ({ title: i.title, verdict: i.verdict, eligible: i.eligible, rationale: i.rationale })), null, 2)}`,
  { label: 'rescue:steelman', phase: 'Rescue', schema: RESCUE_SCHEMA, ...GATHER }
) : { rescues: [] }

// ===================== 8. RENDER (pure JS, orchestrator writes) =====================
// Deterministic output: the workflow does NOT write the file (matching the repo's
// only sibling, speckit-finish-chain, where all writes are agent-mediated and the
// top-level script writes nothing). It returns backlog_markdown + backlog_path; the
// ORCHESTRATOR performs the Write. Same review data + same args -> byte-stable string.
phase('Render')
const BACKLOG_PATH = 'docs/roadmap/idea-backlog.md'

// ASCII normalization of the authored backlog (default on, Principle IX). Agent prose
// (rationale, dissent, rescue, portfolio summary, memory citations) is NOT constrained to
// ASCII upstream, so norm() must GUARANTEE ASCII on the way into the file, not just fold a
// few known glyphs. The FOLD table maps common punctuation to readable ASCII; a final
// catch-all replaces any remaining non-ASCII codepoint (NBSP -> space, everything else
// dropped) so a stray smart-quote/ellipsis/non-breaking-space can never break the contract.
// The FOLD glyph literals are the only non-ASCII in this file.
const FOLD = [
  ['\u2014', '--'], ['\u2013', '--'], ['\u2015', '--'],   // em / en / horizontal bar
  ['\u2192', '->'], ['\u00b7', '-'], ['\u2022', '-'],     // arrow / middle dot / bullet
  ['\u2018', "'"], ['\u2019', "'"], ['\u201a', "'"],      // smart single quotes
  ['\u201c', '"'], ['\u201d', '"'], ['\u201e', '"'],      // smart double quotes
  ['\u2026', '...'],                                  // ellipsis
  ['\u00a0', ' '], ['\u2009', ' '], ['\u202f', ' '],   // non-breaking / thin / narrow-nbsp
]
function toAscii(s) {
  if (typeof s !== 'string') return ''
  let out = s
  for (const [from, to] of FOLD) out = out.split(from).join(to)
  // catch-all: any codepoint still > 127 is dropped (the named maps above handle the
  // readable cases; this is the backstop that makes the ASCII guarantee total).
  return out.replace(/[^\x00-\x7F]/g, '')
}
const norm = ASCII ? toAscii : (s => (typeof s === 'string' ? s : ''))

// Counts are pure JS arithmetic over the structured review array -- never narrated
// by an agent (the verdict/horizon enums are closed and total, so counts are total).
function tally(ideas) {
  const v = { ADOPT: 0, CONSIDER: 0, PARK: 0, REJECT: 0, SHIPPED: 0 }
  const h = { NOW: 0, HORIZON: 0 }
  for (const i of ideas) {
    if (i.verdict in v) v[i.verdict]++
    if (i.horizon in h) h[i.horizon]++
  }
  return { v, h }
}

// selfMetrics: PURE JS rollup of the run's OWN quality -- counts over data already in
// memory, fabricating nothing. Reports how the run did, not just what it produced.
function selfMetrics(reviewObj, rawCount, runHealth) {
  const ideas = (reviewObj && Array.isArray(reviewObj.scored_ideas)) ? reviewObj.scored_ideas : []
  const scored = ideas.length
  const { v } = tally(ideas)
  // gate failures (all reviewers ineligible) AND splits (a reviewer dissented) are both
  // "not a clean eligibility pass" -- counted apart so a split is not hidden as clean.
  const gateOf = i => i.eligibility_gate || (i.eligible === false ? 'fail' : 'pass')
  const ineligible = ideas.filter(i => gateOf(i) === 'fail').length
  const eligibility_split = ideas.filter(i => gateOf(i) === 'split').length
  const cons = { consistent: 0, 'minor-tension': 0, conflict: 0 }
  const disp = { survived: 0, weakened: 0, killed: 0 }
  const layers = {}
  // serves: the meta-bloat tally -- how many ideas serve the end user / an operator / the
  // tool itself. A run heavy on tool_internal is over-producing bookkeeping (the central
  // review finding). Rendered so the ratio is a durable, self-correcting signal each run.
  const serves = { end_user: 0, operator: 0, tool_internal: 0 }
  for (const i of ideas) {
    if (i.consistency in cons) cons[i.consistency]++
    if (i.survived_verification in disp) disp[i.survived_verification]++
    const L = i.strengthens_layer || 'none'
    layers[L] = (layers[L] || 0) + 1
    const sv = i.serves || 'tool_internal'
    if (sv in serves) serves[sv]++
  }
  const pct = (n, d) => d ? Math.round((n / d) * 100) : 0
  return {
    yield_funnel: { raw_pre_dedupe: rawCount, scored, adopt: v.ADOPT, consider: v.CONSIDER, park: v.PARK, reject: v.REJECT, shipped: v.SHIPPED },
    eligibility_rejection_rate_pct: pct(ineligible, scored),
    eligibility_split_count: eligibility_split,
    consistency_mix: cons,
    survived_verification_mix: disp,
    layer_coverage: layers,                 // populated once layer-tag ships (FU2)
    serves_mix: serves,                     // meta-bloat signal: end_user / operator / tool_internal
    degraded: !!(runHealth && runHealth.degraded),
  }
}

// One idea -> its markdown block. Mirrors the existing idea-backlog.md per-idea shape:
//   ### <title>
//   `<horizon>` - **V<n> / F<n>** - consistency: <c> - <eligibility tag>
//   **Why this verdict:** <rationale>
//   **Panel dissent:** <dissent>        (only when the panel disagreed)
//   **First step:** <first_step or 'None.'>
function renderIdea(i) {
  // Three-state eligibility: a 2-1 split is NOT a clean pass -- it reads as needs-human-review,
  // not "respects principles", so a dissenting hard-principle finding stays visible.
  const gate = i.eligibility_gate || (i.eligible === false ? 'fail' : 'pass')
  const eligTag = gate === 'fail'
    ? '**INELIGIBLE -- violates a hard principle**'
    : (gate === 'split'
      ? '**ELIGIBILITY SPLIT -- a reviewer flagged a hard-principle concern; needs human review**'
      : 'respects principles')
  const meta = `\`${i.horizon}\` - **V${i.value_score} / F${i.feasibility_score}** - consistency: ${norm(i.consistency)} - ${eligTag}`
  const lines = [
    `### ${norm(i.title)}`,
    '',
    meta,
    '',
    `**Why this verdict:** ${norm(i.rationale)}`,
  ]
  if (i.dissent && String(i.dissent).trim()) {  // panel split (PR5); '' if unanimous
    lines.push('', `**Panel dissent:** ${norm(i.dissent)}`)
  }
  const firstStep = (i.first_step && String(i.first_step).trim()) || 'None.'
  lines.push('', `**First step:** ${norm(firstStep)}`)
  return lines.join('\n')
}

// renderBacklog: deterministic. `prior` is the Memory object (PR4); when present its
// shipped/settled prior ideas are rendered as a SHIPPED / SETTLED appendix so the live
// ADOPT/CONSIDER/PARK/REJECT body stays about OPEN ideas. Matching is read from Memory's
// own citations -- title is NOT a reliable cross-run join key, so no fuzzy matcher here.
function renderBacklog(review, opts) {
  const ideas = (review && Array.isArray(review.scored_ideas)) ? review.scored_ideas : []
  const { v, h } = tally(ideas)
  const dateLine = opts.date ? `Generated on ${opts.date}.` : 'Generated on (date pending).'
  const rawN = opts.rawCount, scoredM = ideas.length, rounds = opts.rounds

  // History-aware contract (the run is now memory-aware; see PR4). Still an idea BANK,
  // never a roadmap: a SHIPPED tag only records a human already took an equivalent idea
  // through the normal process -- the engine never promotes anything itself.
  const shippedSuffix = v.SHIPPED ? ', SHIPPED ' + v.SHIPPED : ''   // de-nested: no `` inside ${}
  const HEADER = [
    '# Seshat BI -- Idea Bank',
    '',
    '> **This is a future-idea bank, not a roadmap and not a commitment.** Nothing here is',
    '> planned, scheduled, or approved. It is exploratory brainstorming output to browse for',
    '> inspiration. The authoritative roadmap is `docs/roadmap/roadmap.md` (F-numbered features).',
    '',
    '_Re-running regenerates this file as a HISTORY-AWARE snapshot: each run still re-reasons every',
    '_idea from scratch, but it now READS the prior bank and Ground\'s verified ship-status first, so',
    '_an idea that has since SHIPPED is recorded as shipped (with its evidence) and a settled rejection',
    '_is not re-litigated. This is still an idea BANK, not an evolving plan: nothing here is promoted,',
    '_scheduled, or committed. A SHIPPED tag only records that a human already took an equivalent idea',
    '_through the normal feature process -- the engine never moves an idea onto the roadmap itself. The',
    '_verdicts and scores are an automated reviewer\'s triage opinion. An idea advances only through the',
    '_normal spec/feature process, with a human decision._',
    '',
    `_Generated by the \`idea-engine\` workflow. ${dateLine}_`,
    '',
    // Fail-loud: a degraded run (a dead/empty lens) is announced at the top, not hidden.
    ...(opts.health && opts.health.degraded ? [`> **${norm(opts.health.banner)}**`, ''] : []),
    // Honest funnel: raw and scored are both real JS counts; the sentence does not
    // imply a measured conversion between them. SHIPPED is shown only when nonzero so the
    // count stays equal to the rendered sections (no scored idea silently disappears).
    `**${scoredM} ideas scored** (generated across ${rounds} rounds; raw pre-dedupe ${rawN}). Verdicts: ADOPT ${v.ADOPT}, CONSIDER ${v.CONSIDER}, PARK ${v.PARK}, REJECT ${v.REJECT}${shippedSuffix}. Horizon: NOW ${h.NOW}, HORIZON ${h.HORIZON}.`,
  ].join('\n')

  const PORTFOLIO = ['## Reviewer portfolio verdict', '', `> ${norm((review && review.summary) || S())}`].join('\n')

  const LEGEND = [
    '## Legend',
    '',
    '- **Verdict** (reviewer\'s *triage opinion only* -- not a decision to build) -- ADOPT (worth a closer look first; eligible, consistent, high value) - CONSIDER (interesting; needs a decision or dependency) - PARK (horizon / later) - REJECT (ineligible or conflicts -- kept for the record).',
    '- **Horizon** -- `NOW` (fits the repo today) - `HORIZON` (future vision).',
    '- **Eligibility** -- respects all hard principles, or violates one (named in the rationale).',
    '- **V / F** -- value / feasibility (1-10), reviewer-assigned.',
    '- **SHIPPED / SETTLED** -- a prior idea Memory matched to shipped work or a settled rejection; kept for the record, not an open candidate.',
  ].join('\n')

  // Design-foundation lane (G1, spec-dir 066): a first-class CATEGORICAL cohort view of
  // the design layer. It groups ideas by their EXISTING `strengthens_layer === 'design-system'`
  // signal (the design lens + design-foundation reviewer already emit it) and renders them as
  // a cross-reference list -- title + the existing categorical verdict + horizon only. It is
  // ROUTING/RENDERING ONLY: it attaches NO computed or ranked numeric score (roadmap hard
  // rule #9), never promotes an idea onto the roadmap or assigns an F-row (Principle V), and
  // does not touch scoring, the Memory contract, or any authoring. The cohort renders
  // PRESENT-BUT-EMPTY so the design layer stays a visible first-class cohort even on a run
  // with zero design ideas. Non-design ideas are never forced in (strict signal match).
  const designCohort = ideas.filter(i => i.strengthens_layer === 'design-system')
  const DESIGN_LANE = [
    '## Design Foundation',
    '',
    '_A first-class CATEGORICAL cohort of the Power BI presentation FOUNDATION layer',
    '(`strengthens_layer = design-system`): theme-token contracts, background/canvas',
    'conventions, layout blueprints, accessibility/contrast, design-review evidence --',
    'governance of the design layer, never report authoring. This is a cross-reference',
    'grouping, not a re-score: each idea keeps its existing verdict and is detailed in',
    'its verdict section above. No numeric score is attached here (roadmap hard rule #9),',
    'and the lane never promotes an idea onto the roadmap or assigns an F-row (Principle V)._',
    '',
    designCohort.length
      ? designCohort.map(i => `- **${norm(i.title)}** -- ${norm(i.verdict)} - \`${norm(i.horizon)}\``).join('\n')
      : '_(No design-foundation ideas in this run. The lane stays present as a first-class cohort.)_',
  ].join('\n')

  // YOUR IDEAS lane: the load-bearing traceability surface for the user-idea feature. Modeled
  // exactly on the Design Foundation cohort, but it renders the FULL per-idea verdict (V/F,
  // eligibility, verdict) PLUS the interpreter's note (original words -> chosen reading, and the
  // readings it rejected) so the user can (a) find their own idea instantly at the TOP, whatever
  // the verdict, and (b) catch a misread. Rendered ONLY when the user supplied ideas; omitted
  // entirely otherwise (the lane never shows on an ordinary generation run). Cross-reference view:
  // no re-score -- each idea keeps its verdict and also appears in its verdict section below.
  // userNotes is keyed by the interpreter's ORIGINAL title; the panel may have reworded the row,
  // so look notes up by normalized key (same identity origin was re-asserted on) -- an exact-title
  // lookup would drop the "Your words / Read as" lines whenever the title drifted.
  const userNotesRaw = opts.userNotes || {}
  const userNotes = {}
  for (const k of Object.keys(userNotesRaw)) userNotes[proseKey(k)] = userNotesRaw[k]
  const userCohort = ideas.filter(i => i.origin === 'user')
  const YOUR_IDEAS = userCohort.length
    ? ['## Your Ideas (expanded + reviewed)', '',
       '_Your own idea(s), grown from your words into a reviewable shape and run through the same',
       'skeptic + reviewer panel as every other idea. Each shows how the engine READ your words (so',
       'you can catch a misread), the verdict, and V/F scores. The verdict is a triage opinion, never',
       'a decision to build. A rejected idea stays here (not hidden below) with its reason -- and gets',
       'a steelman note in the Rescue section if a narrower eligible version exists._', '',
       userCohort.map(i => {
         const gate = i.eligibility_gate || (i.eligible === false ? 'fail' : 'pass')
         const eligTag = gate === 'fail' ? 'INELIGIBLE' : (gate === 'split' ? 'eligibility split -- needs human review' : 'respects principles')
         const n = userNotes[proseKey(i.title)] || {}
         const lines = [`- **${norm(i.title)}** -- ${norm(i.verdict)} - \`${norm(i.horizon)}\` - V${i.value_score} / F${i.feasibility_score} - ${eligTag}`]
         if (n.original_words) lines.push(`  - Your words: "${norm(n.original_words)}"`)
         if (n.chosen_reading) lines.push(`  - Read as: ${norm(n.chosen_reading)}`)
         const rej = Array.isArray(n.rejected_readings) ? n.rejected_readings.filter(Boolean) : []
         if (rej.length) lines.push(`  - Other readings not taken (tell me if I misread you): ${rej.map(norm).join('; ')}`)
         return lines.join('\n')
       }).join('\n')].join('\n')
    : null

  // Sections in fixed order; preserve input order within each (no sort, no RNG).
  // Empty sections are omitted. SHIPPED is included so a panel-detected duplicate-of-
  // shipped candidate is never silently dropped from the rendered set (it is scored, so
  // it must appear somewhere); it renders last as a distinct "already shipped" bucket.
  const SECTION_TITLES = {
    ADOPT: '## ADOPT', CONSIDER: '## CONSIDER', PARK: '## PARK', REJECT: '## REJECT',
    SHIPPED: '## SHIPPED (panel judged this a duplicate of shipped work)',
  }
  const SECTIONS = ['ADOPT', 'CONSIDER', 'PARK', 'REJECT', 'SHIPPED'].map(verdict => {
    const group = ideas.filter(i => i.verdict === verdict)
    if (!group.length) return null
    return [SECTION_TITLES[verdict], '', group.map(renderIdea).join('\n\n')].join('\n')
  }).filter(Boolean)

  // SHIPPED / SETTLED appendix from Memory (prior ideas no longer open). Omitted when
  // Memory is absent (first run) or found nothing shipped/settled.
  const priorIdeas = (opts.prior && Array.isArray(opts.prior.prior_ideas)) ? opts.prior.prior_ideas : []
  const closed = priorIdeas.filter(p => p.current_state === 'shipped' || p.current_state === 'rejected-settled')
  const APPENDIX = closed.length
    ? ['## SHIPPED / SETTLED (prior ideas, for the record)', '',
       closed.map(p => {
         const tag = p.current_state === 'shipped' ? 'SHIPPED' : 'SETTLED (rejected)'
         return `- **${norm(p.prior_id)} ${norm(p.prior_title)}** -- ${tag}. ${norm(p.state_citation || S())}`
       }).join('\n')].join('\n')
    : null

  // Rescue notes: for each not-adopted idea, the steelman's reframing or the irreducible
  // blocker. Reasons only -- never a re-score. Omitted on a clean run (nothing rejected).
  const rescues = (opts.rescue && Array.isArray(opts.rescue.rescues)) ? opts.rescue.rescues : []
  const RESCUE = rescues.length
    ? ['## Rescue notes (steelman of the not-adopted)', '',
       '_A reframing that MIGHT make an idea eligible later, or the irreducible reason it stays out. A reason for a human to weigh next run -- never a verdict; the gate already ruled._', '',
       rescues.map(r => {
         const head = `- **${norm(r.title)}** -- ${r.rescue_possible ? S(114,101,115,99,117,101,32,112,111,115,115,105,98,108,101) : S(110,111,32,114,101,115,99,117,101)}.`
         const seamNote = r.narrowed_seam ? ' Narrowed seam: ' + norm(r.narrowed_seam) : ''   // de-nested
         const body = r.rescue_possible
           ? ` ${norm(r.reframed_pitch || S())}${seamNote}`
           : ` ${norm(r.residual_blocker || S())}`
         return head + body
       }).join('\n')].join('\n')
    : null

  // Run health & self-metrics: how this run did (deterministic counts). Written into the
  // file so it is a durable signal, not an editor-optional header.
  const m = opts.metrics
  const METRICS = m ? (() => {
    const yf = m.yield_funnel
    const layerPairs = Object.entries(m.layer_coverage || {}).map(([k, n]) => k + ' ' + n).join(', ')   // de-nested
    const layerLine = Object.keys(m.layer_coverage || {}).length > 1 || (m.layer_coverage && !m.layer_coverage.none)
      ? `\n- Layer coverage: ${layerPairs}`
      : ''
    return ['## Run health & self-metrics', '',
      `- Yield: ${yf.raw_pre_dedupe} raw -> ${yf.scored} scored (ADOPT ${yf.adopt}, CONSIDER ${yf.consider}, PARK ${yf.park}, REJECT ${yf.reject}).`,
      `- Eligibility-rejection rate: ${m.eligibility_rejection_rate_pct}%.`,
      `- Consistency: ${m.consistency_mix.consistent} consistent, ${m.consistency_mix[S(109,105,110,111,114,45,116,101,110,115,105,111,110)]} minor-tension, ${m.consistency_mix.conflict} conflict.`,
      `- Verification: ${m.survived_verification_mix.survived} survived, ${m.survived_verification_mix.weakened} weakened, ${m.survived_verification_mix.killed} killed.${layerLine}`,
      `- Who it serves (meta-bloat signal): end-user ${m.serves_mix.end_user}, operator ${m.serves_mix.operator}, tool-internal ${m.serves_mix.tool_internal}. A run heavy on tool-internal is over-producing self-checking; prefer ideas that reach the end user or the operator.`,
      `- Run health: ${m.degraded ? S(68,69,71,82,65,68,69,68,32,40,115,101,101,32,98,97,110,110,101,114,32,97,98,111,118,101,41) : S(97,108,108,32,108,101,110,115,101,115,32,114,101,112,111,114,116,101,100)}.`,
    ].join('\n')
  })() : null

  // YOUR_IDEAS leads (right after the header block) so the user finds their reviewed idea first.
  return [HEADER, ...(YOUR_IDEAS ? [YOUR_IDEAS] : []), PORTFOLIO, LEGEND, DESIGN_LANE, ...SECTIONS, ...(RESCUE ? [RESCUE] : []), ...(APPENDIX ? [APPENDIX] : []), ...(METRICS ? [METRICS] : [])].join('\n\n') + '\n'
}

const self_metrics = selfMetrics(review, allIdeas.length, run_health)
const backlog_markdown = renderBacklog(review, {
  date: DATE,
  ascii: ASCII,
  rawCount: allIdeas.length,
  rounds: 3,                 // r1 + cross + fill generation rounds
  prior: memory,             // PR4: cross-run memory -> SHIPPED/SETTLED appendix
  health: run_health,        // FU1: fail-loud DEGRADED banner
  metrics: self_metrics,     // FU1: deterministic run-quality rollup
  rescue,                    // FU2: steelman notes for the not-adopted
  userNotes: userNotesByTitle, // user-idea feature: interpreter reading notes for the Your Ideas lane
})

return {
  explore_map,                               // the structured map (verified, or unverified-fallback if reconcile failed)
  explore_rendered: exploreMap,              // the prose+table substrate the lenses saw
  ground_missing_subsystems: merged.missing_subsystems,  // dead explorers -- degraded signal
  ground_contradictions: merged.contradictions.length,   // how many ship-status disputes were ruled
  memory,                                    // prior-bank labeling (shipped/settled/open)
  interpreted,                               // user-idea feature: raw interpreter output (null if no user ideas)
  user_ideas_in: USER_IDEAS,                 // the raw user idea strings this run reviewed (null if none)
  user_ideas_expanded: userIdeas.length,     // how many were successfully expanded into the pool
  gaps_found: gaps,
  synthesis,
  adversarial_verify: verify,
  panel,                                     // the 3 raw reviewer records (pre-aggregation)
  panel_splits: aggregated.splits,           // ideas where the panel disagreed (eligibility/score)
  review,                                    // aggregated, renderer-shaped (JS gate + clamp applied)
  raw_idea_count: allIdeas.length,
  rounds: { r1: round1.filter(r => r._status === 'ok').length, cross: crossRound.filter(r => r._status === 'ok').length, fill: fillRound.filter(r => r._status === 'ok').length },
  run_health,                                // FU1: per-round census + degraded flag
  self_metrics,                              // FU1: deterministic run-quality rollup
  rescue,                                    // FU2: steelman notes for the not-adopted
  focus: FOCUS,
  // Deterministic output: orchestrator writes backlog_markdown to backlog_path.
  backlog_markdown,
  backlog_path: BACKLOG_PATH,
}
