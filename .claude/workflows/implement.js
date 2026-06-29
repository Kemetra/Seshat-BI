export const meta = {
  name: 'implement',
  description: 'IMPLEMENT bridge: the 3rd + FINAL stage of idea -> plan -> implement. Consumes a HUMAN-RATIFIED spec dir (spec.md + plan.md + tasks.md + analysis.md + plan-review.md) and drives /speckit-implement task-by-task IN PLACE on the ratified feature-branch worktree (invoke it FROM that worktree -- it does not create or switch worktrees), TDD-gated, then runs the CI gate set (ruff, pytest -m unit, retail check, retail semantic-check) and STOPS at a PR-ready branch a human merges. It fails CLOSED on a disk handoff checklist (H1-H6) before touching anything, and is structurally incapable of merging to main, pushing to main, self-ratifying, building an unratified spec, or faking a test result. The only writes are code + tests + per-task commits on the feature branch. One feature per run.',
  whenToUse: 'After a human has RATIFIED a spec produced by idea-to-spec (the spec.md front-matter says "**Status**: Ratified (<name>, <date>)"). PRECONDITION: invoke from WITHIN the ratified feature-branch worktree (the checkout idea-to-spec left the spec on) -- this workflow does NOT create or switch worktrees; the reader + builder run in the session cwd, so HEAD must already be the feature branch carrying specs/<NNN-kebab>/. Pass the feature "NNN-kebab" (string) or { feature, spec_dir?, branch?, date?, open_draft_pr? }. Output is a PR-ready worktree branch + a PR-readiness ledger -- never a merge, never an approval.',
  phases: [
    { title: 'Pre-flight' },                                                                  // 0a read + 0b JS gate
    { title: 'Build + verify (isolated)', detail: 'one worktree agent: /speckit-implement over tasks.md (TDD), then the CI gate set', model: 'opus' },
    { title: 'PR-ready ledger', detail: 'read-only assembler: present the PR-readiness ledger and STOP at the human PR gate', model: 'opus' },
  ],
}
const S = (...c) => String.fromCharCode(...c)

// Device-portable: never hardcode a machine path. The agents that consume REPO resolve
// the real repo root themselves at runtime (`git rev-parse --show-toplevel`), so this works
// from any device / user / worktree. The literal below is only a human-readable fallback hint.
const REPO = 'the repo root (resolve with `git rev-parse --show-toplevel`)'

// ---- single source of truth (the disk contract this workflow verifies) ---------
// implement.js cannot import idea-to-spec.js (workflow scripts are eval'd in isolation),
// so the contract is the DISK STRING the upstream instructs the human to write and is
// FORBIDDEN to emit itself. These regexes are authored here byte-identically to that
// contract -- two independent verifiers of one disk string, which is what makes the gate
// fail-closed and upstream-bug-proof (not code duplication).
const H3_RATIFIED_RE = /^\s*-?\s*\*\*Status:?\*\*:?\s*Ratified \(.+?,\s*\d{4}-\d{2}-\d{2}\)/m
const H3_DRAFT_RE    = /^\s*-?\s*\*\*Status:?\*\*:?\s*Draft\b/mi
const H3_BLOCKED_RE  = /^\s*-?\s*\*\*Status:?\*\*:?.*\bBLOCKED\b/mi
// H4: a mechanical, deletion-resistant scan for LITERAL open markers in the raw
// ## Clarifications text. We do NOT invent an owner+date resolution grammar (the upstream
// writes free-text), and resolution QUALITY is the human's job at ratification -- H4 only
// fails-closed on a remaining open marker.
// Two alternations: word-like markers carry \b boundaries; the literal "(open)" cannot
// (its parens are non-word chars, so a \b...\(open\)...\b group never matches) -- it is a
// separate boundary-free alternative.
const H4_OPEN_MARKER_RE = /\b(?:OPEN FOR (?:THE )?(?:YOU|HUMAN)|open_for_human|NEEDS CLARIFICATION|unresolved|TBD|TODO)\b|\(open\)/i
const H5_VERDICT_RE  = /^\s*(?:#+\s*)?(?:\*\*)?Verdict(?:\*\*)?\s*:?\s*\**\s*(PASS-WITH-NOTES|PASS|BLOCKED)\b/im

// The ONLY tests permitted to be locally deselected for the Python-3.13 reason. Local is
// 3.12; the package requires >=3.13; this subprocess test spawns a fresh interpreter and
// fails to collect/run locally. It runs GREEN in CI (3.13). A deselect outside this set is
// UNEXPLAINED -> the completion gate treats the run as not-green (never a faked pass).
// (Verified node id: tests/unit/test_metric_drift.py, line 295 -- the subprocess import-
// isolation test; NOT test_never_execute.py as an earlier draft assumed.)
const CI_ONLY_TESTS = [
  'tests/unit/test_metric_drift.py::test_importing_retail_rules_does_not_pull_metric_drift',
]

// ---- ASCII fold (Principle IX) -- folds dirty upstream text + a catch-all -------
const FOLD = [
  ['\u2014', '--'], ['\u2013', '--'], ['\u2015', '--'],
  ['\u2192', '->'], ['\u00b7', '-'], ['\u2022', '-'],
  ['\u2018', "'"], ['\u2019', "'"], ['\u201a', "'"],
  ['\u201c', '"'], ['\u201d', '"'], ['\u201e', '"'],
  ['\u2026', '...'],
  [' ', ' '], [' ', ' '], [' ', ' '],   // nbsp / thin / narrow-nbsp
]
function asciiFold(s) {
  if (typeof s !== 'string') return ''
  let out = s
  for (const [from, to] of FOLD) out = out.split(from).join(to)
  return out.replace(/[^\x00-\x7F]/g, '')   // catch-all: total ASCII guarantee
}

// ---- args boundary -------------------------------------------------------------
// Accepted: a bare feature "NNN-kebab" string | a JSON-encoded object string | the object
//   { feature, spec_dir?, branch?, date?, open_draft_pr? }.
// No new Date() (date is echo-only; H3 reads the date OUT of spec.md). No Math.random().
function norm(v) {
  const feature = String(v.feature).trim().replace(/^feat\//, '')
  return {
    feature,
    spec_dir: (typeof v.spec_dir === 'string' && v.spec_dir.trim()) ? v.spec_dir.trim() : `specs/${feature}`,
    branch: (typeof v.branch === 'string' && v.branch.trim()) ? v.branch.trim() : null,  // null => discover, never assume
    date: (typeof v.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v.date)) ? v.date : null,
    open_draft_pr: v.open_draft_pr === true,   // default false -- conservative; STOP at PR-ready
  }
}
function coerce(a) {
  let v = a
  if (typeof v === 'string') {
    const t = v.trim()
    if (t && !t.startsWith('{')) {
      const feat = t.replace(/^feat\//, '')
      if (!/^\d{3}-[a-z0-9-]+$/.test(feat)) return { error: `bare arg must be a feature \u0022NNN-kebab\u0022 (got \u0022${t}\u0022)` }
      return { value: norm({ feature: feat }) }
    }
    try { v = JSON.parse(t) } catch (e) { return { error: `args was a string that did not JSON.parse: ${String(e)}` } }
  }
  if (!v || typeof v !== 'object' || Array.isArray(v))
    return { error: 'pass a feature "NNN-kebab" string, or { feature, spec_dir?, branch?, date?, open_draft_pr? }' }
  if (typeof v.feature !== 'string' || !/^\d{3}-[a-z0-9-]+$/.test(v.feature.trim()))
    return { error: 'feature must be "NNN-kebab" (e.g. "041-route-registry") -- the value the human ratified' }
  return { value: norm(v) }
}

const c = coerce(args)
if (c.error) { log(`implement: ${c.error}`); return { error: c.error } }
const INPUT = c.value

// ===================== STAGE 0a: READ THE HANDOFF FACTS (read-only agent) =========
// Scripts have no fs, so a minimal read-only agent FETCHES raw bytes + raw git output.
// It is the eyes, never the judge -- it returns facts; pure JS (Stage 0b) decides H1-H6.
phase('Pre-flight')
const ARTIFACTS = ['spec.md', 'plan.md', 'tasks.md', 'analysis.md', 'plan-review.md']
const HANDOFF_FACTS = {
  type: 'object', additionalProperties: false,
  required: ['dir_exists', 'files', 'spec_md_raw', 'clarifications_raw', 'plan_review_verdict_line', 'git', 'status_line_provenance'],
  properties: {
    dir_exists: { type: 'boolean' },
    files: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['name', 'exists', 'bytes', 'committed'],
        properties: {
          name: { type: 'string', enum: ARTIFACTS },
          exists: { type: 'boolean' },
          bytes: { type: 'number' },
          // committed = the file is tracked AND clean on the branch (git ls-files finds it
          // AND git status shows no pending change). The PR ships the COMMITTED branch, so an
          // uncommitted artifact would never reach it (and a dirty one risks being swept into a commit).
          committed: { type: 'boolean' },
        },
      },
    },
    spec_md_raw: { type: 'string', description: 'FULL raw text of spec.md, or "" if missing. JS runs H3/H4 over it.' },
    clarifications_raw: { type: 'string', description: 'raw text of the ## Clarifications section ONLY, verbatim, or "".' },
    plan_review_verdict_line: { type: 'string', description: 'the verbatim "## Verdict" SECTION of plan-review.md (heading through next "## " heading or EOF), or "". Capture the whole section -- the verdict value can sit on the line below the heading.' },
    git: {
      type: 'object', additionalProperties: false,
      required: ['current_branch', 'branch_resolved', 'spec_dir_on_branch', 'origin_main_available', 'ahead', 'behind', 'detached'],
      properties: {
        current_branch: { type: 'string' },
        branch_resolved: { type: 'boolean' },
        spec_dir_on_branch: { type: 'boolean' },
        origin_main_available: { type: 'boolean' },
        ahead: { type: 'number', description: 'commits HEAD ahead of origin/main; -1 if origin unavailable' },
        behind: { type: 'number' },
        detached: { type: 'boolean' },
      },
    },
    status_line_provenance: {
      type: 'object', additionalProperties: false,
      required: ['ratified_line_present', 'last_author_of_status_line', 'introduced_by_human'],
      properties: {
        ratified_line_present: { type: 'boolean' },
        last_author_of_status_line: { type: 'string', description: 'git blame author of the Status line, verbatim; "" if no Ratified line' },
        introduced_by_human: { type: 'boolean', description: 'true if the commit introducing the Ratified line is NOT a workflow/bot identity' },
      },
    },
  },
}
const facts = await agent(
  `You are the HANDOFF READER for a Seshat BI implement run. You FETCH raw facts; you do NOT judge, ` +
  `summarize, interpret \u0022resolved\u0022, or decide pass/fail. Read-only, no writes, no execution beyond the ` +
  `read-only git commands below.\n\n` +
  `FEATURE: ${INPUT.feature}\nSPEC DIR: ${INPUT.spec_dir}\n\n` +
  `Return HANDOFF_FACTS:\n` +
  `- dir_exists: FIRST resolve the repo root with \`git rev-parse --show-toplevel\` (do NOT assume any ` +
  `machine path), then report whether <repo-root>/${INPUT.spec_dir}/ exists on the checked-out branch.\n` +
  `- files: for EACH of ${ARTIFACTS.join(S(44,32))} under the spec dir, {name, exists, bytes, committed}. ` +
  `committed = the file is TRACKED on the branch AND has no pending change: true only if ` +
  `\`git ls-files --error-unmatch <path>\` succeeds AND \`git status --porcelain <path>\` is empty. ` +
  `An uncommitted/dirty artifact must be committed:false (the PR ships the committed branch, so ` +
  `working-tree-only changes would never reach it).\n` +
  `- spec_md_raw: the FULL verbatim text of spec.md (or \u0022\u0022 if missing). Do not truncate.\n` +
  `- clarifications_raw: the verbatim text of ONLY the \u0022## Clarifications\u0022 section of spec.md (or \u0022\u0022).\n` +
  `- plan_review_verdict_line: the verbatim text of the WHOLE "## Verdict" section of plan-review.md ` +
  `(from the "## Verdict" heading to the next "## " heading or end-of-file; "" if none). Capture the ` +
  `SECTION (the verdict value often sits on the line BELOW the heading); return raw text, do NOT ` +
  `interpret or extract the value -- the gate parses it. Do NOT capture only lines containing the word\u0022Verdict\u0022 (or \u0022\u0022).\n` +
  `- git: current_branch (git rev-parse --abbrev-ref HEAD); branch_resolved (true unless detached); ` +
  `spec_dir_on_branch (does ${INPUT.spec_dir}/spec.md exist on the checked-out branch?); ` +
  `origin_main_available (does origin/main resolve?); ahead/behind (git rev-list --count origin/main...HEAD; ` +
  `ahead=-1 if origin/main unavailable); detached (is HEAD detached?).\n` +
  `- status_line_provenance: ratified_line_present (does spec.md contain a \u0022Status: Ratified (...)\u0022 line?); ` +
  `last_author_of_status_line (git blame the Status line, return the author name verbatim, \u0022\u0022 if no Ratified ` +
  `line); introduced_by_human (true UNLESS the commit that introduced the Ratified line was authored by a ` +
  `workflow/bot identity such as one containing \u0022claude\u0022, \u0022bot\u0022, \u0022github-actions\u0022, or the workflow\u0027s own ` +
  `committer -- if bot-authored, false).\n\n` +
  `Fabricate nothing. A missing file is exists:false, not a guess. Return RAW text, not interpretation.`,
  { label: 'preflight:read-handoff', phase: 'Pre-flight', schema: HANDOFF_FACTS, model: 'opus', effort: 'low' }
)

// ===================== STAGE 0b: H1-H6 FAIL-CLOSED GATE (pure JS) =================
// The agent fetched facts; JS DECIDES. Evaluated in order; first false short-circuits so
// failed_check is unambiguous. This is the only stage that authorizes the build agent.
function refuse(failed_check, reason, evidence, human_options) {
  return { outcome: 'REFUSED', failed_check, reason: asciiFold(reason), evidence: (evidence || []).map(asciiFold), human_options: human_options || [] }
}
if (!facts || typeof facts !== 'object') {
  return refuse('H1', 'the handoff reader returned nothing -- cannot verify the spec on disk', [],
    ['Re-invoke; if it persists, the spec dir may be unreadable.'])
}
const fileRec = n => (facts.files || []).find(y => y.name === n)
const fileOk = n => { const x = fileRec(n); return !!(x && x.exists && x.bytes > 0) }
const fileCommitted = n => { const x = fileRec(n); return !!(x && x.committed === true) }
const g = facts.git || {}
const prov = facts.status_line_provenance || {}

// H1: spec dir exists ON THE CURRENT BRANCH/CWD. The reader is NOT worktree-isolated -- it
// resolves the repo root from the SESSION cwd, so a "not found" here almost always means the
// session is on the WRONG branch (e.g. main / a generic session worktree), not that the spec
// is truly absent: idea-to-spec leaves the spec committed on a numbered FEATURE branch in its
// own worktree. Name that cause so the operator switches worktrees instead of re-numbering.
if (!facts.dir_exists) return refuse('H1', `spec dir ${INPUT.spec_dir} not found on the CURRENT branch "${g.current_branch || '?'}"`,
  [`${INPUT.spec_dir}/ absent on ${g.current_branch || '?'}`, `the spec is likely committed on the FEATURE branch "${INPUT.branch || INPUT.feature}", not the branch this session is on`],
  [`Switch into the ratified feature worktree (the checkout on branch "${INPUT.branch || INPUT.feature}" that carries ${INPUT.spec_dir}/) and re-invoke from there -- implement runs in the session cwd and does NOT switch branches itself.`,
   'If you have not planned this idea yet, run idea-to-spec first.'])
// H2: all 5 artifacts present + non-empty
const missing = ARTIFACTS.filter(n => !fileOk(n))
if (missing.length) return refuse('H2', `artifact set incomplete -- the chain did not finish: missing/empty ${missing.join(S(44,32))}`,
  missing, ['Run idea-to-spec (or speckit-finish-chain) to produce spec+plan+tasks+analysis+plan-review.'])
// H2b: every artifact must be COMMITTED + clean on the branch. The PR ships the COMMITTED
// branch, so an uncommitted/dirty tasks.md or plan.md would pass this working-tree preflight
// but never reach the PR -- and a dirty spec dir risks being swept into a task commit. Require
// committed+clean so what the build reads is exactly what the PR carries.
const uncommitted = ARTIFACTS.filter(n => !fileCommitted(n))
if (uncommitted.length) return refuse('H2', `artifact(s) not committed/clean on the branch: ${uncommitted.join(S(44,32))} -- the build runs off the committed tree and would not see working-tree-only changes`,
  uncommitted, ['Commit the spec artifacts on the feature branch (git add specs/<dir>/ && commit) before re-invoking; do not leave them dirty.'])
// H3: human-ratified (the load-bearing gate) -- Ratified present, no contradictory Draft/BLOCKED,
//     and the line was introduced by a HUMAN (git-blame provenance), not the workflow.
const specRaw = facts.spec_md_raw || ''
const h3 = H3_RATIFIED_RE.test(specRaw) && !H3_DRAFT_RE.test(specRaw) && !H3_BLOCKED_RE.test(specRaw) && prov.introduced_by_human === true
if (!h3) {
  const statusExcerpt = (specRaw.match(/^.*\*\*Status.*$/mi) || ['(no Status line found)'])[0]
  return refuse('H3', 'spec.md Status is not human-Ratified (missing, or carries Draft/BLOCKED, or the Ratified line was bot-authored)',
    [statusExcerpt, `introduced_by_human=${prov.introduced_by_human}, blame_author=\u0022${prov.last_author_of_status_line || S()}\u0022`],
    ['A HUMAN must edit spec.md to "**Status**: Ratified (<name>, <YYYY-MM-DD>)" and commit it themselves. implement cannot do this.'])
}
// H4: no unresolved Principle-V marker remains in ## Clarifications
const clar = facts.clarifications_raw || ''
if (clar === '' || H4_OPEN_MARKER_RE.test(clar)) {
  const openExcerpt = (clar.match(H4_OPEN_MARKER_RE) || [clar === '' ? '(no ## Clarifications section found)' : 'open marker'])[0]
  return refuse('H4', 'unresolved Principle-V marker(s) remain in the ## Clarifications section',
    [openExcerpt], ['Resolve every open item in spec.md ## Clarifications, then re-ratify, before re-invoking.'])
}
// H5: plan-review verdict is not a kill (and must parse -- fail-closed on missing/garbled)
const vm = (facts.plan_review_verdict_line || '').match(H5_VERDICT_RE)
if (!vm || vm[1] === 'BLOCKED') {
  return refuse('H5', 'plan-review.md verdict is BLOCKED or unreadable',
    [facts.plan_review_verdict_line || '(no Verdict line found)'],
    ['Address the adversarial review and re-run plan-review so the verdict is PASS / PASS-WITH-NOTES.'])
}
// H6: on a PR-ready feature branch (verify only; never create/push/merge)
const h6 = g.detached === false && g.current_branch !== 'main' && g.branch_resolved === true && g.spec_dir_on_branch === true
if (!h6) return refuse('H6', 'not on a PR-ready feature branch (HEAD is main/detached, or the branch lacks the spec)',
  [`branch=${g.current_branch}, detached=${g.detached}, spec_dir_on_branch=${g.spec_dir_on_branch}`],
  ['Check out the feature branch carrying this spec; never build on main.'])

// all six true -> the input contract Stage 1 consumes (pure function of the ratified bytes)
const branch = INPUT.branch || g.current_branch
const ratified_status_line = asciiFold((specRaw.match(H3_RATIFIED_RE) || [''])[0])
log(`implement: handoff gate PASSED for ${INPUT.feature} on ${branch} -- ratified, building.`)

// ===================== STAGE 1+2: BUILD (TDD) + VERIFY (CI gates) =================
// ONE worktree agent: reuse /speckit-implement over tasks.md, then run the CI gate set on
// the same checkout. The agent returns FACTS (raw test summary, raw exits); pure JS scores.
phase('Build + verify (isolated)')
const BUILD_RESULT = {
  type: 'object', additionalProperties: false,
  required: ['feature', 'branch', 'spec_dir', 'tasks_total', 'tasks_done', 'tasks_blocked', 'principle_v_wall', 'open_for_human', 'status', 'blocked_reason', 'notes', 'verify'],
  properties: {
    feature: { type: 'string' },
    branch: { type: 'string', description: 'worktree feature branch; NEVER main' },
    spec_dir: { type: 'string' },
    tasks_total: { type: 'number', description: 'count parsed from the ratified tasks.md' },
    tasks_done: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['task_id', 'committed', 'verified'],
        properties: {
          task_id: { type: 'string' },
          committed: { type: 'boolean' },
          verified: { type: 'string', enum: ['tests-pass', 'ci-only'], description: 'ci-only = code complete but its verifying test is the 3.13/CI-only one; NEVER reported as tests-pass' },
        },
      },
    },
    tasks_blocked: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['task_id', 'reason', 'detail'],
        properties: {
          task_id: { type: 'string' },
          reason: { type: 'string', enum: ['principle-v-wall', 'assumes-deferred-capability', 'test-fail', 'gate-fail', 'checklist-incomplete-stop'] },
          detail: { type: 'string', description: 'the exact open question / deferred capability; NEVER an invented answer' },
        },
      },
    },
    principle_v_wall: { type: 'boolean' },
    open_for_human: { type: 'array', items: { type: 'string' } },
    status: { type: 'string', enum: ['built', 'partial', 'blocked', 'failed'], description: 'agent self-report; JS RE-DERIVES the real outcome -- never trusted alone' },
    blocked_reason: { type: 'string' },
    notes: { type: 'string', description: 'ASCII; coverage caveat, CI-only caveat, follow-ups' },
    // verify facts gathered on the SAME worktree, in CI order (the agent returns raw values; JS scores)
    verify: {
      type: 'object', additionalProperties: false,
      required: ['install_ok', 'pytest_argv', 'pytest_summary_line', 'pytest_deselected_ids', 'pytest_collected', 'coverage_term_total', 'ruff_format_exit', 'ruff_check_exit', 'retail_check_exit', 'retail_check_commit_range_resolved', 'retail_semantic_check_exit', 'retail_validate_status', 'wiring_ok', 'never_execute_ok', 'head_branch'],
      properties: {
        install_ok: { type: 'boolean' },
        pytest_argv: { type: 'string', description: 'the EXACT pytest argv run, incl any --deselect' },
        pytest_summary_line: { type: 'string', description: 'the verbatim final pytest summary line' },
        pytest_deselected_ids: { type: 'array', items: { type: 'string' }, description: 'node ids deselected; JS asserts subset of CI_ONLY_TESTS' },
        pytest_collected: { type: 'number', description: 'collected count; -1 if collection errored' },
        coverage_term_total: { type: 'string', description: 'observed term-missing TOTAL %, or "unknown" -- NEVER fabricated' },
        ruff_format_exit: { type: 'number' },
        ruff_check_exit: { type: 'number' },
        retail_check_exit: { type: 'number' },
        retail_check_commit_range_resolved: { type: 'boolean', description: 'true if merge-base(origin/main,HEAD) resolved (ranged run); false -> a BARE retail check was run instead (as CI does); retail_check_exit is scored either way' },
        retail_semantic_check_exit: { type: 'number' },
        retail_validate_status: { type: 'string', enum: ['needs-db', 'pass', 'fail'], description: 'needs-db is the EXPECTED deferred state; INFORMATIONAL, never scored' },
        wiring_ok: { type: 'boolean', description: 'EXPECTED_RULE_IDS updated for any added/removed @register rule (test_rules_wiring green)' },
        never_execute_ok: { type: 'boolean', description: 'B1 sentinel green: no module-scope DB/network import in governed src/retail/' },
        head_branch: { type: 'string', description: 'git rev-parse --abbrev-ref HEAD at verify time; JS asserts != main' },
      },
    },
  },
}
const build = await agent(
  `You are the IMPLEMENT BUILDER for Seshat BI. You run in the SESSION cwd, which the workflow ` +
  `requires to ALREADY be the ratified feature-branch worktree (idea-to-spec created one worktree ` +
  `per feature; you build IN PLACE on that branch -- you are NOT separately isolated and must NOT ` +
  `create or switch worktrees). You write code + tests + per-task commits on the RATIFIED feature branch and ` +
  `STOP. You NEVER merge, push, touch main, open a PR, or edit the spec\u0027s Status line. Repo: Seshat_BI.\n\n` +
  `FEATURE: ${INPUT.feature}\nSPEC DIR: ${INPUT.spec_dir}\nRATIFIED BRANCH: ${branch}\n\n` +
  `STEP A -- worktree safety FIRST (load-bearing now that you build in place): assert git rev-parse --abbrev-ref HEAD is the ratified feature ` +
  `branch (carrying ${INPUT.spec_dir}/spec.md) and NOT main/detached. If not, STOP: status:\u0027failed\u0027, ` +
  `blocked_reason:\u0027worktree-not-on-feature-branch\u0027, write nothing.\n\n` +
  `STEP A0 -- PIN the feature dir via the ENV OVERRIDE (critical, and do NOT dirty tracked config): ` +
  `/speckit-implement\u0027s prereq script resolves the feature in this order (verified, common.ps1 L290): ` +
  `(1) the SPECIFY_FEATURE_DIRECTORY env var, then (2) the PERSISTED .specify/feature.json (which is a ` +
  `TRACKED file that may hold a STALE prior feature). So EXPORT SPECIFY_FEATURE_DIRECTORY=${INPUT.spec_dir} ` +
  `for every command in this run BEFORE invoking the skill -- the env override wins, so you get the ` +
  `right feature WITHOUT modifying the tracked .specify/feature.json (leaving it dirty risks it being ` +
  `swept into a task commit, or tested-with-but-absent-from the PR). Do NOT overwrite the file; do NOT ` +
  `commit any config change. If you cannot set the env, FAIL closed (status:\u0027failed\u0027, ` +
  `blocked_reason:\u0027cannot pin SPECIFY_FEATURE_DIRECTORY\u0027) rather than mutate the tracked file -- never ` +
  `risk a silent wrong-feature build (ledger would report ${INPUT.feature} while a stale list ran).\n\n` +
  `STEP B -- handle the SKILL\u0027s interactive STOP: /speckit-implement has a hard \u0022Wait for user ` +
  `response\u0022 prompt when checklists are incomplete. You have NO user. Do NOT auto-answer it. Record it ` +
  `as a tasks_blocked entry {reason:\u0027checklist-incomplete-stop\u0027} and return status:\u0027partial\u0027 -- the ` +
  `human decides.\n\n` +
  `STEP C -- BUILD: invoke /speckit-implement over ${INPUT.spec_dir}/tasks.md. Execute the ratified ` +
  `task list (do NOT re-plan -- YAGNI). TDD order, tests-first; a task is DONE only when its tests pass. ` +
  `Commit per task: \u0022feat: <task-id> <desc> (${INPUT.feature.slice(0, 3)})\u0022. Skip a task already done + ` +
  `committed + passing (resume-safe). STOP a task (never invent) if it needs a Principle-V ruling ` +
  `(grain/uniqueness, PII publish-safety, business rollup/segment, product identity) the spec left open, ` +
  `or assumes a DEFERRED capability (F016 Power BI Execution Adapter; F031-F033 spec-only) -> record to ` +
  `tasks_blocked + open_for_human + set principle_v_wall true if it is a judgment call; build only ` +
  `non-dependent tasks past it.\n\n` +
  `STEP D -- ENV-GAP (honest, never fake green): local Python is 3.12 but the package requires >=3.13, ` +
  `and there is NO skipif(version) marker, so this test does NOT auto-skip and will fail/err locally: ` +
  `${CI_ONLY_TESTS.join(S(44,32))}. Run pytest -m unit with an EXPLICIT --deselect of exactly that node id; ` +
  `return the EXACT pytest_argv, the verbatim pytest_summary_line, and pytest_deselected_ids. A test that ` +
  `could NOT run is NEVER counted as passing -- a task whose only verifying test is that CI-only one is ` +
  `committed with verified:\u0027ci-only\u0027 (code complete, CI-verified-pending), never \u0027tests-pass\u0027. Report ` +
  `coverage_term_total as observed or \u0022unknown\u0022 -- NEVER fabricate a number.\n\n` +
  `STEP E -- VERIFY (after build, on this SAME worktree, in CI order; return RAW exits, do not judge):\n` +
  `  1. pip install -e \u0022.[dev]\u0022  -> install_ok\n` +
  `  2. ruff format --check src tests  -> ruff_format_exit\n` +
  `  3. ruff check src tests  -> ruff_check_exit\n` +
  `  4. pytest -m unit (with the deselect from STEP D)  -> summary + deselected ids + collected\n` +
  `  5. git fetch origin main; if git merge-base origin/main HEAD resolves, run ` +
  `retail check --commit-range \u0022<merge-base>..HEAD\u0022 -> retail_check_exit (retail_check_commit_range_` +
  `resolved:true). If merge-base does NOT resolve, run BARE retail check (exactly as CI does in that ` +
  `case -- ci.yml falls back to bare retail check, it does NOT skip) and record its exit in ` +
  `retail_check_exit with retail_check_commit_range_resolved:false. Either way retail_check_exit MUST ` +
  `reflect a real run -- the gate scores it (a P2 on grandfathered history is honest; it collapses on ` +
  `squash-merge, same as CI).\n` +
  `  6. retail semantic-check --repo .  -> retail_semantic_check_exit\n` +
  `  retail_validate_status: record \u0027needs-db\u0027 (the EXPECTED deferred state -- retail validate without a ` +
  `DB/--source-map returns the deferred state; CI does NOT run it; it is INFORMATIONAL, never scored).\n` +
  `  wiring_ok: if any task added/removed a @register rule, the SAME change updated EXPECTED_RULE_IDS in ` +
  `tests/unit/test_rules_wiring.py (the test asserts len(all_rules())==len(EXPECTED_RULE_IDS)); else true.\n` +
  `  never_execute_ok: any new governed src/retail/ module imports DB/network drivers LAZILY (in-function), ` +
  `never at module scope (the B1 invariant); else true.\n` +
  `  head_branch: git rev-parse --abbrev-ref HEAD at verify time.\n\n` +
  `CONSTRAINTS: ASCII + UTF-8 no BOM in any authored file (-- and ->, no glyphs; rule IX). Generic-only ` +
  `(no C086/pharmacy specifics; rule 7). No fabricated confidence/coverage (rule 9). Never merge/push/` +
  `touch main/open a PR/edit Status. status is your self-report -- the orchestrator RE-DERIVES the real ` +
  `outcome in JS; report honestly (a failing test is \u0027test-fail\u0027 in tasks_blocked, never hidden).`,
  // NO isolation:'worktree' here. The completion gate requires head_branch === expectedBranch
  // (the ratified feature branch), but a fresh isolated worktree gets a NEW branch and git
  // forbids a second checkout of an already-checked-out branch -- so an isolated builder can
  // NEVER satisfy the gate. The builder instead runs in the session cwd, which the whenToUse
  // precondition requires to already BE the ratified feature-branch worktree (idea-to-spec
  // creates one worktree per feature, so this builder is one-feature-per-run inside it --
  // the per-feature worktree already provides the isolation a separate build worktree would).
  { label: `build:${INPUT.feature}`, phase: 'Build + verify (isolated)', schema: BUILD_RESULT, model: 'opus', effort: 'high' }
)

// ===================== STAGE 3: COMPLETION GATE (pure JS; agent cannot soften) =====
// Scores EXACTLY the CI set (pytest -m unit, retail check, retail semantic-check) + the
// wiring/never-execute invariants + no-Principle-V-wall. retail validate is NOT scored
// (CI never runs it; it is structurally always non-zero here). Coverage is reported, never
// gated (CI has no --cov-fail-under).
function deselectsAreExplained(v) {
  const ds = (v && Array.isArray(v.pytest_deselected_ids)) ? v.pytest_deselected_ids : []
  // (1) every reported deselect must be in the CI-only allow-list, AND (2) the --deselect
  // tokens actually present in the argv must MATCH the reported ids -- otherwise a hidden
  // argv "--deselect foo.py::test_bar" omitted from pytest_deselected_ids would skip a real
  // test undetected (the argvCore strip would remove it, hiding the subset run). Both the
  // reported set and the argv set must be exactly the allow-list (or empty).
  const argv = (v && v.pytest_argv) || ''
  const argvDeselects = [...argv.matchAll(/(?:^|\s)--deselect(?:\s+|=)(\S+)/g)].map(m => m[1])
  const sorted = a => a.slice().sort().join('\u0001')
  const idsAllAllowed = ds.every(id => CI_ONLY_TESTS.includes(id))
  const argvAllAllowed = argvDeselects.every(id => CI_ONLY_TESTS.includes(id))
  const argvMatchesIds = sorted(argvDeselects) === sorted(ds)   // no hidden argv deselect
  return idsAllAllowed && argvAllAllowed && argvMatchesIds
}
function completionGate(b, expectedBranch) {
  const v = b && b.verify
  const reasons = []

  // (a) every task accounted for -- computed in JS, not trusted from the agent's status enum.
  // A "done" task must also be COMMITTED, or its changes are not on the PR branch: a
  // size-only done===total check would call READY a branch missing that task's code.
  const doneArr = (b && Array.isArray(b.tasks_done)) ? b.tasks_done : null
  const total = b ? b.tasks_total : 0
  const done = doneArr ? doneArr.length : -1
  const blocked = (b && Array.isArray(b.tasks_blocked)) ? b.tasks_blocked.length : 1
  const allCommitted = !!doneArr && doneArr.every(t => t && t.committed === true)
  const tasksAllDone = total > 0 && done === total && blocked === 0 && allCommitted
  if (!tasksAllDone) reasons.push(`tasks incomplete: ${done}/${total} done, ${blocked} blocked` + (doneArr && !allCommitted ? ', some done tasks UNCOMMITTED (not on the branch)' : ''))

  // (b) tests + lint green; the ONLY deselects are the JS allow-list; install + collection ok.
  // The argv MUST be the real CI gate: "pytest -m unit" with NO narrowing (-k / a single
  // file / a node-id arg), or an "N passed" summary from a narrowed run could fake green.
  const summary = (v && v.pytest_summary_line) || ''
  const argv = (v && v.pytest_argv) || ''
  // Strip the sanctioned "--deselect <node-id>" tokens BEFORE checking for narrowing --
  // a deselect value legitimately contains a .py path and a ::node-id (the CI-only test),
  // so scanning the raw argv would false-positive on the allowed deselect. After stripping,
  // the remainder must be a full "pytest -m unit" with no -k, no ::node-id, no bare .py file.
  const argvCore = argv.replace(/(^|\s)--deselect(\s+|=)\S+/g, ' ')
  // Reject narrowing/subset flags: -k, ::node-id, a bare .py file; the cache-subset flags
  // (--lf/--last-failed/--ff/--failed-first/--sw/--stepwise) that rerun only a CACHED subset;
  // AND the collection-ignore flags (--ignore / --ignore-glob) that drop paths at collection
  // -- all can produce "N passed" without the full unit suite. Only a clean "pytest -m unit"
  // (plus the sanctioned --deselect, already stripped) is the CI-equivalent run.
  const argvIsFullUnitRun = /(^|\s)-m\s+unit(\s|$)/.test(argvCore) &&
    !/(^|\s)-k(\s|=)/.test(argvCore) && !/::/.test(argvCore) && !/(^|\s)[^\s-]\S*\.py(\s|$)/.test(argvCore) &&
    !/(^|\s)(--lf|--last-failed|--ff|--failed-first|--sw|--stepwise|--stepwise-skip)(\s|$)/.test(argvCore) &&
    !/(^|\s)--ignore(-glob)?(\s|=)/.test(argvCore)
  const summaryGreen = !!(v && v.install_ok && v.pytest_collected >= 0 && argvIsFullUnitRun &&
    /(?:^|\s)\d+ passed\b/.test(summary) && !/\b(failed|error|errors)\b/i.test(summary))
  const deselectExplained = deselectsAreExplained(v)
  const testsOk = !!(summaryGreen && deselectExplained && v && v.ruff_format_exit === 0 && v.ruff_check_exit === 0)
  if (!testsOk) {
    // install_ok stays a hard requirement (CI must install), but a FAILED install is most
    // often the env mismatch: this builds code for a >=3.13 package, so `pip install -e
    // ".[dev]"` cannot succeed on the documented local 3.12 -- name that distinctly so a
    // human sees "wrong interpreter" rather than a confusing generic "tests not green".
    if (v && v.install_ok === false) {
      reasons.push('pip install -e ".[dev]" failed -- run implement on a >=3.13 dev toolchain (the package requires-python >=3.13; local 3.12 cannot install/build/test it). This is an environment gate, not a code failure.')
    } else {
      reasons.push(`tests/lint not green: \u0022${summary || S(110,111,32,118,101,114,105,102,121,32,114,101,99,111,114,100)}\u0022` +
        (v && !argvIsFullUnitRun ? ` (argv was NOT a full \u0022pytest -m unit\u0022 run: \u0022${argv}\u0022)` : '') +
        (v && !deselectExplained ? ' (UNEXPLAINED deselect -- not the CI-only allow-list)' : ''))
    }
  }

  // (c) the EXACT CI gate set: retail check + retail semantic-check. CI does NOT skip
  // retail check when the merge-base is unavailable -- it falls back to BARE `retail check`
  // (ci.yml L49-53). So the agent must do the same (run bare retail check on an unresolved
  // range), and the gate ALWAYS scores retail_check_exit === 0. Treating an unresolved range
  // as auto-green would advertise PR-ready locally while CI's bare run fails.
  const checkGreen = !!(v && v.retail_check_exit === 0)
  const semanticGreen = !!(v && v.retail_semantic_check_exit === 0)
  if (!checkGreen) reasons.push(`retail check exit ${v ? v.retail_check_exit : S(63)}` + (v && v.retail_check_commit_range_resolved === false ? ' (bare run; merge-base unresolved)' : ''))
  if (!semanticGreen) reasons.push(`retail semantic-check exit ${v ? v.retail_semantic_check_exit : S(63)}`)

  // (d) wiring + never-execute invariants green
  const wiringGreen = !!(v && v.wiring_ok === true && v.never_execute_ok === true)
  if (!wiringGreen) reasons.push('rule-wiring or never-execute (B1) invariant is red')

  // (e) no Principle-V wall / surfaced judgment call
  const noWall = !!(b && b.principle_v_wall === false && (!Array.isArray(b.open_for_human) || b.open_for_human.length === 0))
  if (!noWall) reasons.push(`Principle-V wall: ${b && b.open_for_human ? b.open_for_human.join(S(59,32)) : S(117,110,114,101,115,111,108,118,101,100,32,106,117,100,103,109,101,110,116,32,99,97,108,108)}`)

  // (f) the build+verify happened on the EXPECTED ratified branch, not just "not main".
  // If verify ran on some other feature branch, the PR-ready branch the ledger advertises
  // may not contain the tested commits -- defeating the per-task commit guarantee. Compare
  // head_branch to the expected branch (and always reject main as a backstop).
  const headOk = !!(v && v.head_branch && v.head_branch !== 'main' &&
    (!expectedBranch || v.head_branch === expectedBranch))
  if (!headOk) reasons.push(`HEAD at verify time is \u0022${v ? v.head_branch : S(63)}\u0022 -- must be the ratified branch \u0022${expectedBranch || S(40,101,120,112,101,99,116,101,100,41)}\u0022, never main or another branch`)

  if (reasons.length === 0) return { outcome: 'READY_FOR_PR', reasons: [] }
  // hard red (fix-first) vs partial (honest progress / wall -- resume continues)
  const hardRed = !testsOk || !checkGreen || !semanticGreen || !wiringGreen || !headOk ||
    (b && Array.isArray(b.tasks_blocked) && b.tasks_blocked.some(t => t.reason === 'test-fail' || t.reason === 'gate-fail'))
  return { outcome: hardRed ? 'BLOCKED' : 'PARTIAL', reasons }
}
const gate = completionGate(build, branch)   // branch = the ratified branch from the H6 gate

// ===================== STAGE 4: PR-READY LEDGER (read-only assembler; STOPS) =======
phase('PR-ready ledger')
const PR_LEDGER = {
  type: 'object', additionalProperties: false,
  required: ['pr_summary', 'how_to_open_pr', 'how_to_fix_and_rerun'],
  properties: {
    pr_summary: { type: 'string', description: 'ASCII markdown; sections 1-8, stop-on-fail top-down' },
    how_to_open_pr: { type: 'string', description: 'exact human gh pr create steps; "" unless READY_FOR_PR' },
    how_to_fix_and_rerun: { type: 'string', description: 'what to fix + resume re-invoke; "" unless BLOCKED/PARTIAL' },
  },
}
const ledger = await agent(
  `You are the PR-READY LEDGER assembler for a Seshat BI implement run. You ARRANGE the FIXED outcome ` +
  `into a scannable ASCII ledger a human reads top-down. You do NOT recompute the outcome, change any ` +
  `verdict, open a PR, push, or merge. ASCII only (-- and ->).\n\n` +
  `FIXED OUTCOME: ${gate.outcome}\n` +
  `BLOCKING REASONS (JS-computed; empty iff READY_FOR_PR): ${JSON.stringify(gate.reasons)}\n` +
  `FEATURE: ${INPUT.feature}  BRANCH: ${branch}  SPEC DIR: ${INPUT.spec_dir}\n` +
  `RATIFIED STATUS LINE (proof implement did not self-ratify): ${ratified_status_line}\n\n` +
  `=== BUILD + VERIFY RECORD ===\n${JSON.stringify(build, null, 2)}\n\n` +
  `Write pr_summary with these sections, stop-on-fail top-down: (1) FROM SPEC: feature + branch + the ` +
  `ratified status line (a human wrote it; implement did not); (2) OUTCOME + the blocking reasons first ` +
  `if not READY_FOR_PR; (3) TASKS: done/total + blocked ids; (4) TESTS: status + the NAMED ci-only ` +
  `deselected test, flagged as a RESIDUAL RISK the human must weigh: \u0022this subprocess import-isolation ` +
  `test is deselected locally and is verified ONLY by CI (3.13); if a change regresses it, CI -- not ` +
  `this local run -- is what catches it. It is NOT a faked local pass.\u0022 List any real failures ` +
  `individually; (5) GOVERNANCE: retail check / semantic-check / wiring / ` +
  `never-execute each its own line, plus \u0022retail validate: needs-db-deferred (informational, per ` +
  `Principle VIII)\u0022; (6) PRINCIPLE-V STOPS: surfaced questions or \u0022(none)\u0022; (7) DIFF SUMMARY: the ` +
  `per-task commit subjects on the branch; (8) NEXT ACTION.\n` +
  `If READY_FOR_PR: how_to_open_pr = the exact human steps (gh pr create --base main --head ${branch} ` +
  `..., review, merge) and note the workflow itself will NOT open or merge it; how_to_fix_and_rerun = \u0022\u0022.\n` +
  `If BLOCKED/PARTIAL: how_to_fix_and_rerun = what to fix + \u0022re-invoke Workflow({scriptPath, ` +
  `resumeFromRunId}) -- done tasks skip\u0022; how_to_open_pr = \u0022\u0022.`,
  { label: 'ledger:pr-ready', phase: 'PR-ready ledger', schema: PR_LEDGER, model: 'opus', effort: 'high' }
)

// ===================== TERMINAL SEAM (no-merge constants; uncomputable-otherwise) ==
// implement produced a PR-ready branch and STOPS. The human opens + merges the PR. No
// code path here merges, pushes to main, or marks work approved/ratified -- proven by the
// acceptance test (grep) shipped alongside this workflow.
return {
  outcome: gate.outcome,                 // READY_FOR_PR | BLOCKED | PARTIAL (pure JS)
  feature: INPUT.feature,
  branch,
  spec_dir: INPUT.spec_dir,
  ratified_status_line,                  // the human-written line; implement never wrote it
  blocking_reasons: gate.reasons,
  build,
  ledger,
  handoff: {
    branch,                              // the PR-ready worktree branch
    merged_to_main: false,               // ALWAYS false -- this workflow cannot merge
    pushed_to_main: false,               // ALWAYS false -- this workflow cannot push to main
    ratified: false,                     // implement never ratifies (the human did, upstream)
    pr_opened: false,                    // default; the human runs gh pr create
    note: 'implement produced a PR-ready branch and stopped. The human opens + merges the PR. No code path here merges, pushes to main, or marks work approved/done.',
  },
}
