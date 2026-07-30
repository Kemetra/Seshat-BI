# Engine Program Design — five tracks to harden and extend the Seshat kit engine

**Created**: 2026-07-30
**Status**: Draft — awaiting owner review
**Scope**: the kit engine itself (`src/seshat/`, `.claude/skills/`, `tests/`, distribution),
not any customer warehouse.

## Why this document exists

The request was "make our tool engine incredible". That is several independent
subsystems, not one project, so this document decomposes it into five tracks, each of
which gets its own PR. Four were scoped from the request; T5 was discovered during the
investigation and accepted separately (see *Provenance of T5*). Every track below is
anchored to evidence verified in the committed tree on 2026-07-30 — not to
`docs/roadmap/idea-backlog.md`, whose entries are a generated triage opinion, and not to
spec `**Status**:` lines, which this investigation found to be unreliable and which T5
now addresses.

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

Make the **test session** hermetic with respect to git configuration, rather than
fixing each call site. A session-scoped autouse fixture in a new `tests/conftest.py`
points `GIT_CONFIG_GLOBAL` at a known-good throwaway config for the duration of the run,
restoring it afterwards. It goes at `tests/` rather than `tests/unit/` so it also covers
`tests/integration/`; the existing `tests/unit/conftest.py` (which only re-exports two
stub fixtures) and `tests/live_db/conftest.py` compose with it, since pytest applies
conftest files at every directory level.

**Redirect the global layer only — never `GIT_CONFIG_SYSTEM`.** An earlier version of
this design also blanked the system layer "for hermeticity", and it broke five unrelated
`test_narrative_check*` tests, which reported `stale_contract_revision`. On Windows the
Git-for-Windows installer writes `core.autocrlf=true` into the system config
(`git config --show-origin --get core.autocrlf` → `C:/Program Files/Git/etc/gitconfig`),
and blanking that layer changes line-ending normalization on `git add`, which changes
committed **blob SHAs** — so those tests were correct and the fixture was wrong. Nothing
is lost by narrowing: config precedence is system < global < local, verified empirically,
so the fixture's `gpgsign=false` wins even against a system-level `gpgsign=true`. A guard
test asserts `"GIT_CONFIG_SYSTEM" not in os.environ` so the broader version cannot return
as tidying. Every `git` subprocess the suite spawns then
reads known configuration regardless of what the developer has set, and the
developer's real config is never read or written.

An earlier draft of this section proposed repointing the five files at
`_gitfix.make_git_repo`. **That is not viable**: `make_git_repo` hardcodes
`repo = tmp_path / "repo"` and calls `repo.mkdir()` (`tests/unit/_gitfix.py:11-12`),
whereas all five sites initialize git *in place* at a caller-supplied root and pass
that same root to the code under test — via three different local `_git` wrappers
(`test_project.py:264`, `test_scaffold_conformed_orchestration.py:24`,
`test_workspace_init.py:40`), plus `_init_repo_with_commit` at
`test_portfolio_watch_invariants.py:128` and an inline block in
`test_portfolio_watch_summary.py`. Adopting the helper would need a new in-place
variant or a reshaping of what each test asserts on. The static sweep that reported
"no helper gaps" was wrong; this mismatch is the gap.

The hermetic fixture is also the smaller change — one new file rather than five edits —
and it covers `tests/integration/test_watch_cli.py` (which commits at L77-78 without
disabling signing, and which `-m unit` merely deselects) plus every future temp-repo
test, instead of relying on each author remembering the rule. Confirm that integration
test passes rather than assuming it.

Detailed steps: `docs/superpowers/plans/2026-07-30-t1-hermetic-git-test-environment.md`.

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
| `src/retail/cli/parser.py` (tasks.md T012) | `src/seshat/cli/parser.py` |
| `Python 3.11+` (plan.md:42) | Python 3.13+ per `pyproject.toml` |
| CT2 = `design_categorical_distinctness`, CT3 = `design_ramp_deltae` | **Swapped.** Source says `design_ramp_deltae.py:27 → RULE_ID = "CT2"` and `design_categorical_distinctness.py:35 → RULE_ID = "CT3"` |

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
| `.claude/skills/retail-govern/SKILL.md` fix table | **47** rows | **none** |

Set-differenced both ways programmatically, not by hand: **32** manifest ids are
missing from the table — `AP1, CB1, CT1, CT2, CT3, DL3, DL4, DL5, DL6, DL7, DL8, DL9,
DR1, DS1, DS2, DS3, DS4, DS5, HR1, HR4, HR5, HR6, HR7, HR8, HR9, HR11, HR12, HR13,
KP1, KR1, R2, SF1` — and **zero** table rows name an id absent from the manifest. So
the drift is one-directional: the table is a clean stale subset, with no phantom rows
to retire. `grep -rl "retail-govern/SKILL.md"` across `src/` and `tests/` returns
nothing, and no rule id, test, or doc declares the gap intentional.

The consequence is specific: when `seshat check` emits one of those 32 ids, the skill
an agent is told to consult for the fix has no row for it. The engine's own
contributing guide points at that table (`CONTRIBUTING.md:73`). Whole families are
absent — every design-layer id (`CT*`, `DL*`, `DS*`) and every `HR*` id.

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

### Cost warning — price this before sequencing it

Generation is not a mechanical codegen job, and the plan must say so. `registry.py`
stores `id`, `title`, `tier` and **no fix field**, so generating the table means
*authoring* fix guidance as data: 32 new entries written from scratch, plus migrating
the 47 existing prose rows into the same structure. Each entry requires knowing what
the fix for that rule actually is — content work gated on rule knowledge, not
templating.

That plausibly makes T3 larger than T2 and would reorder the sequencing table below.
Two shapes to weigh in the plan: one PR that lands the field, the generator, the guard
and all 79 entries together; or a split where the mechanism lands first with the 47
known rows migrated, and the 32 new entries follow — noting that a guard test cannot
land red, so the guard must arrive with, not before, full coverage.

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
Measured across the 9 fixture JSONs under `tests/fixtures/public_distribution/`: **no**
fixture carries `manifest_digest`; 7 carry `recorded_at`; **3 carry
`source_revision`**. So partial provenance already exists — it is simply not universal
and not asserted. Nothing ties a captured transcript to the bundle it was captured
from, and a change that alters real agent behaviour therefore passes CI on a stale
recording.

### Design

Record provenance on capture and assert it on use, binding to **`manifest_digest`**.

That question is now settled by reading the writer rather than left to planning.
`scripts/export_agent_bundles.py:555` computes
`payload["manifest_digest"] = _sha256(_canonical_json(payload))` — a digest over the
*whole* manifest payload, which already contains `source_revision` **and** every entry's
own sha256. `source_revision` alone is just git HEAD at build time
(`_validated_source_revision`, `:177-186`), so binding fixtures to it would be strictly
wrong in practice: HEAD moves on every commit, so every fixture would read as stale
immediately and the check would be unusable. `manifest_digest` changes only when bundle
content actually changes, which is the property the guard needs. (An earlier draft of
this section recommended `source_revision` because 3 of 9 fixtures already carry it;
that reasoning mistook prior art for authority.)

Then have the consuming tests assert the stamp matches the current bundle, reporting
"this fixture predates the current bundle; re-capture with `--execute-cli`" — a named,
actionable blocker rather than a silent pass.

### Non-goals

Not running live agents in CI. That needs credentials and a CLI install, and the repo
already made that call deliberately. The honest improvement is making staleness
**visible**, not eliminating the manual capture step.

### Testing

The provenance assertion must fail against today's un-stamped fixtures before they are
stamped, for the same reason as T3.

## Track T5 — Make a spec's status a checkable claim

### Problem

`specs/` holds 127 directories whose `**Status**:` lines do not track reality, in both
directions. `specs/131-portfolio-watch` reads "Ratified" while shipping `src/seshat/`
code and tests; `specs/118-cvd-simulation-evidence` reads "Draft" and is genuinely
unbuilt; `specs/104-rename-impact-refactor-guard` reads "Draft" while
`src/seshat/rules/rename_impact_guard.py` is on `main` — a spec about stale references
that is itself stale.

Three facts establish this is unguarded rather than intentionally loose:

- **Nothing reads `specs/` at all.** Greps across `src/seshat/rules/`, `tests/`, and
  `scripts/` return only docstring provenance comments and one test asserting a doc
  does *not* mention `specs/`. No code opens a `specs/**/spec.md` at runtime.
- **No closed vocabulary.** `.specify/templates/spec-template.md` seeds
  `**Status**: Draft` with no enum. Values in the wild include `Draft`, `Approved for
  planning`, `Ratified (…)`, `Implemented (commit …)`, `BUILT (docs-only) …`,
  `Shipped (…)`, `Planned (spec only…)`, and `Finalized -- …`.
- **No structured implementing-artifact field.** Commit shas appear inline inside the
  free-text status value, never as data. Nothing defines what `Ratified` vs
  `Implemented` vs `BUILT` are supposed to mean — not even
  `.specify/memory/constitution.md`.

The cost is concrete and was paid during this very investigation: establishing whether
any track was already built required a tree-verification pass per track, because the
status lines could not be trusted.

### Design

Reuse the shipped mechanism rather than inventing one. Rule **`SC1`**
(`src/seshat/rules/status_claims.py`, spec 050) already reconciles a human-curated
manifest — `docs/quality/status-claims.yaml`, whose entries name a claiming doc, an
anchor sentence, a `claimed-artifact`, and a `claimed-status` — against
`ctx.tracked_files`. A spec claiming completion is exactly that shape: the spec is the
claiming doc, its status line is the anchor, and its implementing module or test is the
claimed artifact. **No new rule is required**, which matters because the
governance/lint lane is saturated and a new rule must be no-finding on `main` before it
can land.

Two parts:

1. **A closed status vocabulary**, documented, with each value's meaning and what
   evidence it requires. This is a governance convention, so it is an owner decision,
   not an agent one — request the ruling early (see Sequencing) so it does not block.
2. **Register completion-claiming specs as `SC1` status claims**, so a spec asserting
   `Implemented`/`Shipped`/`BUILT` must name an artifact that exists, and fails the
   gate when it does not.

The asymmetry is deliberate and must be preserved: an **over-claim** ("Implemented",
artifact absent) is mechanically detectable and is the dangerous direction, because it
causes work to be skipped as already-done. An **under-claim** ("Ratified" for something
that shipped) is *not* mechanically detectable without inferring implementation status,
which would be fabrication. Under-claims are prevented going forward — a spec gains its
artifact pointer when it is implemented — and corrected historically only by a human
reading, one spec at a time.

### Non-goals

Not auto-deriving or auto-flipping any spec's status from tree evidence: that is an
inferred verdict about human intent, and `SC1`'s human-curated manifest exists
precisely to avoid it. Not back-filling all 127 specs in one pass — the plan picks a
bounded first batch, the roughly two dozen specs already claiming
`Implemented`/`Shipped`/`BUILT`, where the claim is explicit and the artifact check is
unambiguous. Not adding a new `seshat check` rule. Not rewriting
`.specify/templates/spec-template.md`'s workflow, only its status field's allowed
values once the vocabulary is ratified.

### Testing

`SC1` already has coverage, so the deliverable is evidence that the new manifest
entries are live: a deliberately-wrong claim (a spec naming a non-existent artifact)
must produce an `SC1` finding, and the real entries must be no-finding on `main`. That
second half is a hard gate — per repo convention a newly-wired check must be
no-finding on `main` before it lands, so any spec whose claim is genuinely false has to
be corrected in the same PR or left out of the first batch.

## Sequencing

| Order | Track | Rationale | Deliverable |
|---|---|---|---|
| 1 | T1 | Makes every later track's "tests pass" claim evidence rather than a caveat; mechanical and zero governance surface | 1 PR |
| 2 | T2 | Design already done and owner-clarified; highest visible value per unit of work | 1 PR |
| 3 | T3 | Independent of T1/T2, but its guard test is easiest to trust once the suite is honestly green | 1 PR |
| 4 | T4 | Packages behaviour the earlier tracks may change; doing it first risks re-stamping twice | 1 PR |
| 5 | T5 | Needs an owner ruling on the status vocabulary, so its *decision* is requested first and its *build* lands last — the ruling has lead time that code work should not wait on | 1 decision + 1 PR |

T1 and T2 are independent of each other and could run in parallel worktrees; T3 and
T4 are independent of everything. The order above optimises for review confidence
rather than wall-clock.

**T3's position is provisional.** Its cost warning above may make it the largest track
rather than the third-smallest; if pricing confirms that, it moves after T4 or splits
in two. Settle that in T3's own plan, not here.

## Governance constraints applying to all tracks

No self-granted approvals; grain, PII, business rollups, and metric policy stay named-
human decisions recorded in `approvals[]`. No numeric confidence, health, or readiness
score anywhere (hard rule #9) — status is `status` + `evidence` + `blocking_reasons`.
The static `seshat check` core stays stdlib-only, with no module-scope `import yaml`
(B1/B3). Secrets stay in `.env`; committed text stays ASCII/UTF-8 without BOM (G3/G4).
Any edit under `skills/**` requires `python scripts/export_agent_bundles.py` followed
by `--check`, and `integrations/**` is never hand-edited. Commit subjects are
`<type>: <description>`, scope-free per rule `P2`.

## Provenance of T5

T5 was not in the original request. It surfaced during this investigation, when
establishing what was already built required a tree-verification pass per track because
the spec status lines could not be trusted. It was recorded as an unscoped candidate,
put to the owner as its own decision, and **accepted on 2026-07-30** — at which point it
was designed above rather than left as a note.

It belongs to the same drift class the repo already guards three other ways: `SC2` for
prose rule counts, `A3` for route-table bijection, and
`tests/unit/test_glossary_rule_table.py` for the glossary table. T5 applies the `SC1`
variant of that pattern to spec status.
