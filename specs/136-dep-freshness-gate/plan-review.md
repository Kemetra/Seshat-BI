# Adversarial Plan Review: Governed Dependency Freshness and Co-Resolution

**Reviewer**: Fable (independent adversarial pass over spec.md, plan.md,
tasks.md, analysis.md at commit 2c4d808, grounded against pip resolver
behavior, the PyPI JSON API, and the repo's install shapes).

**Disposition**: all findings FIXED on this branch in the same cycle; none
dismissed.

## Findings

### D1 (HIGH) -- the gate can silently validate PyPI's copy of seshat-bi instead of the PR's tree

The whole point is catching a conflict IN THE PR before merge. But if any
declared environment references `seshat-bi` by DISTRIBUTION NAME (the
orchestration project will depend on `seshat-bi[dbt]` after spec 135), pip
resolves the PUBLISHED seshat-bi from PyPI (0.4.0) -- NOT the working tree the
PR changed. A PR that edits the root `dbt` extra pins would then co-resolve
against yesterday's published pins and pass while actually broken (or fail
while actually fixed). The gate must resolve LOCAL projects AS LOCAL PATHS.

**Failure scenario**: spec 137 bumps `dbt-core` in the root extra; the
cross-product resolves `seshat-bi[dbt]` from PyPI (still the old pin); the gate
passes; the conflict ships and is discovered at the next release build.

**Fix required (applied)**: FR-002 amended -- any declared environment or
cross-product member that IS a repository-local project MUST be assembled as a
LOCAL PATH requirement (e.g. `<repo-root>[dbt]`, the orchestration directory),
never by distribution name; the manifest schema marks local projects
explicitly; a unit test pins that the assembled requirement strings for local
members are paths, not names. SC-001 only means anything with this fix.

### D2 (MEDIUM) -- INFRA-vs-RESOLUTION classification can fail OPEN

pip does not exit with distinct codes for network vs resolution failures; the
classifier reads stderr text. A resolver error not matching the RESOLUTION
signatures could be classified INFRA ("probably the network") -- excusing a
real conflict, the exact fail-open the spec forbids in prose but did not pin
directionally.

**Fix required (applied)**: FR-004 amended -- classification MUST default to
RESOLUTION (fail-closed, non-zero) when ambiguous; INFRA requires an explicit,
fixture-tested network signature (connection/timeout/DNS/5xx). Unit fixtures
pin BOTH classifications from captured pip outputs.

### D3 (MEDIUM) -- proposal solve-proof semantics were self-contradictory

FR-009 says the solve-proof substitutes the proposed version; the ceiling edge
case said the solve-proof "runs against the ceiling as declared" -- for a
ceilinged pin those cannot both hold, and a proof that does not substitute
proves nothing about the proposal.

**Fix required (applied)**: one semantic everywhere -- the solve-proof ALWAYS
substitutes the proposed version into the affected environment's requirement
set; when a declared ceiling or sibling pin forbids it, the proof honestly
records RESOLUTION with the forbidding requirement named (that IS the
actionable information: what the owner would have to relax). Edge case
reworded to match FR-009.

### D4 (LOW) -- Dependabot may not parse a pyproject carrying a local-path dependency

After spec 135, the orchestration pyproject may carry a repository-local
seshat-bi reference; Dependabot's pip support for local/direct references is
historically shaky and could error or skip the whole manifest.

**Fix required (applied)**: US3 task extended -- verify Dependabot accepts the
orchestration manifest as it exists at implementation time; if it refuses the
local reference, record the limitation in the manifest comment and keep the
directory watched for its remaining named pins (partial coverage recorded
honestly, never claimed as full).

### D5 (LOW) -- two mechanical correctness details lacked pinned tests

(a) `pip --report` requires pip >= 22.2; ephemeral venvs get the BUNDLED pip of
the CI Python -- fine on 3.13, but the script must fail CONFIG-distinct (not
crash) if the venv pip is too old. (b) The PyPI JSON `yanked` flag is
PER-FILE: a release is yanked only when ALL its files are yanked; a
half-yanked release is still installable and may be latest-stable.

**Fix required (applied)**: both pinned as unit-test cases in the tasks (pip
version guard -> CONFIG outcome; yanked-latest computed on the all-files
rule).

## What was attacked and held

- The ephemeral-venv `--dry-run --report` mechanism: preserves the lazy-import
  isolation posture (SC-002); correct boundary vs the offline static gate.
- The manifest-as-data shape (FR-001/FR-015): survives spec 135's pin change
  by data edit only. Holds.
- The Option-B constraint (no new CLI verb): script + CI job + opt-in comment
  reuses existing patterns. Holds.
- The four open-for-human items: correctly refuse the governed-pin bump, the
  merge-blocking policy, the default-on comment, and auto-merge. Holds.
- The `build:` prefix choice for Dependabot subjects: `build` is in the P2
  allow-list and scope-free prefixes match SUBJECT_RE. Holds (verified against
  git_meta.py).

## Verdict

APPROVE WITH REQUIRED FIXES -- all applied on this branch (spec/plan/tasks
amended; see commit trail). With D1 fixed, SC-001 is real: the gate tests the
PR's tree, not PyPI's memory of it. Findings: HIGH 1 (D1), MEDIUM 2 (D2, D3),
LOW 2 (D4, D5) -- all fixed.

This review is not a ratification. RATIFICATION is a named-human edit of the
spec Status line.
