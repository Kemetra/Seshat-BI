export const meta = {
  name: 'idea-engine',
  description: 'Idea generator for Seshat BI. Explore grounds on the real repo; three lenses (creative / BI analyst / technical) generate in parallel, then cross-pollinate (each reacts to the others); a completeness critic finds blind spots and triggers one targeted fill pass; a synthesizer merges; an adversarial skeptic stress-tests the strong candidates; an external reviewer scores value/feasibility and gates eligibility & consistency. Every stage runs on Opus at xhigh effort. Output: a ranked NOW/HORIZON idea BANK -- exploratory inspiration, not a roadmap or commitment.',
  whenToUse: 'When you want a deep, exhaustive, rigorously vetted idea bank for the project. All-Opus, xhigh effort, multi-round -- thorough and heavy (many agents/tokens/time). Re-runnable; pass args to focus a theme. Output is an idea bank, never a plan.',
  phases: [
    { title: 'Explore',        detail: 'map the real repo: shipped, planned, gaps, principles', model: 'opus' },
    { title: 'Generate',       detail: 'creative / BI / technical lenses propose in parallel (round 1)', model: 'opus' },
    { title: 'Cross-pollinate',detail: 'each lens reacts to the others; surface cross-disciplinary ideas', model: 'opus' },
    { title: 'Completeness',   detail: 'critic finds blind spots -> one more targeted generation pass', model: 'opus' },
    { title: 'Synthesize',     detail: 'merge + dedupe into one candidate set', model: 'opus' },
    { title: 'Verify',         detail: 'adversarial skeptic stress-tests each strong candidate', model: 'opus' },
    { title: 'Review',         detail: 'external reviewer scores + gates eligibility & consistency', model: 'opus' },
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
        required: ['title', 'pitch', 'horizon', 'why_it_fits', 'rough_shape'],
        properties: {
          title: { type: 'string' },
          pitch: { type: 'string', description: '2-3 sentences: what it is and the value' },
          horizon: { type: 'string', enum: ['NOW', 'HORIZON'] },
          why_it_fits: { type: 'string' },
          rough_shape: { type: 'string', description: 'the seam it touches, not full impl' },
        },
      },
    },
  },
}

// ===================== 1. EXPLORE =====================
phase('Explore')
const explore = await agent(
  `${PROJECT}

YOU ARE THE EXPLORER. Read the real repo under ${REPO} and produce a tight, factual MAP the
idea generators build on. Do NOT propose ideas yet. Read enough to ground (not everything):
COMPASS.md, AGENTS.md, docs/knowledge-map.md, docs/roadmap/roadmap.md,
docs/readiness/readiness-model.md, the 5 skills' SKILL.md; skim docs/ for what's missing.

Output: 1) CAPABILITY MAP by readiness stage; 2) SHIPPED FEATURES (F-numbers, brief);
3) GAPS & DEFERRALS (F016, Tier 5 partials, seed deferrals, absent-but-expected capability);
4) TENSIONS/FRICTION (incomplete/duplicated/awkward -- good idea fuel); 5) the PRINCIPLES an
idea must respect, in your own words. Cite file/feature names. This is the shared substrate.`,
  { label: 'explore:repo-map', phase: 'Explore', agentType: 'Explore', ...SCOUT }
)

// ===================== 2. GENERATE (round 1) =====================
phase('Generate')
const LENSES = [
  { key: 'creative', label: 'gen:creative', role: `a CREATIVE PROGRAMMER lens. Generate inventive, original ideas -- features, agent capabilities, DX wins, novel uses of the knowledge layers, surprising combinations. Favor imagination and delight.` },
  { key: 'bi',       label: 'gen:bi-analyst', role: `a PROFESSIONAL BI ANALYST lens (15+ yrs retail). Generate ideas that increase ANALYTICAL VALUE -- KPI/metric coverage, decision-support, forecasting, anomaly/exception surfacing, business-question coverage, things a real merchandiser/finance owner needs.` },
  { key: 'technical',label: 'gen:technical', role: `a PROFESSIONAL TECHNICAL ARCHITECT lens. Generate ideas that strengthen the system -- architecture, testing/CI gates, performance, the router/two-hop contract, knowledge-layer tooling, drift/reconciliation, adapter design, observability, agent-eval harnesses. Buildable in-repo.` },
]
function genPrompt(role, extra='') {
  return `You are ${role}\nGenerate 6-8 ideas for Seshat BI. Each MUST respect the hard principles (no executor, no gate bypass, generic-only, no fabricated confidence). Mix NOW and HORIZON. ${extra}\n\n=== REPO MAP ===\n${explore}`
}
const round1 = await parallel(LENSES.map(l => () =>
  agent(genPrompt(l.role), { label: `${l.label}:r1`, phase: 'Generate', schema: IDEA_SCHEMA, ...SCOUT })
    .then(r => r ? { ...r, _key: l.key } : null)
))

// ===================== 3. CROSS-POLLINATE =====================
phase('Cross-pollinate')
const round1Json = JSON.stringify(round1.filter(Boolean).map(r => ({ lens: r.lens || r._key, ideas: r.ideas })), null, 2)
const crossRound = await parallel(LENSES.map(l => () =>
  agent(
    genPrompt(l.role,
      `You have now SEEN what the other two lenses proposed (below). React to them: combine a strong idea from another lens with your own perspective, fill a gap they left, or push a half-idea further. Generate 3-5 NEW cross-disciplinary ideas (do NOT repeat ideas already listed). The best ideas live at the seams between disciplines.\n\n=== ALL ROUND-1 IDEAS ===\n${round1Json}`),
    { label: `${l.label}:cross`, phase: 'Cross-pollinate', schema: IDEA_SCHEMA, ...SCOUT }
  ).then(r => r ? { ...r, _key: l.key } : null)
))

// ===================== 4. COMPLETENESS CRITIC -> targeted pass =====================
phase('Completeness')
const sofar = [...round1, ...crossRound].filter(Boolean)
const sofarJson = JSON.stringify(sofar.map(r => ({ lens: r.lens || r._key, ideas: (r.ideas||[]).map(i => i.title) })), null, 2)
const gaps = await agent(
  `You are a COMPLETENESS CRITIC. Below are all idea TITLES generated so far for Seshat BI, plus the repo map. Your job is to find what's MISSING -- readiness stages with few ideas, repo gaps/tensions nobody addressed, idea TYPES underrepresented (e.g. all features and no DX, or all technical and no business value), and obvious adjacent ideas no lens reached. List 5-10 specific missing angles as short prompts ("nobody proposed anything for X / for the Y gap"). Do not generate full ideas -- just name the blind spots precisely.\n\n=== REPO MAP ===\n${explore}\n\n=== IDEA TITLES SO FAR ===\n${sofarJson}`,
  { label: 'critic:gaps', phase: 'Completeness', ...SCOUT }
)
// one targeted fill pass aimed at the named gaps
const fillRound = await parallel(LENSES.map(l => () =>
  agent(genPrompt(l.role,
    `A completeness critic identified these BLIND SPOTS in the ideas generated so far. From YOUR lens, generate 2-4 ideas that specifically fill the gaps most relevant to you (do not repeat existing ideas).\n\n=== BLIND SPOTS ===\n${gaps}`),
    { label: `${l.label}:fill`, phase: 'Completeness', schema: IDEA_SCHEMA, ...SCOUT }
  ).then(r => r ? { ...r, _key: l.key } : null)
))

const allIdeas = [...round1, ...crossRound, ...fillRound].filter(Boolean).flatMap(r =>
  (r.ideas || []).map(i => ({ ...i, source_lens: r.lens || r._key }))
)

// ===================== 5. SYNTHESIZE =====================
phase('Synthesize')
const synthesis = await agent(
  `You are the SYNTHESIZER. Many ideas were generated across three lenses over three rounds
(initial, cross-pollination, gap-fill). Merge into ONE clean candidate set.
- DEDUPE near-duplicates (keep the strongest framing; note where lenses/rounds converged -- convergence is a strength signal).
- GROUP into themes.
- Keep each idea's title, pitch, horizon, why_it_fits, rough_shape, source_lens(es).
- Do NOT score (the reviewer does). Do NOT invent new ideas; only merge/clarify.
- Flag any idea that might violate a hard principle (the reviewer rules).

=== REPO MAP ===\n${explore}\n\n=== ALL RAW IDEAS (JSON) ===\n${JSON.stringify(allIdeas, null, 2)}

Output a clean candidate list grouped by theme, each idea with its fields + source lens(es)
+ a convergence note where applicable.`,
  { label: 'synthesize:merge', phase: 'Synthesize', ...LEAD }
)

// ===================== 6. ADVERSARIAL VERIFY (top candidates) =====================
phase('Verify')
// A skeptic stress-tests the synthesized set for feasibility/eligibility traps BEFORE final scoring.
const verify = await agent(
  `You are an ADVERSARIAL SKEPTIC. For the synthesized candidate set below, try to KILL the most
attractive-looking ideas. For each idea that looks like a likely ADOPT (high apparent value +
seems feasible), attempt to refute it: does it secretly violate a hard principle? does it
duplicate a shipped feature? is the "feasible" framing hiding a missing dependency (a gold
source, a runtime consumer, a human ruling)? would it quietly turn a reasoning layer into an
executor or a stats engine? Default to skeptical: if an idea can't survive a hard look, say so.
Output, per challenged idea: title, the strongest objection, and a survives/weakened/killed call
with one line of why. Ideas you don't challenge are presumed fine -- only spend effort on the
tempting ones.

=== SYNTHESIZED CANDIDATES ===\n${synthesis}`,
  { label: 'verify:skeptic', phase: 'Verify', ...SCOUT }
)

// ===================== 7. EXTERNAL REVIEW (score + gate) =====================
phase('Review')
const REVIEW_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['scored_ideas', 'summary'],
  properties: {
    summary: { type: 'string' },
    scored_ideas: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'horizon', 'eligible', 'consistency', 'value_score', 'feasibility_score', 'verdict', 'rationale'],
        properties: {
          title: { type: 'string' },
          horizon: { type: 'string', enum: ['NOW', 'HORIZON'] },
          eligible: { type: 'boolean' },
          consistency: { type: 'string', enum: ['consistent', 'minor-tension', 'conflict'] },
          value_score: { type: 'integer', minimum: 1, maximum: 10 },
          feasibility_score: { type: 'integer', minimum: 1, maximum: 10 },
          verdict: { type: 'string', enum: ['ADOPT', 'CONSIDER', 'PARK', 'REJECT'] },
          rationale: { type: 'string' },
          survived_verification: { type: 'string', enum: ['survived', 'weakened', 'killed', 'not-challenged'], description: 'how it fared against the adversarial skeptic' },
          first_step: { type: 'string' },
        },
      },
    },
  },
}
const review = await agent(
  `You are the EXTERNAL REVIEWER -- independent, skeptical, default to caution. Score the
synthesized idea set for Seshat BI. You also have an ADVERSARIAL SKEPTIC's challenges -- weigh
them: an idea the skeptic KILLED should not be ADOPT; one WEAKENED should drop in feasibility.

For EACH idea: eligible (respects ALL hard principles? name the violated one if not);
consistency (consistent / minor-tension / conflict with shipped features); value_score &
feasibility_score (1-10); survived_verification (survived/weakened/killed/not-challenged);
verdict (ADOPT / CONSIDER / PARK / REJECT); first_step for ADOPT/CONSIDER. Reward genuine
extension; penalize restating what's shipped. Mark INELIGIBLE ideas, don't soften them.

Remember: this is a triage opinion for an IDEA BANK, not a build decision.

=== REPO MAP ===\n${explore}
=== SYNTHESIZED CANDIDATES ===\n${synthesis}
=== ADVERSARIAL SKEPTIC'S CHALLENGES ===\n${verify}`,
  { label: 'review:score-and-gate', phase: 'Review', schema: REVIEW_SCHEMA, ...LEAD }
)

// ===================== 8. RENDER (pure JS, orchestrator writes) =====================
// Deterministic output: the workflow does NOT write the file (matching the repo's
// only sibling, speckit-finish-chain, where all writes are agent-mediated and the
// top-level script writes nothing). It returns backlog_markdown + backlog_path; the
// ORCHESTRATOR performs the Write. Same review data + same args -> byte-stable string.
phase('Render')
const BACKLOG_PATH = 'docs/roadmap/idea-backlog.md'

// ASCII normalization of the authored backlog (default on, Principle IX). This single
// line is the ONLY place a literal Unicode glyph is allowed in this file: it is the
// search set the normalizer strips (em-dash, en-dash, rightwards arrow, middle dot).
// Everything the engine WRITES to docs/roadmap/idea-backlog.md passes through norm()
// and is proven ASCII; .claude/workflows scripts are not governed content artifacts.
const U_EMDASH = '—', U_ENDASH = '–', U_ARROW = '→', U_MIDDOT = '·'
function toAscii(s) {
  if (typeof s !== 'string') return ''
  return s.split(U_EMDASH).join('--').split(U_ENDASH).join('--')
          .split(U_ARROW).join('->').split(U_MIDDOT).join('-')
}
const norm = ASCII ? toAscii : (s => (typeof s === 'string' ? s : ''))

// Counts are pure JS arithmetic over the structured review array -- never narrated
// by an agent (the verdict/horizon enums are closed and total, so counts are total).
function tally(ideas) {
  const v = { ADOPT: 0, CONSIDER: 0, PARK: 0, REJECT: 0 }
  const h = { NOW: 0, HORIZON: 0 }
  for (const i of ideas) {
    if (i.verdict in v) v[i.verdict]++
    if (i.horizon in h) h[i.horizon]++
  }
  return { v, h }
}

// One idea -> its markdown block. Mirrors the existing idea-backlog.md per-idea shape:
//   ### <title>
//   `<horizon>` - **V<n> / F<n>** - consistency: <c> - <eligibility tag>
//   **Why this verdict:** <rationale>
//   **Panel dissent:** <dissent>        (only if present -- reserved for PR5)
//   **First step:** <first_step or 'None.'>
function renderIdea(i) {
  const eligTag = i.eligible === false
    ? '**INELIGIBLE -- violates a hard principle**'
    : 'respects principles'
  const meta = `\`${i.horizon}\` - **V${i.value_score} / F${i.feasibility_score}** - consistency: ${norm(i.consistency)} - ${eligTag}`
  const lines = [
    `### ${norm(i.title)}`,
    '',
    meta,
    '',
    `**Why this verdict:** ${norm(i.rationale)}`,
  ]
  if (i.dissent && String(i.dissent).trim()) {  // reserved for PR5 panel; '' today
    lines.push('', `**Panel dissent:** ${norm(i.dissent)}`)
  }
  const firstStep = (i.first_step && String(i.first_step).trim()) || 'None.'
  lines.push('', `**First step:** ${norm(firstStep)}`)
  return lines.join('\n')
}

// renderBacklog: deterministic. `prior` is RESERVED (ignored) until PR4 (cross-run
// memory) populates a SHIPPED/SETTLED appendix; matching prior ideas is a Memory
// concern -- title is NOT a reliable cross-run join key, so no matcher is built here.
function renderBacklog(review, opts) {
  const ideas = (review && Array.isArray(review.scored_ideas)) ? review.scored_ideas : []
  const { v, h } = tally(ideas)
  const dateLine = opts.date ? `Generated on ${opts.date}.` : 'Generated on (date pending).'
  const rawN = opts.rawCount, scoredM = ideas.length, rounds = opts.rounds

  const HEADER = [
    '# Seshat BI -- Idea Bank',
    '',
    '> **This is a future-idea bank, not a roadmap and not a commitment.** Nothing here is',
    '> planned, scheduled, or approved. It is exploratory brainstorming output to browse for',
    '> inspiration. The authoritative roadmap is `docs/roadmap/roadmap.md` (F-numbered features);',
    '> the "verdicts" and scores below are an automated reviewer\'s opinion to help triage *what',
    '> might be worth a closer look later* -- they do not promote anything into the roadmap. An',
    '> idea moves forward only through the normal spec/feature process, with a human decision.',
    '',
    `_Generated by the \`idea-engine\` workflow. ${dateLine} Re-running regenerates this file; treat each run as a fresh snapshot of ideas, not an evolving plan._`,
    '',
    // Honest funnel: raw and scored are both real JS counts; the sentence does not
    // imply a measured conversion between them.
    `**${scoredM} ideas scored** (generated across ${rounds} rounds; raw pre-dedupe ${rawN}). Verdicts: ADOPT ${v.ADOPT}, CONSIDER ${v.CONSIDER}, PARK ${v.PARK}, REJECT ${v.REJECT}. Horizon: NOW ${h.NOW}, HORIZON ${h.HORIZON}.`,
  ].join('\n')

  const PORTFOLIO = ['## Reviewer portfolio verdict', '', `> ${norm((review && review.summary) || '')}`].join('\n')

  const LEGEND = [
    '## Legend',
    '',
    '- **Verdict** (reviewer\'s *triage opinion only* -- not a decision to build) -- ADOPT (worth a closer look first; eligible, consistent, high value) - CONSIDER (interesting; needs a decision or dependency) - PARK (horizon / later) - REJECT (ineligible or conflicts -- kept for the record).',
    '- **Horizon** -- `NOW` (fits the repo today) - `HORIZON` (future vision).',
    '- **Eligibility** -- respects all hard principles, or violates one (named in the rationale).',
    '- **V / F** -- value / feasibility (1-10), reviewer-assigned.',
  ].join('\n')

  // Sections in fixed order; preserve input order within each (no sort, no RNG).
  // Empty sections are omitted.
  const SECTIONS = ['ADOPT', 'CONSIDER', 'PARK', 'REJECT'].map(verdict => {
    const group = ideas.filter(i => i.verdict === verdict)
    if (!group.length) return null
    return [`## ${verdict}`, '', group.map(renderIdea).join('\n\n')].join('\n')
  }).filter(Boolean)

  return [HEADER, PORTFOLIO, LEGEND, ...SECTIONS].join('\n\n') + '\n'
}

const rounds_done = round1.filter(Boolean).length + crossRound.filter(Boolean).length + fillRound.filter(Boolean).length
const backlog_markdown = renderBacklog(review, {
  date: DATE,
  ascii: ASCII,
  rawCount: allIdeas.length,
  rounds: 3,                 // r1 + cross + fill generation rounds
  prior: null,               // RESERVED for PR4 (cross-run memory)
})

return {
  explore_map: explore,
  gaps_found: gaps,
  synthesis,
  adversarial_verify: verify,
  review,
  raw_idea_count: allIdeas.length,
  rounds: { r1: round1.filter(Boolean).length, cross: crossRound.filter(Boolean).length, fill: fillRound.filter(Boolean).length },
  focus: FOCUS,
  // Deterministic output: orchestrator writes backlog_markdown to backlog_path.
  backlog_markdown,
  backlog_path: BACKLOG_PATH,
}
