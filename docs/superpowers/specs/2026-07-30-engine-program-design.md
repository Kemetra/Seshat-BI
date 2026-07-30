# Engine Program Design — four tracks to harden and extend the Seshat kit engine

**Created**: 2026-07-30
**Status**: Draft — awaiting owner review
**Scope**: the kit engine itself (`src/seshat/`, `.claude/skills/`, `tests/`, distribution),
not any customer warehouse.

## Why this document exists

The request was "make our tool engine incredible". That is four independent
subsystems, not one project, so this document decomposes it into four tracks, each
of which gets its own PR. Every track below is anchored to evidence verified in the
committed tree on 2026-07-30 — not to `docs/roadmap/idea-backlog.md`, whose entries
are a generated triage opinion, and not to spec `**Status**:` lines, which this
investigation found to be unreliable (see *Discovered issue*).

Two tracks changed shape once the tree was checked:

- **T2 needs no new design.** `specs/118-cvd-simulation-evidence/` already exists as
  a fully clarified spec (four Q/A rounds, 2026-07-10) with `plan.md` and `tasks.md`.
  This document records only the delta needed to unblock it.
- **T3 is a confirmed defect, not a vague improvement.** The rule-id coverage gap is
  measurable and unguarded (numbers below).

## Track T1 — Close the temp-git test portability gap

### Problem

`tests/unit/_gitfix.py:9` ships `make_git_repo(tmp_path) -> Path`, which inits with
`-b main`, sets `user.email`/`user.name`, and sets `commit.gpgsign false`. Several
tests build their own temp repo and call `git commit` *without* disabling signing, so
they inherit whatever global git config the developer has. Where a global
`commit.gpgsign=true` with `gpg.format=ssh` is set, `git commit` exits 128 with no
`SSH_AUTH_SOCK` present, and the tests fail for reasons unrelated to the code.

CI does not currently configure signing, so CI does not see this. That makes it
latent rather than harmless: any CI change that introduces commit config turns these
into red builds, and today they make every local `pytest -m unit` run untrustworthy —
which in turn weakens the verification evidence for T2, T3, and T4.

### Measured baseline

`pytest -m unit` on a clean checkout of `main` at commit `512ff40`, 2026-07-30:
**17 failed, 4288 passed, 28 skipped, 388 deselected** in 691s. All 17 are
environmental, in two distinct groups.

**Group B — 13 failures, this track's scope.** Confirmed by re-running the five
files with `GIT_CONFIG_GLOBAL` pointed at a scratch config carrying
`commit.gpgsign=false`: **59 passed, 1 skipped in 11.97s**. The failing tests are:

| File | Failing tests |
|---|---|
| `tests/unit/dbt/test_scaffold_conformed_orchestration.py` | 6 |
| `tests/unit/dbt/test_project.py` | 2 |
| `tests/unit/test_portfolio_watch_invariants.py` | 2 |
| `tests/unit/test_workspace_init.py` | 2 |
| `tests/unit/test_portfolio_watch_summary.py` | 1 |

A static sweep for call sites lacking `commit.gpgsign=false` was run first and proved
**unreliable in both directions** — it missed the two `tests/unit/dbt/` files and
`test_workspace_init.py`, and it flagged `tests/unit/test_stage1_scaffold.py`, which
does not fail. The measured list above supersedes it; scope T1 from the run, and
re-measure rather than re-reasoning if the set appears to change.

`tests/integration/test_watch_cli.py::test_watch_writes_only_the_local_snapshot`
builds a temp repo and commits at L77-78 without disabling signing, so it is the same
latent defect, but `-m unit` deselects it and this baseline therefore does not prove
it fails. Confirm it directly before including it.

Sites verified already safe and explicitly **out of scope**: `test_dagster_evidence.py`,
`tests/fixtures/portfolio_watch/builders.py::init_git_repo`, the three
`test_pbip_adoption_*.py` files, and `test_fresh_workspace.py` all set
`commit.gpgsign=false` inline. `test_cli.py::_init_repo`,
`test_distribution_compat.py`, and `test_security_review_findings.py::_git_repo`
only `git init` and never commit, so they have no exposure.

**Group A — 4 failures, not this track.** `test_registry.py`,
`test_cli_analyze.py`, `test_cli_dagster.py`, and `test_metric_drift.py` each spawn a
clean subprocess (`<python> -c "import seshat.rules; …"`) to prove a lazy-import
boundary holds (rules B1/B3) — the right design for that assertion. They fail with
`ModuleNotFoundError: No module named 'seshat.rules'` because the editable install in
the active interpreter predates the `retail` → `seshat` rename. The fix is
`pip install -e .`; there is no code defect. Recorded here so a future run does not
mistake them for regressions.

### Design

Repoint the temp-repo construction in the five Group-B files at
`_gitfix.make_git_repo`. No helper changes are needed: none of the callers requires a
bare repo, a remote, a `file://` protocol allowance, or a non-`main` initial branch —
the four capabilities `make_git_repo` already provides are exactly the four they need.
Where a site currently inlines identity config, that config is deleted rather than
kept, so the helper stays the single place signing policy is expressed.

`tests/integration/test_watch_cli.py` is a candidate, not a commitment: confirm it
actually fails under a signing global first. If it does, fold it into the same PR
(same defect, same one-line fix); if it does not, leave it alone rather than churn a
passing test.

### Non-goals

Not converting the already-safe inline sites for stylistic consistency (churn without
defect). Not changing `_gitfix.py`'s API. Not touching
`test_cli_identity_version.py::test_version_resolver_matches_pyproject_when_installed`
— it did not fail in the measured baseline. `_distribution_version()` in
`seshat/cli/parser.py` reads installed metadata via `importlib.metadata` and compares
it to `pyproject.toml`, and the test skips when that metadata is absent, so a stale
editable install shows up as a skip or a Group-A failure rather than here. Either way
the remedy is `pip install -e .`, an environment action, not a code change.

Not fixing Group A in this track. Making those four guards degrade to a skip with a
"reinstall the editable package" reason would be a genuine ergonomic improvement, but
it also weakens a governance assertion (B1/B3) by letting it pass silently — that
trade is its own decision, not a rider on a test-portability fix.

### Testing

The change *is* test code, so verification is the suite itself: the four converted
tests must pass with a global `commit.gpgsign=true` present, which is the condition
that currently breaks them. Confirm by running the four with signing configured
globally rather than by asserting on the helper.

## Track T2 — Implement `specs/118-cvd-simulation-evidence`

### Status

Design complete and owner-clarified in `specs/118-cvd-simulation-evidence/spec.md`
(`plan.md` and `tasks.md` present). Not implemented: no colour-vision-deficiency
transform exists anywhere in `src/seshat/`.

### Delta needed to unblock it

The spec was written before the `retail` → `seshat` module rename, so its anchors are
stale pointers rather than wrong intent:

| Spec says | Current tree |
|---|---|
| `src/retail/color.py` | `src/seshat/color.py` — `delta_e76` at L83 |
| `theme_gen.py:569` (the OPEN checkbox) | `src/seshat/theme_gen.py:789-790` |
| `theme_gen.py:470` | shifted to ~L676 |

The spec's substantive decisions all survive the rename and are confirmed by the
tree: `render_spec_md()` (`theme_gen.py:758-808`) hand-composes the checklist as a
literal Markdown string, and its "Accessibility checks" section already mixes computed
`[x]` lines with disclaimed `[ ]` OPEN lines each carrying an `*Evidence: …*`
provenance note. So the spec's companion-file output shape joins an existing
convention instead of inventing one, and the `- [ ] **CVD distinguishability** -- OPEN`
checkbox stays open for a named reviewer.

### Governance constraints (from the spec, restated because they bound the code)

Per-pair `delta_e76` on simulated colours is a **measurement** and is permitted — the
shipped CT2/CT3 rules already surface pairwise deltaE. Forbidden: any rolled-up "CVD
score", any pass/fail verdict against a threshold, any theme ranking, any count
presented as a quality index, and any claim that a palette is or is not
colorblind-safe. Ordering pairs by measured distance is a presentation of measured
values, not a new computed rank. These are hard rule #9 and Principle V, and
`design_categorical_distinctness.py` (CT3) and `design_ramp_deltae.py` (CT2) already
carry the same disclaimer in their docstrings.

### Testing

`render_spec_md`'s CVD checkbox line currently has **no test coverage** —
`tests/unit/test_theme_gen.py:466-470` exercises the function but asserts only on the
font-floor and tap-target lines. The transforms are deterministic closed-form colour
projections, so they take exact-value unit tests plus a golden test on the emitted
evidence file. Add an assertion that the OPEN checkbox is still emitted and still
OPEN, so a future change cannot silently convert evidence into a verdict.

## Track T3 — Guard the agent-facing rule-id fix table

### Problem, with measured numbers

| Surface | Count | Guard |
|---|---|---|
| `docs/rules/rules-manifest.json` | **79** rule ids | `tests/unit/test_rules_manifest_snapshot.py` (spec 043) locks it to the live registry |
| `docs/glossary.md` rule table | — | `tests/unit/test_glossary_rule_table.py` |
| prose "N rules" claims | — | rule `SC2` (`src/seshat/rules/rule_count_claims.py`, spec 065) |
| `.claude/skills/retail-govern/SKILL.md` fix table | **45** rows | **none** |

`grep -rl "retail-govern/SKILL.md"` across `src/` and `tests/` returns nothing. `AP1`
(spec 085, implemented at `src/seshat/rules/rule_ap1.py`, present in the manifest) is
absent from the table. No rule id, test, or doc declares the gap intentional.

The consequence is specific: when `seshat check` emits one of the ~34 unlisted ids,
the skill an agent is told to consult for the fix has no row for it. The engine's
own contributing guide points at that table (`CONTRIBUTING.md:73`).

### Design

Extend the guard pattern the repo already uses twice, rather than inventing one.
Two parts:

1. **Make fix guidance data.** `src/seshat/registry.py` currently stores
   `RegisteredRule(id, rule, title, tier)` — severity lives separately in
   `severity_posture.py` + `docs/rules/severity-posture.json`, and fix guidance exists
   only as prose in the skill table and glossary. Add a structured fix field at
   registration so "where to fix this" is attached to the rule.
2. **Guard the surface.** A test asserting the `retail-govern` table's id set matches
   the registry's, in the same shape as `test_glossary_rule_table.py`.

**Decision: generate the table from registry data**, rather than hand-completing it
behind a coverage test. Generation removes the drift class permanently instead of
re-arming it at 80 ids, and it carries no distribution cost: `retail-govern` appears
nowhere in `distribution/public-knowledge-allowlist.yaml`, so
`.claude/skills/retail-govern/SKILL.md` is not vendored into
`integrations/**` and editing it does not require a bundle regeneration. The coverage
test then guards the generated output, matching how `docs/rules/rules-manifest.json`
is both generated and snapshot-locked.

### Non-goals

Not adding a `seshat check` rule for this — the governance/lint lane is saturated and
a new rule must be no-finding on `main` before it can land, which a 34-id gap is not.
A test is the right enforcement surface. Also **not** making the kit verbs
"self-routing": `.seshat/kit-source.yaml` verb entries carry only `id` + `purpose`, and
skill frontmatter carries only `name` + `description`, so routing signal is prose by
design. Changing that is a separate decision, not part of closing a coverage gap.

### Testing

The coverage test is the deliverable. It must fail on the current tree (34 missing
ids, `AP1` among them) before the table is completed — a guard that passes on arrival
proves nothing.

## Track T4 — Bind acceptance fixtures to the bundle they were captured from

### Problem

Distribution has two automated guarantees and one silent gap.

Guaranteed: `scripts/export_agent_bundles.py --check` regenerates both bundles into a
temp dir and diffs byte-for-byte against the committed trees, cross-checking that the
Claude and Codex bundles share one version, source revision, and canonical-source
digest. `scripts/install_smoke_test.py` builds the wheel, pipx-installs into an
isolated HOME, asserts no dev deps leak, runs `init-project` → `status`/`next`/`demo`/
`check`, and asserts no numeric score or fabricated `pass` appears.

The gap: CI's agent-behaviour evidence comes from **pre-recorded** transcripts under
`tests/fixtures/public_distribution/`, classified by
`scripts/external_agent_acceptance.py --transcript` against
`distribution/synthetic-retail/expected-outcomes.yaml`. The live-agent path
(`--execute-cli`) exists but is credential-dependent and deliberately not CI-wired.
The fixture JSONs carry `recorded_at` timestamps and **no** `manifest_digest` or bundle
version, and nothing asserts a fixture was captured against the current bundle. So a
change that alters real agent behaviour passes CI on a stale recording.

### Design

Record provenance on capture and assert it on use: stamp the bundle's
`manifest_digest` into each fixture when it is captured, and have the consuming tests
assert that stamp matches the current bundle. A mismatch should report "this fixture
predates the current bundle; re-capture with `--execute-cli`" — a named, actionable
blocker rather than a silent pass.

### Non-goals

Not running live agents in CI. That needs credentials and a CLI install, and the repo
already made that call deliberately. The honest improvement is making staleness
**visible**, not eliminating the manual capture step.

### Testing

The provenance assertion must fail against today's un-stamped fixtures before they are
stamped, for the same reason as T3.

## Sequencing

| Order | Track | Rationale | Deliverable |
|---|---|---|---|
| 1 | T1 | Makes every later track's "tests pass" claim evidence rather than a caveat; mechanical and zero governance surface | 1 PR |
| 2 | T2 | Design already done and owner-clarified; highest visible value per unit of work | 1 PR |
| 3 | T3 | Independent of T1/T2, but its guard test is easiest to trust once the suite is honestly green | 1 PR |
| 4 | T4 | Packages behaviour the earlier tracks may change; doing it first risks re-stamping twice | 1 PR |

T1 and T2 are independent of each other and could run in parallel worktrees; T3 and
T4 are independent of everything. The order above optimises for review confidence
rather than wall-clock.

## Governance constraints applying to all tracks

No self-granted approvals; grain, PII, business rollups, and metric policy stay named-
human decisions recorded in `approvals[]`. No numeric confidence, health, or readiness
score anywhere (hard rule #9) — status is `status` + `evidence` + `blocking_reasons`.
The static `seshat check` core stays stdlib-only, with no module-scope `import yaml`
(B1/B3). Secrets stay in `.env`; committed text stays ASCII/UTF-8 without BOM (G3/G4).
Any edit under `skills/**` requires `python scripts/export_agent_bundles.py` followed
by `--check`, and `integrations/**` is never hand-edited. Commit subjects are
`<type>: <description>`, scope-free per rule `P2`.

## Discovered issue — not scoped here

`specs/` holds 127 directories whose `**Status**:` lines do not track reality:
`131-portfolio-watch` reads "Ratified" but ships `src/seshat/` code plus tests, while
`118-cvd-simulation-evidence` reads "Draft" and is genuinely unbuilt. Establishing
whether a spec is implemented currently requires reading the tree, which is why this
investigation needed a verification pass before it could plan anything.

This is the same drift class the repo already guards elsewhere — `SC2` for prose rule
counts, `A3` for route-table bijection, `test_glossary_rule_table.py` for the glossary
table — applied to spec status. It is recorded here as a candidate, deliberately
unscoped, because it was discovered during planning rather than requested. It should
be accepted or dropped as its own decision.
