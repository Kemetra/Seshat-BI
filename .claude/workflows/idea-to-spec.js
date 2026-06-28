export const meta = {
  name: 'idea-to-spec',
  description: 'PLANNING bridge: take ONE human-chosen idea from docs/roadmap/idea-backlog.md and drive it through the existing Spec-Kit chain (branch -> specify -> advisor-driven clarify -> plan -> tasks -> read-only analyze -> a single adversarial plan-review skeptic) inside an isolated git worktree, then STOP at a ratify ledger. It DEFINES and CHECKS; it never APPROVES, never implements, never touches main. Ratification is a human edit the workflow is structurally forbidden to make. A thin mirror of speckit-finish-chain.js that adds one front stage (locate + ground the idea) and one back stage (the ratify ledger). One idea per run.',
  whenToUse: 'After the idea-engine produces a bank and a human has CHOSEN one ADOPT idea to pursue. Pass the idea TITLE (string) or { title, feature_name?, date?, allow_ineligible? }. Output is a ratifiable spec dir on a worktree branch + a ratify ledger -- never a built feature, never a merge.',
  phases: [
    { title: 'Pre-flight' },                                                           // in-script, no agent
    { title: 'Ground',       detail: 'read-only: confirm the idea\'s seams + map its roadmap stage', model: 'opus' },
    { title: 'Plan (per-idea, isolated)', detail: 'one worktree agent: branch -> specify -> clarify -> plan -> tasks -> analyze -> adversarial review', model: 'opus' },
    { title: 'Ratify ledger', detail: 'read-only assembler: present the ledger and STOP at the human gate', model: 'opus' },
  ],
}

const REPO = 'C:/Users/Shaaban/Documents/GitHub/Seshat_BI'
const BACKLOG_PATH = 'docs/roadmap/idea-backlog.md'

// ---- ASCII fold (Principle IX) -------------------------------------------------
// The backlog is known-dirty (it contains arrows, middle dots, em/en-dashes, smart
// quotes). The chosen title flows verbatim into the spec's Input line and the ratify
// ledger -- both AUTHORED artifacts that must be ASCII + UTF-8 no BOM. Fold before it can
// land anywhere tracked. The FOLD table's search chars are the only non-ASCII in this
// file; everything the workflow AUTHORS is folded through them to ASCII.
const FOLD = [
  ['—', '--'], ['–', '--'],   // em / en dash
  ['→', '->'], ['·', '-'],     // rightwards arrow / middle dot
  ['‘', "'"], ['’', "'"],     // smart single quotes
  ['“', '"'], ['”', '"'],     // smart double quotes
  ['…', '...'],                     // ellipsis
]
function asciiFold(s) {
  if (typeof s !== 'string') return ''
  let out = s
  for (const [from, to] of FOLD) out = out.split(from).join(to)
  return out
}

// ---- args boundary (one coerce, the only place args are normalized) ------------
// Accepted: a bare idea-TITLE string | a JSON-encoded string of the object | the object
//   { title, feature_name?, date?, allow_ineligible? }.
// A bare string is the natural default (the human pastes a title from the backlog). Only a
// leading '{' is treated as JSON, so a '['-prefixed title is still a title, not an array.
function coerce(a) {
  let v = a
  if (typeof v === 'string') {
    const t = v.trim()
    // bare-string fast path -- fold to ASCII here too (this is the MOST COMMON input; an
    // early return without folding would leak a smart-dash/arrow into the authored spec).
    if (t && !t.startsWith('{')) return { value: { title: asciiFold(t), feature_name: null, date: null, allow_ineligible: false } }
    try { v = JSON.parse(t) } catch (e) { return { error: `args was a string that did not JSON.parse: ${String(e)}` } }
  }
  if (typeof v === 'string') v = { title: v }                     // JSON that decoded to a bare string
  if (!v || typeof v !== 'object' || Array.isArray(v))            // arrays are finish-chain's shape, not ours
    return { error: 'pass an idea TITLE string, or { title, feature_name?, date?, allow_ineligible? }' }
  if (typeof v.title !== 'string' || !v.title.trim())
    return { error: 'title is required (the idea title from docs/roadmap/idea-backlog.md)' }
  return { value: {
    title: asciiFold(v.title.trim()),
    feature_name: typeof v.feature_name === 'string' ? asciiFold(v.feature_name.trim()) : null,
    date: (typeof v.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v.date)) ? v.date : null,
    allow_ineligible: v.allow_ineligible === true,
  } }
}

const c = coerce(args)
if (c.error) { log(`idea-to-spec: ${c.error}`); return { error: c.error } }
const INPUT = c.value
const DATE_NOTE = INPUT.date
  ? `Use "### Session ${INPUT.date}" as the Clarifications session heading.`
  : `No date supplied; use "### Session (date pending)" and note in the ledger that the operator must fill the date -- do NOT invent one (scripts cannot call new Date()).`

// ===================== STAGE 0: PRE-FLIGHT + LOCATE ===============================
// Pure-JS parse + match. Workflow scripts have no fs, so a single minimal read-only agent
// fetches the committed backlog text; ALL parsing, matching, and the refuse matrix are
// deterministic JS over that text -- the agent reads, the script decides. Refusals fire
// before the expensive worktree agent. The committed file is the durable artifact; the
// A1/F7 id is an EPHEMERAL per-run label (the backlog header says the file is regenerated
// each run), so the TITLE is the key and the id is only a secondary convenience match.
phase('Pre-flight')

const READ_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['found', 'content'],
  properties: {
    found: { type: 'boolean', description: 'false if docs/roadmap/idea-backlog.md does not exist' },
    content: { type: 'string', description: 'the FULL verbatim file content, or "" if not found' },
  },
}
const backlogRead = await agent(
  `Read the file ${REPO}/${BACKLOG_PATH} and return its FULL verbatim content in 'content' ` +
  `(found:true). If the file does not exist, return found:false and content:"". Do NOT summarize, ` +
  `truncate, reformat, or interpret -- return the raw bytes as text. Read nothing else.`,
  { label: 'preflight:read-backlog', phase: 'Pre-flight', schema: READ_SCHEMA, model: 'opus', effort: 'low' }
)
if (!backlogRead || !backlogRead.found || !backlogRead.content) {
  const reason = `${BACKLOG_PATH} not found or empty -- run the idea-engine first to produce a bank.`
  log(`idea-to-spec: ${reason}`)
  return { outcome: 'BLOCKED', blocked: { status: 'idea-not-found', stage_failed: 'pre-flight', title: INPUT.title, reason, evidence: [], human_options: ['Run Workflow({name:"idea-engine"}) to generate docs/roadmap/idea-backlog.md, then re-invoke with the chosen idea title.'] } }
}

function parseBacklog(raw) {
  const ideas = []
  let section = null
  for (const line of raw.split(/\r?\n/)) {
    const sec = line.match(/^##\s+(ADOPT|CONSIDER|PARK|REJECT)\b/)
    if (sec) { section = sec[1]; continue }
    const h = line.match(/^###\s+([A-Z]+\d+)\.\s+(.+?)\s*$/)   // "### A1. Title ..."
    if (h && section) {
      ideas.push({
        id: h[1],                                   // ephemeral label, not a stable key
        title_raw: h[2],                            // verbatim, for the ledger echo
        title_fold: asciiFold(h[2]).toLowerCase(),  // folded + lowered, for matching
        section,                                    // ADOPT | CONSIDER | PARK | REJECT
        eligible: section !== 'REJECT',             // REJECT = ineligible to plan w/o override
      })
    }
  }
  return ideas
}

// Match priority: exact (folded) -> id -> unique substring. NEVER silently pick among
// several -- ambiguity is the human's call (the constitution forbids silent judgment).
function locate(ideas, input) {
  const needle = asciiFold(input.title).toLowerCase().trim()
  const exact = ideas.filter(i => i.title_fold === needle)
  if (exact.length === 1) return { match: exact[0] }
  if (exact.length > 1) return { ambiguous: exact }
  const byId = ideas.filter(i => i.id.toLowerCase() === needle)
  if (byId.length === 1) return { match: byId[0] }
  const sub = ideas.filter(i => i.title_fold.includes(needle))
  if (sub.length === 1) return { match: sub[0] }
  if (sub.length > 1) return { ambiguous: sub }
  const toks = new Set(needle.split(/\s+/).filter(Boolean))   // closest-3 by token overlap
  const scored = ideas.map(i => ({ i, score: i.title_fold.split(/\s+/).filter(t => toks.has(t)).length }))
    .sort((a, b) => b.score - a.score)
  return { notFound: scored.slice(0, 3).map(s => `${s.i.id}. ${s.i.title_raw}`) }
}

const ideas = parseBacklog(backlogRead.content)
const loc = locate(ideas, INPUT)

// --- the refuse matrix (deterministic; refusals cost zero further agents) ---
function blocked(status, reason, evidence, options) {
  return { outcome: 'BLOCKED', blocked: { status, stage_failed: 'pre-flight', title: INPUT.title, reason, evidence: evidence || [], human_options: options || [] } }
}
if (loc.notFound) {
  log(`idea-to-spec: idea not found -- "${INPUT.title}"`)
  return blocked('idea-not-found', `No idea in the backlog matched "${INPUT.title}".`, loc.notFound,
    ['Re-invoke with one of the closest titles above, exactly as written in the backlog.'])
}
if (loc.ambiguous) {
  const ev = loc.ambiguous.map(i => `${i.id}. ${i.title_raw}`)
  log(`idea-to-spec: idea ambiguous -- ${ev.length} matches`)
  return blocked('idea-ambiguous', `"${INPUT.title}" matched ${ev.length} ideas; refusing to guess which you meant.`, ev,
    ['Re-invoke with the full exact title (or the heading id like "A1") to disambiguate.'])
}
const chosen = loc.match
if (!chosen.eligible && !INPUT.allow_ineligible) {
  log(`idea-to-spec: idea ineligible -- ${chosen.id} (${chosen.section})`)
  return blocked('ineligible', `"${chosen.id}. ${chosen.title_raw}" is in the ${chosen.section} section -- the bank judged it ineligible (it crosses a hard principle). You cannot ratify a hard-principle violation.`,
    [`${chosen.id}. ${chosen.title_raw} [${chosen.section}]`],
    ['If you intend to pursue it anyway, re-invoke with { title, allow_ineligible: true } -- the violation will be recorded, never cleared, and stamped into the spec as BLOCKED.'])
}
const forced_ineligible = !chosen.eligible && INPUT.allow_ineligible
// WARN-PROCEED: CONSIDER/PARK are eligible but lower-triaged -- proceed, flag the ledger.
const bank_warning = (chosen.section === 'CONSIDER' || chosen.section === 'PARK')
  ? `the bank triaged this ${chosen.section}, not ADOPT -- you are deliberately overriding its ranking (the bank is a triage opinion, never a commitment)`
  : ''

// ===================== STAGE 1: GROUND (read-only) ================================
// Confirm the idea's named seams against the live repo so the spec is concrete, not vibes.
// Read-only, no worktree (writes nothing). Fabricate nothing -- a missing file is a finding.
// Resolve no Principle-V call; surface it to open_for_human. If unmapped, push "which
// stage?" to open_for_human rather than assert a stage.
phase('Ground')
const GROUNDING_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['idea_title', 'roadmap_stage', 'f_number', 'touches', 'existing_seams', 'missing_or_deferred', 'constraining_principles', 'open_for_human', 'c086_risk', 'grounding_notes'],
  properties: {
    idea_title: { type: 'string' },
    f_number: { type: 'string', description: 'F-number from roadmap.md, or "none"' },
    roadmap_stage: { type: 'string', description: 'readiness stage advanced; MUST be "unmapped" when f_number is "none" -- never a guessed stage' },
    touches: { type: 'array', items: { type: 'string' } },
    existing_seams: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['ref', 'confirmed', 'note'], properties: { ref: { type: 'string' }, confirmed: { type: 'boolean' }, note: { type: 'string' } } } },
    missing_or_deferred: { type: 'array', items: { type: 'string' }, description: 'named deps that do NOT exist -> blocking assumptions' },
    constraining_principles: { type: 'array', items: { type: 'string' } },
    open_for_human: { type: 'array', items: { type: 'string' }, description: 'Principle-V calls surfaced, never answered' },
    c086_risk: { type: 'string', description: 'how a C086 specific could leak into a generic artifact; "none" if N/A' },
    grounding_notes: { type: 'string' },
  },
}
const grounding = await agent(
  `You are the GROUNDER for a Seshat BI planning run. Read the real repo under ${REPO} (READ-ONLY; ` +
  `you write nothing, you execute nothing). Confirm the chosen idea's named seams so the spec it seeds ` +
  `is concrete, not hand-wavy.\n\n` +
  `CHOSEN IDEA: ${chosen.id}. ${asciiFold(chosen.title_raw)}  [bank verdict: ${chosen.section}]\n\n` +
  `DO:\n` +
  `- Read the files/symbols the idea implies and record existing_seams (ref + confirmed:true/false + note). ` +
  `A reference that does NOT exist as described is confirmed:false and goes in missing_or_deferred -- a ` +
  `blocking assumption, never glossed over.\n` +
  `- Map the idea to its roadmap.md F-number + readiness stage. If you cannot find an F-number, set ` +
  `f_number:"none" AND roadmap_stage:"unmapped" AND push "which readiness stage does this advance?" to ` +
  `open_for_human -- do NOT guess a stage.\n` +
  `- List constraining_principles (the constitution principles that bound this idea, in your words).\n` +
  `- Surface (NEVER answer) any Principle-V judgment call -- grain/uniqueness, PII publish-safety, ` +
  `business rollup/segment, product identity -- into open_for_human.\n` +
  `- Note c086_risk: how a pharmacy/C086 specific could leak into what must stay generic ("none" if N/A).\n` +
  `Fabricate nothing. ASCII only (-- and ->). This grounding seeds the spec; getting it wrong poisons ` +
  `the whole plan, so prefer "confirmed:false" over an optimistic guess.`,
  { label: `ground:${chosen.id}`, phase: 'Ground', schema: GROUNDING_SCHEMA, model: 'opus', effort: 'high' }
)

// ===================== STAGE 2-7: PLAN (one worktree agent owns the chain) =========
// branch -> specify -> clarify -> plan -> tasks -> analyze -> adversarial plan-review,
// all inside ONE isolation:'worktree' agent so a single feature-number allocation, one
// .specify/feature.json, and one commit history hold (finish-chain's pattern). Keeping
// branch + specify in one agent is the fix for the 041 double-numbering race.
phase('Plan (per-idea, isolated)')
const PLAN_RESULT = {
  type: 'object', additionalProperties: false,
  required: ['idea_title', 'bank_verdict', 'forced_ineligible', 'feature', 'branch', 'spec_dir', 'status', 'stages_done', 'clarifications', 'open_for_human', 'analyze_verdict', 'analyze_critical', 'analyze_high', 'plan_review_verdict', 'plan_review_findings', 'blocked_reason', 'notes'],
  properties: {
    idea_title: { type: 'string' },
    bank_verdict: { type: 'string', enum: ['ADOPT', 'CONSIDER', 'PARK', 'REJECT', 'SHIPPED'] },
    forced_ineligible: { type: 'boolean' },
    feature: { type: 'string', description: 'NNN-kebab from speckit-git-feature' },
    branch: { type: 'string', description: 'worktree branch; NEVER main' },
    spec_dir: { type: 'string' },
    status: { type: 'string', enum: ['drafted', 'partial', 'blocked', 'failed'] },
    stages_done: { type: 'array', items: { type: 'string', enum: ['specify', 'clarify', 'plan', 'tasks', 'analyze', 'plan-review'] } },
    clarifications: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['question', 'recommended_answer', 'reasoning', 'reversible'], properties: { question: { type: 'string' }, recommended_answer: { type: 'string' }, reasoning: { type: 'string' }, reversible: { type: 'string', enum: ['easy', 'costly', 'irreversible'] } } } },
    open_for_human: { type: 'array', items: { type: 'string' }, description: 'Principle-V questions REFUSED; recorded in spec.md ## Clarifications, never answered' },
    analyze_verdict: { type: 'string', enum: ['clean', 'findings', 'not-run'] },
    analyze_critical: { type: 'number' },
    analyze_high: { type: 'number' },
    plan_review_verdict: { type: 'string', enum: ['PASS', 'PASS-WITH-NOTES', 'BLOCKED', 'not-run'] },
    plan_review_findings: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['axis', 'finding', 'severity', 'fix'], properties: { axis: { type: 'string', enum: ['hidden-principle-violation', 'assumes-deferred-capability', 'c086-leak', 'fabricated-confidence', 'over-scope'] }, finding: { type: 'string' }, severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] }, fix: { type: 'string' } } } },
    blocked_reason: { type: 'string', description: '"" unless blocked/failed/partial; non-empty when any stage did not run' },
    notes: { type: 'string' },
  },
}

const kebabHint = INPUT.feature_name || asciiFold(chosen.title_raw).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').split('-').slice(0, 5).join('-')

const plan = await agent(
  `You are PLANNING one chosen Seshat BI idea into a RATIFIABLE spec, in an ISOLATED git worktree ` +
  `(you were launched with worktree isolation -- your own checkout + your own .specify/feature.json). ` +
  `You DEFINE and CHECK; you NEVER approve, never implement, never merge, never push, never touch main. ` +
  `Repo: Seshat_BI.\n\n` +
  `CHOSEN IDEA: ${chosen.id}. ${asciiFold(chosen.title_raw)}  [bank verdict: ${chosen.section}]\n` +
  (forced_ineligible ? `FORCED INELIGIBLE: the human used allow_ineligible to proceed past the bank's ineligible verdict. You MUST stamp "**Status**: Draft -- BLOCKED: ineligible per bank (${chosen.section}); proceeding under explicit human override" into the spec front-matter and surface the violation in open_for_human. NEVER self-clear it.\n` : '') +
  `\n=== GROUNDING (from the read-only grounder; the seed for the spec) ===\n${JSON.stringify(grounding, null, 2)}\n\n` +
  `RUN THESE STAGES IN ORDER, committing on THIS branch after each that writes a file; SKIP any stage ` +
  `whose output already exists (resume-safe), counting it in stages_done:\n\n` +
  `STAGE 2 -- SPECIFY (this creates the branch via its hook -- do NOT create one yourself): run ` +
  `/speckit-specify to author spec.md from the grounding seed. IMPORTANT (repo-specific): ` +
  `.specify/extensions.yml enables a NON-OPTIONAL before_specify hook (speckit.git.feature) with ` +
  `auto_execute_hooks:true, so /speckit-specify ITSELF creates + switches to the numbered feature ` +
  `branch (next is 041+, auto-numbered by scanning specs+branches for max+1) BEFORE it writes the ` +
  `spec, then creates specs/NNN-*/ + .specify/feature.json. Do NOT run the feature script separately ` +
  `and do NOT pre-create the dir -- a second manual branch would split the artifacts across two ` +
  `branches and point the ratify handoff at the wrong worktree. Pass the short name "${kebabHint}" to ` +
  `the hook (keep the path short; Windows 260-char rule). If branch/spec creation fails (e.g. name ` +
  `collision, hook non-zero), STOP: return status:'failed', blocked_reason with the error, write no ` +
  `further artifacts. AFTER specify returns, record the ACTUAL feature (NNN-kebab) + branch it created ` +
  `(read .specify/feature.json / the current branch -- do not assume; the hook owns the number). Run ` +
  `NON-INTERACTIVELY: make informed guesses for ordinary gaps but NEVER block on a prompt and NEVER ` +
  `answer a Principle-V [NEEDS CLARIFICATION] marker (grain / PII / rollup / identity) -- leave those ` +
  `markers in place for stage 3. Put the idea title verbatim (ASCII) in the spec's Input line.\n\n` +
  `STAGE 3 -- /speckit-clarify (advisor-driven): for each ambiguity (max 5, highest Impact*Uncertainty ` +
  `first): reason as the advisor against the constitution / readiness spine / RC defaults / the roadmap ` +
  `stage, pick the RECOMMENDED answer, record {question, recommended_answer, reasoning, reversible}, and ` +
  `integrate it into the spec. ${DATE_NOTE} HARD CARVE-OUT (Principle V -- do NOT answer; record to ` +
  `open_for_human and into the spec's ## Clarifications block): grain/uniqueness, PII publish-safety, ` +
  `business rollup/segment, product identity. Also harvest any Principle-V markers stage 2 (specify) left in place. ` +
  `If a clarify question is BUILD-BLOCKING (the spec cannot be meaningfully written without the human's ` +
  `ruling), STOP: status:'blocked', blocked_reason:'clarify-principle-v-wall' + the wall question(s) ` +
  `recorded -- do NOT fabricate a spec around the unknown.\n\n` +
  `STAGE 4 -- /speckit-plan then /speckit-tasks (idempotent, skip-if-exists). Stay INSIDE this one idea's ` +
  `first-step scope (YAGNI: add the seam, not the implementation). Do NOT assume any DEFERRED capability ` +
  `exists (F016 Power BI Execution Adapter; F031-F033 spec-only runtimes).\n\n` +
  `STAGE 5 -- /speckit-analyze (READ-ONLY on spec/plan/tasks): run the real cross-artifact consistency ` +
  `pass; capture its full report into analysis.md (the only write it produces -- our repo convention). ` +
  `Record analyze_verdict (clean if 0 critical & 0 high, else findings), analyze_critical, analyze_high.\n\n` +
  `STAGE 6 -- ADVERSARIAL PLAN-REVIEW (your final step; you already own the branch + commit): be a SINGLE ` +
  `default-adverse skeptic over spec/plan/tasks (READ-ONLY -- report fixes, never edit). Check five axes: ` +
  `hidden-principle-violation, assumes-deferred-capability, c086-leak, fabricated-confidence, over-scope. ` +
  `Write your findings to plan-review.md committed on the branch (durable; the handoff reads it). Set ` +
  `plan_review_verdict PASS / PASS-WITH-NOTES / BLOCKED. A draft missing analyze or tasks is automatic ` +
  `BLOCKED. On a CRITICAL you are unsure of, say so in notes -- never retry, never override.\n\n` +
  `COMMIT DISCIPLINE: "docs(NNN): specify" after stage 2, "docs(NNN): clarify" after 3, "docs(NNN): ` +
  `plan+tasks" after 4, "docs(NNN): analyze" after 5, "docs(NNN): plan-review" after 6. Never merge/push/` +
  `touch main.\n\n` +
  `CONSTRAINTS (every authored artifact): ASCII + UTF-8 no BOM (-- and ->, no glyphs; rule IX). ` +
  `Generic-only (no C086/pharmacy specifics in a generic artifact; rule 7). No fabricated confidence / ` +
  `readiness score (rule 9). No executor (docs only). Never self-grant a readiness pass.\n\n` +
  `STATUS RULE: status:'drafted' REQUIRES every stage ran AND analyze_verdict != 'not-run' AND ` +
  `plan_review_verdict in {PASS, PASS-WITH-NOTES}. Any missing stage or a BLOCKED review -> status ` +
  `'blocked'/'partial' with a non-empty blocked_reason. A half-spec must NEVER report 'drafted'. The spec ` +
  `front-matter Status stays "**Status**: Draft" -- you are FORBIDDEN to write "Ratified" (only a human ` +
  `does that, after this workflow returns).`,
  { label: `plan:${chosen.id}`, phase: 'Plan (per-idea, isolated)', isolation: 'worktree', schema: PLAN_RESULT, model: 'opus', effort: 'high' }
)

// ===================== STAGE 8: RATIFY LEDGER (read-only assembler; STOPS here) ====
// A non-writing assembler that COLLECTS the prior verdicts into a ledger + a scannable
// summary and STOPS. It performs NO judgment of its own and writes NO ratified value.
// READY_FOR_RATIFY only when the plan truly drafted; otherwise BLOCKED. The word
// "Ratified" can never be produced by this workflow -- only a human edit, after we return.
phase('Ratify ledger')

// Pure-JS gate: the structural guarantee. drafted-AND-clean -> READY_FOR_RATIFY; anything
// short -> BLOCKED. Computed in code, never by the agent (it cannot soften this).
//  - analyze must be CLEAN (zero critical AND zero high) -- a spec analyze already flagged
//    unsafe must never reach a ratify path. ('findings' or any critical/high => BLOCKED.)
//  - a FORCED-INELIGIBLE idea (operator used allow_ineligible on a REJECT) can NEVER be
//    ratify-ready: it is the exact hard-principle violation pre-flight says is unratifiable.
//    The override let the run PROCEED to produce an auditable draft; it never clears the gate.
const analyzeClean = plan
  && plan.analyze_verdict === 'clean'
  && (plan.analyze_critical || 0) === 0
  && (plan.analyze_high || 0) === 0
const planOk = plan
  && !forced_ineligible
  && plan.status === 'drafted'
  && analyzeClean
  && (plan.plan_review_verdict === 'PASS' || plan.plan_review_verdict === 'PASS-WITH-NOTES')
const gateOutcome = planOk ? 'READY_FOR_RATIFY' : 'BLOCKED'

const RATIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['feature', 'branch', 'spec_dir', 'idea_ref', 'outcome', 'ratify_summary', 'how_to_ratify'],
  properties: {
    feature: { type: 'string' },
    branch: { type: 'string', description: 'NEVER main' },
    spec_dir: { type: 'string' },
    idea_ref: { type: 'object', additionalProperties: false, required: ['id', 'title', 'verdict'], properties: { id: { type: 'string' }, title: { type: 'string' }, verdict: { type: 'string', enum: ['ADOPT', 'CONSIDER', 'PARK', 'REJECT', 'SHIPPED'] } } },
    outcome: { type: 'string', enum: ['READY_FOR_RATIFY', 'BLOCKED'], description: 'the word "Ratified" can NEVER appear here -- the workflow cannot emit it' },
    ratify_summary: { type: 'string', description: 'ASCII markdown; the one-read ratify-or-reject view' },
    how_to_ratify: { type: 'string', description: 'the exact human action that records ratification' },
  },
}
const ledger = await agent(
  `You are the RATIFY-LEDGER assembler for a Seshat BI planning run. You are a NON-WRITING assembler: ` +
  `you read the committed branch files + the plan record below and ARRANGE them into a scannable ` +
  `ratify ledger for a human. You perform NO judgment of your own, you change NO verdict or score, and ` +
  `you NEVER write a "Ratified" value anywhere -- ratification is a human action AFTER this workflow ` +
  `returns. The outcome is FIXED by the orchestrator (given below); do not change it.\n\n` +
  `FIXED OUTCOME: ${gateOutcome}\n` +
  `IDEA: ${chosen.id}. ${asciiFold(chosen.title_raw)}  [bank verdict: ${chosen.section}]` +
  (bank_warning ? `  (WARNING: ${bank_warning})` : '') +
  (forced_ineligible ? `  (FORCED INELIGIBLE per human override -- the violation is recorded, never cleared)` : '') + `\n\n` +
  `=== PLAN RECORD ===\n${JSON.stringify(plan, null, 2)}\n\n` +
  `=== GROUNDING (open_for_human originated partly here) ===\n${JSON.stringify({ open_for_human: grounding && grounding.open_for_human, missing_or_deferred: grounding && grounding.missing_or_deferred }, null, 2)}\n\n` +
  `Build ratify_summary as ASCII markdown ordered so a human reads downward and stops the moment ` +
  `something fails: (1) FROM IDEA (the id+title+bank verdict, explicitly flagged as a TRIAGE opinion -- ` +
  `ratifying THIS spec is a fresh decision, not the bank's); (2) ARTIFACTS present (spec/plan/tasks/` +
  `analysis/plan-review); (3) CLARIFY -- the recommended answers the workflow chose + reasoning; ` +
  `(4) OPEN FOR YOU -- the Principle-V questions the workflow REFUSED to answer (the human must resolve ` +
  `these before ratifying), or "(none)"; (5) ANALYZE verdict; (6) PLAN REVIEW verdict + findings; ` +
  `(7) OUTCOME (${gateOutcome}). If READY_FOR_RATIFY, how_to_ratify lists the exact human steps: resolve ` +
  `every OPEN FOR YOU item in spec.md, flip "**Status**: Draft" to "**Status**: Ratified (<name>, ` +
  `<YYYY-MM-DD>)", commit "docs(${plan && plan.feature ? plan.feature : 'NNN'}): ratify spec" on the ` +
  `branch -- and note the implement workflow refuses the spec until that human Status edit lands. If ` +
  `BLOCKED, how_to_ratify instead states what must be fixed and that NO ratify path is offered yet. ` +
  `ASCII only.`,
  { label: 'ratify-ledger', phase: 'Ratify ledger', schema: RATIFY_SCHEMA, model: 'opus', effort: 'high' }
)

return {
  outcome: gateOutcome,
  idea: { id: chosen.id, title: asciiFold(chosen.title_raw), bank_verdict: chosen.section, forced_ineligible, bank_warning },
  grounding,
  plan,
  ledger,
  // The seam to the implement workflow: a human must flip Status to Ratified on disk before
  // implement will act. This workflow STOPS here -- it cannot and does not advance.
  handoff: {
    spec_dir: plan && plan.spec_dir,
    branch: plan && plan.branch,
    ratified: false,   // ALWAYS false from this workflow -- only a human edit makes it true
    note: 'implement must re-verify on disk: spec dir + 5 artifacts + human-written "Status: Ratified" + resolved Principle-V questions + non-BLOCKED plan-review + mergeable branch. Any failure -> REFUSED.',
  },
}
