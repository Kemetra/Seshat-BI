export const meta = {
  name: 'idea-engine',
  description: 'Idea generator for Seshat BI. Ground maps the real repo with five subsystem explorers + a reconcile-verify pass; Memory reads the prior bank so shipped/settled ideas are not regenerated; three lenses (creative / BI analyst / technical) generate in parallel, then cross-pollinate; a completeness critic finds blind spots and triggers one targeted fill pass; a synthesizer merges; an adversarial skeptic challenges EVERY candidate (default-refuted); a three-standpoint reviewer PANEL scores value/feasibility and rules eligibility; a pure-JS aggregate takes the median, gates eligibility, and applies a demote-only clamp. Every agent stage runs on Opus at xhigh effort. Output: a ranked NOW/HORIZON idea BANK, rendered deterministically -- exploratory inspiration, not a roadmap or commitment.',
  whenToUse: 'When you want a deep, exhaustive, rigorously vetted, history-aware idea bank for the project. All-Opus, xhigh effort, multi-round, multi-explorer, panel-reviewed -- thorough and heavy (many agents/tokens/time). Re-runnable; pass a focus string or {focus,sinceRef,date,ascii}. Output is an idea bank, never a plan.',
  phases: [
    { title: 'Ground',         detail: '5 subsystem explorers map the repo in parallel; JS merge + reconcile-verify', model: 'opus' },
    { title: 'Memory',         detail: 'read prior bank + Ground ship-status: label shipped/settled ideas (no re-litigation)', model: 'opus' },
    { title: 'Generate',       detail: 'creative / BI / technical lenses propose in parallel (round 1)', model: 'opus' },
    { title: 'Cross-pollinate',detail: 'each lens reacts to the others; surface cross-disciplinary ideas', model: 'opus' },
    { title: 'Completeness',   detail: 'critic finds blind spots -> one more targeted generation pass', model: 'opus' },
    { title: 'Synthesize',     detail: 'merge + dedupe into one candidate set', model: 'opus' },
    { title: 'Verify',         detail: 'adversarial skeptic challenges EVERY candidate (default-refuted)', model: 'opus' },
    { title: 'Panel-review',   detail: '3 independent reviewers (principle / shipped-dup / value-feasibility) score the set', model: 'opus' },
    { title: 'Aggregate',      detail: 'pure-JS median + eligibility gate + demote-only clamp; tiny prose agent for dissent', model: 'opus' },
    { title: 'Rescue',         detail: 'steelman the not-adopted ideas (reason only, never a re-score); skipped if none', model: 'opus' },
    { title: 'Render',         detail: 'pure-JS: render the idea-backlog markdown (no agent); orchestrator writes' },
  ],
}

const REPO = 'C:/Users/Shaaban/Documents/GitHub/Seshat_BI'

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
const FOCUS_LINE = FOCUS
  ? `\nFOCUS for this run (bias ideas toward this, but don't ignore strong off-theme ideas): ${FOCUS}\n`
  : ''

const PROJECT = `
PROJECT: Seshat BI (package alias Seshat_BI; formerly "Tower BI Agent Kit"). An AGENT-FIRST
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

// ---- model tiers ----
// User directive: run ALL stages on Opus for maximum quality (overrides the
// sonnet-scout / opus-lead split). Both aliases point at Opus; kept as two names
// so the stage intent stays readable and the split is easy to restore later.
const SCOUT = { model: 'opus', effort: 'xhigh' }   // explore / generate / cross-pollinate / critic / verify
const LEAD  = { model: 'opus', effort: 'xhigh' }   // synthesize / final review

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
        required: ['title', 'pitch', 'horizon', 'why_it_fits', 'rough_shape', 'strengthens_layer'],
        properties: {
          title: { type: 'string' },
          pitch: { type: 'string', description: '2-3 sentences: what it is and the value' },
          horizon: { type: 'string', enum: ['NOW', 'HORIZON'] },
          why_it_fits: { type: 'string' },
          rough_shape: { type: 'string', description: 'the seam it touches, not full impl' },
          // Which knowledge layer / spine this idea would strengthen -- surfaces layer
          // starvation in self-metrics. The lens JUDGES this; nothing is assigned by index.
          strengthens_layer: { type: 'string', enum: ['bi-sql', 'bi-dax', 'bi-python', 'bi-bigdata', 'retail-kpi', 'docs-spine', 'none'], description: 'the knowledge layer this most strengthens, or none' },
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
        required: ['title', 'horizon', 'eligible', 'ineligibility_reason', 'consistency', 'value_score', 'feasibility_score', 'verdict', 'survived_verification', 'prior_status', 'relitigation', 'rationale', 'strengthens_layer'],
        properties: {
          title: { type: 'string' },
          horizon: { type: 'string', enum: ['NOW', 'HORIZON'] },
          strengthens_layer: { type: 'string', enum: ['bi-sql', 'bi-dax', 'bi-python', 'bi-bigdata', 'retail-kpi', 'docs-spine', 'none'], description: 'carried from the idea: the knowledge layer it most strengthens' },
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
  // The skeptic's "challenge EVERY candidate" contract is enforced HERE in JS, not by the
  // schema (which only requires an array) or the prompt (a request). An idea the skeptic
  // silently omitted from challenged[] is treated as if it FAILED the gate: marked killed
  // and demoted out of ADOPT, mirroring the demote-only eligibility clamp. Unchallenged !=
  // safe -- it means coverage was not proven, so it must not read as a survived ADOPT.
  const challengedTitles = new Set(((verifyRec && Array.isArray(verifyRec.challenged) ? verifyRec.challenged : []))
    .map(ch => ch && ch.title).filter(Boolean))
  let uncovered = 0
  // union of titles, first-seen order preserved (reviewer 0 then 1 then 2). Carry each
  // reviewer's standpoint/key DOWN onto its rows so attribution survives grouping.
  const order = []
  const seen = new Set()
  const byTitle = {}
  for (const reviewer of live) {
    const standpoint = reviewer.reviewer_standpoint || reviewer._key || 'reviewer'
    for (const si of (reviewer.scored_ideas || [])) {
      if (!si || !si.title) continue
      if (!seen.has(si.title)) { seen.add(si.title); order.push(si.title) }
      ;(byTitle[si.title] = byTitle[si.title] || []).push({ ...si, reviewer_standpoint: si.reviewer_standpoint || standpoint })
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

  const ideas = order.map(title => {
    const rows = byTitle[title]
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
    if (!challengedTitles.has(title)) {
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
    // rationale: concatenate each reviewer's one-liner with its standpoint
    const rationale = rows.map(r => `[${r.reviewer_standpoint || 'reviewer'}] ${r.rationale || ''}`.trim()).join(' ')

    return {
      title, horizon, consistency, value_score, feasibility_score, score_spread,
      eligibility_gate, verdict, survived_verification, first_step, rationale, strengthens_layer,
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
const EXPLORERS = [
  { key: 'knowledge', label: 'explore:knowledge', brief: `Map skills/: each knowledge layer's SKILL.md + INDEX.md. COUNT the layers exactly (there are FIVE: bi-sql, bi-dax, bi-python, bi-bigdata, retail-kpi -- do not assume four) and note which are seed vs mature. Capture what each layer routes and its two-hop contract.` },
  { key: 'src', label: 'explore:src', brief: `Map src/retail/**: the rule families in rules/*.py (each @register), cli.py, runner.py, registry. Cross-check the rule count against EXPECTED_RULE_IDS in tests/unit/test_rules_wiring.py (the wiring test is the source of truth). Note the never-execute / stdlib-only discipline as you see it in code.` },
  { key: 'docs', label: 'explore:docs', brief: `Map the docs spine: COMPASS.md, AGENTS.md, docs/knowledge-map.md, docs/readiness/, docs/metrics/, docs/quality/. Capture the readiness stage model (7 stages, 4 statuses), the router, the metric-contract store, and any quality/smoke-test docs.` },
  { key: 'roadmap', label: 'explore:roadmap', brief: `Map docs/roadmap/roadmap.md as the canonical F-number ledger AND read docs/roadmap/idea-backlog.md for context. For roadmap.md, record each F-number's status using the shared enum. This subsystem owns the roadmap's own SHIPPED/DEFERRED/PARTIAL markers.` },
  { key: 'ship-delta', label: 'explore:ship-delta', brief: `Establish ship-status from REPO TRUTH ONLY: git log subjects${SINCE_REF ? ` over range ${SINCE_REF}` : ` (no range supplied -- use roadmap SHIPPED markers only; do NOT invent a range)`} plus the roadmap's SHIPPED markers. Do NOT read prior idea-backlog titles -- those are engine OUTPUT, not repo truth (reading them is a statefulness leak; that is cross-run memory's job, not grounding's). Your ship_status describes only "what the repo contains."` },
]

const submaps = await parallel(EXPLORERS.map(e => () =>
  agent(
    `${PROJECT}

YOU ARE A SUBSYSTEM EXPLORER for Seshat BI. Read the real repo under ${REPO} and map ONLY your
subsystem. Do NOT propose ideas. Do NOT execute anything (read-only). Cite a file/feature for
every capability and every ship-status row. If a path is unreadable, list it in 'unreadable' --
never guess.

YOUR SUBSYSTEM: ${e.brief}

Return capability_notes (each citing a file), tensions (incomplete/duplicated/awkward seams),
ship_status (feature_id + status from the shared enum + evidence_path), and unreadable[].`,
    { label: e.label, phase: 'Ground', agentType: 'Explore', schema: SUBMAP_SCHEMA, ...SCOUT }
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
  { label: 'ground:reconcile-verify', phase: 'Ground', schema: MERGED_MAP_SCHEMA, ...SCOUT }
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
    m.ship_status.forEach(r => lines.push(`- ${r.feature_id}: ${r.status} [${r.evidence_path}]${r.verifier_opened_evidence ? '' : ' (UNVERIFIED-evidence)'}`))
    lines.push('')
  }
  if (Array.isArray(m.reconciliation_ledger) && m.reconciliation_ledger.length) {
    lines.push('=== RECONCILED CONTRADICTIONS ===')
    m.reconciliation_ledger.forEach(r => lines.push(`- ${r.feature_id}: ruled ${r.ruling} (${r.winning_evidence})`))
    lines.push('')
  }
  if (Array.isArray(m.missing_subsystems) && m.missing_subsystems.length) {
    lines.push(`=== DEGRADED: missing subsystem explorers: ${m.missing_subsystems.join(', ')} ===`, '')
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
re-litigate settled rejections. You are given Ground's VERIFIED ship-status table -- that is your
authoritative source for what shipped. Do NOT re-read git (Ground owns that).

STEPS:
1. Read the prior bank at ${REPO}/docs/roadmap/idea-backlog.md from disk. If it does not exist or
   has no idea headings, return prior_ideas: [] and say so in notes (a first run is normal).
2. Parse each idea heading (e.g. "### A1. Machine-Checkable Route Registry"). For EACH: capture
   prior_id, prior_title, the verdict SECTION it sits under (## ADOPT/CONSIDER/PARK/REJECT) as
   prior_verdict, and -- as verdict_citation -- the VERBATIM heading line plus the verbatim section
   header, so any misparse is a quotable artifact a human can catch.
2b. ALSO parse the "## SHIPPED / SETTLED (prior ideas, for the record)" appendix if present: its
   entries are BULLETS, not headings, of the form "- **<id> <title>** -- SHIPPED. <citation>" or
   "-- SETTLED (rejected). <citation>". For each bullet, emit a prior_ideas entry with prior_id,
   prior_title, prior_verdict (ADOPT/REJECT/UNKNOWN as best inferred from the tag), current_state
   ("shipped" for SHIPPED, "rejected-settled" for SETTLED), verdict_citation = the verbatim bullet,
   and state_citation = the bullet's trailing citation. This is the round-trip: closed ideas live
   in that appendix as bullets, so they MUST be re-read here or they vanish from memory next run.
3. Set current_state by matching the idea against Ground's ship_status:
   - "shipped" ONLY if a ship_status row marks an equivalent capability SHIPPED -- cite that row
     (feature_id + evidence_path) in state_citation.
   - "rejected-settled" if the prior verdict was REJECT/INELIGIBLE and nothing changed -- cite the
     prior rationale line.
   - "open" otherwise. If you cannot back a shipped/settled claim with a citation, it is "open".
4. NEVER guess that something shipped. No citation -> open. git_corroborated is always false
   (Ground owns git). You never execute anything and you never write the roadmap.

=== GROUND VERIFIED SHIP-STATUS (your only state source) ===
${shipStatusForMemory}`,
  { label: 'memory:read-prior', phase: 'Memory', schema: MEMORY_SCHEMA, ...SCOUT }
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

// ===================== 2. GENERATE (round 1) =====================
phase('Generate')
const LENSES = [
  { key: 'creative', label: 'gen:creative', role: `a CREATIVE PROGRAMMER lens. Generate inventive, original ideas -- features, agent capabilities, DX wins, novel uses of the knowledge layers, surprising combinations. Favor imagination and delight.` },
  { key: 'bi',       label: 'gen:bi-analyst', role: `a PROFESSIONAL BI ANALYST lens (15+ yrs retail). Generate ideas that increase ANALYTICAL VALUE -- KPI/metric coverage, decision-support, forecasting, anomaly/exception surfacing, business-question coverage, things a real merchandiser/finance owner needs.` },
  { key: 'technical',label: 'gen:technical', role: `a PROFESSIONAL TECHNICAL ARCHITECT lens. Generate ideas that strengthen the system -- architecture, testing/CI gates, performance, the router/two-hop contract, knowledge-layer tooling, drift/reconciliation, adapter design, observability, agent-eval harnesses. Buildable in-repo.` },
]
function genPrompt(role, extra='') {
  return `You are ${role}\nGenerate 6-8 ideas for Seshat BI. Each MUST respect the hard principles (no executor, no gate bypass, generic-only, no fabricated confidence). Mix NOW and HORIZON. For each idea set strengthens_layer to the ONE knowledge layer it most strengthens (bi-sql / bi-dax / bi-python / bi-bigdata / retail-kpi / docs-spine), or 'none' if it strengthens the engine/CLI/gates rather than a knowledge layer -- judge honestly, do not force a layer. ${extra}${MEMORY_LINE}\n\n=== REPO MAP ===\n${exploreMap}`
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
  agent(genPrompt(l.role), { label: `${l.label}:r1`, phase: 'Generate', schema: IDEA_SCHEMA, ...SCOUT })
    .then(r => classify(r, l.key))
))

// ===================== 3. CROSS-POLLINATE =====================
phase('Cross-pollinate')
const round1Json = JSON.stringify(round1.filter(r => r._status === 'ok').map(r => ({ lens: r.lens || r._key, ideas: r.ideas })), null, 2)
const crossRound = await parallel(LENSES.map(l => () =>
  agent(
    genPrompt(l.role,
      `You have now SEEN what the other two lenses proposed (below). React to them: combine a strong idea from another lens with your own perspective, fill a gap they left, or push a half-idea further. Generate 3-5 NEW cross-disciplinary ideas (do NOT repeat ideas already listed). The best ideas live at the seams between disciplines.\n\n=== ALL ROUND-1 IDEAS ===\n${round1Json}`),
    { label: `${l.label}:cross`, phase: 'Cross-pollinate', schema: IDEA_SCHEMA, ...SCOUT }
  ).then(r => classify(r, l.key))
))

// ===================== 4. COMPLETENESS CRITIC -> targeted pass =====================
phase('Completeness')
const sofar = [...round1, ...crossRound].filter(r => r._status === 'ok')
const sofarJson = JSON.stringify(sofar.map(r => ({ lens: r.lens || r._key, ideas: (r.ideas||[]).map(i => i.title) })), null, 2)
const gaps = await agent(
  `You are a COMPLETENESS CRITIC. Below are all idea TITLES generated so far for Seshat BI, plus the repo map. Your job is to find what's MISSING -- readiness stages with few ideas, repo gaps/tensions nobody addressed, idea TYPES underrepresented (e.g. all features and no DX, or all technical and no business value), and obvious adjacent ideas no lens reached. List 5-10 specific missing angles as short prompts ("nobody proposed anything for X / for the Y gap"). Do not generate full ideas -- just name the blind spots precisely.\n\n=== REPO MAP ===\n${exploreMap}\n\n=== IDEA TITLES SO FAR ===\n${sofarJson}`,
  { label: 'critic:gaps', phase: 'Completeness', ...SCOUT }
)
// one targeted fill pass aimed at the named gaps
const fillRound = await parallel(LENSES.map(l => () =>
  agent(genPrompt(l.role,
    `A completeness critic identified these BLIND SPOTS in the ideas generated so far. From YOUR lens, generate 2-4 ideas that specifically fill the gaps most relevant to you (do not repeat existing ideas).\n\n=== BLIND SPOTS ===\n${gaps}`),
    { label: `${l.label}:fill`, phase: 'Completeness', schema: IDEA_SCHEMA, ...SCOUT }
  ).then(r => classify(r, l.key))
))

const allIdeas = [...round1, ...crossRound, ...fillRound].filter(r => r._status === 'ok').flatMap(r =>
  (r.ideas || []).map(i => ({ ...i, source_lens: r.lens || r._key }))
)

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
  const degraded = anyFailed || anyShort || groundFailed || memoryFailed
  const parts = rounds.filter(r => r.ok < r.expected).map(r => `${r.label} ${r.ok}/${r.expected} lenses ok${r.failed ? ` (${r.failed} failed)` : ''}`)
  if (groundFailed) parts.unshift('grounding reconcile-verify returned null -- the repo map is the RAW UNVERIFIED submap union')
  if (memoryFailed) parts.unshift('memory:read-prior returned null -- prior shipped/settled ideas are UNKNOWN this run; lenses may re-propose closed work')
  const banner = degraded ? `DEGRADED RUN: ${parts.join('; ')}. Treat this bank as partial.` : ''
  return { rounds, degraded, banner }
})()

// ===================== 5. SYNTHESIZE =====================
phase('Synthesize')
const synthesis = await agent(
  `You are the SYNTHESIZER. Many ideas were generated across three lenses over three rounds
(initial, cross-pollination, gap-fill). Merge into ONE clean candidate set.
- DEDUPE near-duplicates (keep the strongest framing; note where lenses/rounds converged -- convergence is a strength signal).
- GROUP into themes.
- Keep each idea's title, pitch, horizon, why_it_fits, rough_shape, strengthens_layer, source_lens(es).
- Do NOT score (the reviewer does). Do NOT invent new ideas; only merge/clarify.
- Flag any idea that might violate a hard principle (the reviewer rules).
- If a candidate matches a prior idea KNOWN to have SHIPPED (see history below), KEEP it but
  tag it "prior_state: shipped" with the citation -- do NOT drop it (a materially-new variant
  and the convergence signal both matter). Dropping would hide a genuine extension.
${MEMORY_LINE}

=== REPO MAP ===\n${exploreMap}\n\n=== ALL RAW IDEAS (JSON) ===\n${JSON.stringify(allIdeas, null, 2)}

Output a clean candidate list grouped by theme, each idea with its fields + source lens(es)
+ a convergence note where applicable.`,
  { label: 'synthesize:merge', phase: 'Synthesize', ...LEAD }
)

// ===================== 6. ADVERSARIAL VERIFY (universal coverage) =====================
phase('Verify')
// Every idea is challenged -- no "only the tempting ones" escape hatch. Default
// disposition is refuted; an idea earns 'survived' only if its hardest objection fails.
const verify = await agent(
  `You are an ADVERSARIAL SKEPTIC. For EVERY idea in the synthesized candidate set below you MUST
attempt a refutation -- there is no "skip the ones that look fine." The default disposition of
every idea is that it does NOT survive; an idea earns 'survived' only if your hardest objection
provably fails. Killing nothing is a RED FLAG that you did not really try.

For EACH idea, find the strongest objection: does it secretly violate a hard principle? does it
duplicate a feature the ship-status says is already SHIPPED? is the "feasible" framing hiding a
missing dependency (a gold source, a runtime consumer, a human ruling)? would it quietly turn a
reasoning layer into an executor or a stats engine? Then rule it survived / weakened / killed
with one line of why.

=== SHIP STATUS (for the duplicate-of-shipped check) ===\n${JSON.stringify((explore_map && explore_map.ship_status) || [], null, 2)}
=== SYNTHESIZED CANDIDATES ===\n${synthesis}`,
  { label: 'verify:skeptic', phase: 'Verify', schema: VERIFY_SCHEMA, ...SCOUT }
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
    `the VALUE/FEASIBILITY REALIST. Judge value and feasibility honestly: is "feasible" hiding a missing gold source, a runtime consumer that does not exist yet, or an unmade human ruling? Reward genuine analytical/system value; discount ideas whose feasibility depends on something deferred (e.g. F016).` },
]
const panel = (await parallel(PANELISTS.map(p => () =>
  agent(
    `You are ${p.standpoint}

You are ONE of three independent reviewers scoring the SAME synthesized idea set for Seshat BI.
Score from YOUR standpoint; the other two cover the other angles. Default to caution. This is a
triage opinion for an IDEA BANK, never a build decision -- you never promote anything to the roadmap.

For EACH idea set: horizon (NOW/HORIZON); eligible (bool) + ineligibility_reason (named principle
or ''); consistency (consistent/minor-tension/conflict); value_score & feasibility_score (1-10);
verdict (ADOPT/CONSIDER/PARK/REJECT/SHIPPED -- use SHIPPED only if it matches a shipped feature);
survived_verification (survived/weakened/killed, weighed from the skeptic); prior_status
(new/shipped/rejected-settled/open-prior from the history); relitigation (n/a/settled/materially-new);
rationale; first_step for ADOPT/CONSIDER. An idea the skeptic KILLED should not be ADOPT.

=== SHIP STATUS ===\n${JSON.stringify((explore_map && explore_map.ship_status) || [], null, 2)}${MEMORY_LINE}
=== SYNTHESIZED CANDIDATES ===\n${synthesis}
=== ADVERSARIAL SKEPTIC'S CHALLENGES ===\n${verify ? JSON.stringify(verify) : '(skeptic produced nothing)'}`,
    { label: p.label, phase: 'Panel-review', schema: PANEL_REVIEWER_SCHEMA, ...LEAD }
  ).then(r => r ? { ...r, _key: p.key } : null)
)).filter(Boolean)

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

// One tiny agent writes ONLY the dissent prose + portfolio summary; it touches no number.
// It is a NON-CRITICAL prose step -- the verdicts/scores are already final in JS -- so a null
// return (schema miss / agent failure) must NOT abort the run after the panel succeeded. We
// coalesce null to a safe default (matching the defensive null-handling on the lens/panel
// agents) so the deterministic renderer still emits the aggregated scores.
const FALLBACK_DISSENT = { dissent_by_title: [], portfolio_summary: aggregated.ideas.length ? '(panel summary unavailable -- the dissent clerk did not return; verdicts and scores below are final.)' : 'No ideas reached the panel.' }
const dissentRaw = aggregated.ideas.length ? await agent(
  `You are the PANEL CLERK. Write human-facing PROSE only -- you change NO scores and NO verdicts
(those are already computed). (1) For each idea flagged with a panel split below, write a one- to
two-sentence 'dissent' explaining the disagreement (e.g. "2 reviewers ADOPT; the principle auditor
ruled it ineligible for X"). (2) Write a 'portfolio_summary': a scannable paragraph a human can act
on. Return dissent keyed by idea title, plus the summary. Do not invent ideas or numbers.

=== AGGREGATED IDEAS (verdicts/scores already final; splits flagged) ===
${JSON.stringify(aggregated.ideas.map(i => ({ title: i.title, verdict: i.verdict, eligibility_gate: i.eligibility_gate, value_score: i.value_score, feasibility_score: i.feasibility_score, score_spread: i.score_spread, per_reviewer: i._per_reviewer })), null, 2)}`,
  { label: 'aggregate:dissent-prose', phase: 'Aggregate', schema: DISSENT_SCHEMA, ...LEAD }
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
INELIGIBLE), each with the reviewers' rationale. For EACH, attempt one good-faith rescue: is there
a reframing or a NARROWER seam that would make it eligible and worth a closer look later (e.g. a
std-dev anomaly KIND -> an owner-set absolute threshold; a feature needing a missing gold source ->
the authorable contract-with-blocking-reason seam)? If yes, give the reframed_pitch + narrowed_seam.
If no, state the irreducible residual_blocker plainly -- that reason is the durable signal the next
run inherits so it stops re-litigating.

YOU DO NOT RE-SCORE. You output a reason, never a verdict or eligibility -- the gate has already
ruled. A rescue is a suggestion for a HUMAN to consider in a future run, never an override. Respect
every hard principle: a "rescue" that still executes, bypasses a gate, or fabricates confidence is
NOT a rescue -- say rescue_possible false and name the principle.

=== NOT-ADOPTED IDEAS (title, verdict, eligibility, rationale) ===
${JSON.stringify(rejected.map(i => ({ title: i.title, verdict: i.verdict, eligible: i.eligible, rationale: i.rationale })), null, 2)}`,
  { label: 'rescue:steelman', phase: 'Rescue', schema: RESCUE_SCHEMA, ...SCOUT }
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
  ['—', '--'], ['–', '--'], ['―', '--'],   // em / en / horizontal bar
  ['→', '->'], ['·', '-'], ['•', '-'],     // arrow / middle dot / bullet
  ['‘', "'"], ['’', "'"], ['‚', "'"],      // smart single quotes
  ['“', '"'], ['”', '"'], ['„', '"'],      // smart double quotes
  ['…', '...'],                                  // ellipsis
  [' ', ' '], [' ', ' '], [' ', ' '],   // non-breaking / thin / narrow-nbsp
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
  for (const i of ideas) {
    if (i.consistency in cons) cons[i.consistency]++
    if (i.survived_verification in disp) disp[i.survived_verification]++
    const L = i.strengthens_layer || 'none'
    layers[L] = (layers[L] || 0) + 1
  }
  const pct = (n, d) => d ? Math.round((n / d) * 100) : 0
  return {
    yield_funnel: { raw_pre_dedupe: rawCount, scored, adopt: v.ADOPT, consider: v.CONSIDER, park: v.PARK, reject: v.REJECT, shipped: v.SHIPPED },
    eligibility_rejection_rate_pct: pct(ineligible, scored),
    eligibility_split_count: eligibility_split,
    consistency_mix: cons,
    survived_verification_mix: disp,
    layer_coverage: layers,                 // populated once layer-tag ships (FU2)
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
    `**${scoredM} ideas scored** (generated across ${rounds} rounds; raw pre-dedupe ${rawN}). Verdicts: ADOPT ${v.ADOPT}, CONSIDER ${v.CONSIDER}, PARK ${v.PARK}, REJECT ${v.REJECT}${v.SHIPPED ? `, SHIPPED ${v.SHIPPED}` : ''}. Horizon: NOW ${h.NOW}, HORIZON ${h.HORIZON}.`,
  ].join('\n')

  const PORTFOLIO = ['## Reviewer portfolio verdict', '', `> ${norm((review && review.summary) || '')}`].join('\n')

  const LEGEND = [
    '## Legend',
    '',
    '- **Verdict** (reviewer\'s *triage opinion only* -- not a decision to build) -- ADOPT (worth a closer look first; eligible, consistent, high value) - CONSIDER (interesting; needs a decision or dependency) - PARK (horizon / later) - REJECT (ineligible or conflicts -- kept for the record).',
    '- **Horizon** -- `NOW` (fits the repo today) - `HORIZON` (future vision).',
    '- **Eligibility** -- respects all hard principles, or violates one (named in the rationale).',
    '- **V / F** -- value / feasibility (1-10), reviewer-assigned.',
    '- **SHIPPED / SETTLED** -- a prior idea Memory matched to shipped work or a settled rejection; kept for the record, not an open candidate.',
  ].join('\n')

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
         return `- **${norm(p.prior_id)} ${norm(p.prior_title)}** -- ${tag}. ${norm(p.state_citation || '')}`
       }).join('\n')].join('\n')
    : null

  // Rescue notes: for each not-adopted idea, the steelman's reframing or the irreducible
  // blocker. Reasons only -- never a re-score. Omitted on a clean run (nothing rejected).
  const rescues = (opts.rescue && Array.isArray(opts.rescue.rescues)) ? opts.rescue.rescues : []
  const RESCUE = rescues.length
    ? ['## Rescue notes (steelman of the not-adopted)', '',
       '_A reframing that MIGHT make an idea eligible later, or the irreducible reason it stays out. A reason for a human to weigh next run -- never a verdict; the gate already ruled._', '',
       rescues.map(r => {
         const head = `- **${norm(r.title)}** -- ${r.rescue_possible ? 'rescue possible' : 'no rescue'}.`
         const body = r.rescue_possible
           ? ` ${norm(r.reframed_pitch || '')}${r.narrowed_seam ? ` Narrowed seam: ${norm(r.narrowed_seam)}` : ''}`
           : ` ${norm(r.residual_blocker || '')}`
         return head + body
       }).join('\n')].join('\n')
    : null

  // Run health & self-metrics: how this run did (deterministic counts). Written into the
  // file so it is a durable signal, not an editor-optional header.
  const m = opts.metrics
  const METRICS = m ? (() => {
    const yf = m.yield_funnel
    const layerLine = Object.keys(m.layer_coverage || {}).length > 1 || (m.layer_coverage && !m.layer_coverage.none)
      ? `\n- Layer coverage: ${Object.entries(m.layer_coverage).map(([k, n]) => `${k} ${n}`).join(', ')}`
      : ''
    return ['## Run health & self-metrics', '',
      `- Yield: ${yf.raw_pre_dedupe} raw -> ${yf.scored} scored (ADOPT ${yf.adopt}, CONSIDER ${yf.consider}, PARK ${yf.park}, REJECT ${yf.reject}).`,
      `- Eligibility-rejection rate: ${m.eligibility_rejection_rate_pct}%.`,
      `- Consistency: ${m.consistency_mix.consistent} consistent, ${m.consistency_mix['minor-tension']} minor-tension, ${m.consistency_mix.conflict} conflict.`,
      `- Verification: ${m.survived_verification_mix.survived} survived, ${m.survived_verification_mix.weakened} weakened, ${m.survived_verification_mix.killed} killed.${layerLine}`,
      `- Run health: ${m.degraded ? 'DEGRADED (see banner above)' : 'all lenses reported'}.`,
    ].join('\n')
  })() : null

  return [HEADER, PORTFOLIO, LEGEND, ...SECTIONS, ...(RESCUE ? [RESCUE] : []), ...(APPENDIX ? [APPENDIX] : []), ...(METRICS ? [METRICS] : [])].join('\n\n') + '\n'
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
})

return {
  explore_map,                               // the structured map (verified, or unverified-fallback if reconcile failed)
  explore_rendered: exploreMap,              // the prose+table substrate the lenses saw
  ground_missing_subsystems: merged.missing_subsystems,  // dead explorers -- degraded signal
  ground_contradictions: merged.contradictions.length,   // how many ship-status disputes were ruled
  memory,                                    // prior-bank labeling (shipped/settled/open)
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
