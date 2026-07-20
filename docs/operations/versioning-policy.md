# Versioning Policy -- the version scheme for a governance kit, and who bumps it

- **Status:** Authored (the FR-001 deliverable of spec 108; docs-only, no runtime
  code, no CI config, no `seshat check` rule).
- **Authority category:** Maintenance Automation *(sub-axis: none / `--`)* -- per
  `docs/architecture/product-modules.md` (the five-category contract, F024 / on-disk
  spec 018). This policy is read/authored by a human; it defines no CLI verb and
  carries no Module capability level and no Adapter connectivity level.
- **Roadmap feature:** M11 (Distribution and Release Maturity), roadmap
  `docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md`. **On-disk spec:**
  `specs/108-release-distribution-maturity`.
- **Readiness stage affected:** none directly (see the closing section).

## What this is

Seshat BI is not an ordinary library -- it is a **governance kit**: the thing being
versioned is a bundle of `seshat check` rules, CLI verbs, and templates that other
repos depend on to gate their own readiness. A version bump communicates blast radius
to a consumer repo pinning this package, exactly as it would for any dependency (see
`docs/operations/dependency-update-policy.md`, which classifies incoming updates by
lane). This policy is the mirror image: it classifies **outgoing** changes to Seshat
BI itself, so a consumer can trust the number.

## Where the version lives

The version is the single value at `pyproject.toml` `[project].version`. There is no
second source of truth -- no `__version__` string duplicated in `src/seshat/`, no
version baked into a template. A future `seshat --version` (if built) reads this same
field at runtime rather than hardcoding a copy.

For a distribution candidate, that owner-selected value is projected into every
public surface by deterministic tooling. The governed projections are:

- Python wheel/sdist filenames and core metadata;
- Claude plugin manifest, root marketplace metadata, and generated bundle manifest;
- Codex plugin manifest and generated bundle manifest (plus catalog metadata only
  when the current official schema permits a version field);
- the exact changelog heading, release-note path/heading, proposed `v<version>` tag,
  and GitHub Release tag/title.

`scripts/check_release_versions.py` compares these locations and reports concrete
blockers. A missing field, mismatch, release note, or conflicting existing tag fails
closed. Its `pass` means only that projections agree; it never selects the version or
authorizes a tag, upload, release, catalog publication, or OpenAI public plugin
submission.

Generated bundle provenance uses the immutable version-projection commit. Coordinated
release preparation first commits `pyproject.toml`, the root marketplace version, and
the frozen changelog; the exporter then records that commit as `source_revision` and
verifies locally that its canonical `project.version` equals the bundle version. A
second commit records the generated Claude and Codex bundles. The final generated
commit cannot be its own provenance revision because embedding that commit hash in the
manifest would create a self-referential hash cycle. Release PRs therefore preserve
both commits with a merge commit; squash or rebase merging invalidates the recorded
projection revision and fails provenance validation.

## Who bumps it

**The owner bumps the version.** A version bump is a human, named decision -- never
self-granted by the agent (Principle V, `never_self_grant_approval`; hard rule #9
applies to version claims exactly as it does to a confidence score: no fabricated
maturity number). An agent may PROPOSE a bump (stating the scheme rule it believes
applies and the changes since the last tag) but does not edit `pyproject.toml`'s
version field on its own authority. For Public Beta, the decision record binds the
selected value to the candidate source revision and validated artifact digests. That
version decision is distinct from the later, action-scoped approvals to create a tag,
publish Python artifacts, publish a GitHub Release, publish the Claude catalog, or
submit/publish through OpenAI's public plugin process.

## The scheme: semver, kit-specific bump rules

Seshat BI follows [Semantic Versioning 2.0.0](https://semver.org/) (`MAJOR.MINOR.PATCH`),
with the bump classification adapted to what actually changes blast radius for a
**governance kit** rather than a library API:

| Change class | Bump | Why |
|---|---|---|
| A NEW `seshat check` rule is registered (the rule set grows) | **MINOR** | Additive. A consumer who was passing keeps passing until they touch the newly-covered surface; the new rule fires only on a pattern that was previously ungoverned. Expected kit growth -- a consumer who wants to defer adopting it can pin the prior minor. |
| A rule's **behavior changes** such that it can newly fail a previously-passing repo (a broadened predicate, a new failure mode inside an existing rule id, a severity change from `warning` to blocking) | **MAJOR** | Breaking. The rule id a consumer already adopted now judges their already-green repo differently. This is the exact shape semver's MAJOR clause exists for: an existing, relied-upon contract changed underneath the consumer without them opting in. |
| A NEW CLI verb, or a new optional flag on an existing verb, with no change to existing verb behavior | **MINOR** | Additive surface. |
| A CLI verb's existing flag/output contract changes (e.g. `--format text` output shape changes, a flag is removed or renamed, an exit-code meaning changes) | **MAJOR** | Breaking for any consumer/script parsing that output. |
| Docs-only change (a `docs/` file, a template, a skill's prose) | **PATCH** | No governed behavior changed. |
| Tests-only change (new test, refactored test, no `src/seshat/` behavior change) | **PATCH** | No governed behavior changed. |
| A bug fix that makes a rule correctly fail something it should already have caught (the rule's *documented* intent did not change; a defect in matching it did) | **PATCH** | Restores intended behavior; still MAY newly fail a repo that was accidentally passing due to the bug -- if that blast radius is judged large, the owner may instead classify it MINOR or MAJOR at their discretion (this table states the default, not an unbreakable formula). |
| A dependency bump inside `pyproject.toml` (`pyyaml`, an optional extra's driver) | **PATCH** unless the dependency bump itself is Lane B/C under `docs/operations/dependency-update-policy.md`, in which case it is at minimum **MINOR** and the lane's required review applies first. | Mirrors the existing dependency-update lane table; this policy does not re-derive it. |

### The additive-rule vs. behavior-change line, stated once

A **new rule id** is MINOR even though, mechanically, it can also turn a
previously-green consumer repo red -- the same observable effect a MAJOR change has.
The distinction is not "can it fail something," it is **which contract moved**:

- A new rule id is a *new* contract the consumer has not adopted a specific version
  against yet; they encounter it as part of adopting the newer minor, same as gaining
  a new opt-in lint rule.
- A behavior change to an *existing* rule id changes a contract the consumer already
  built process around at a specific version. That is the break semver protects
  against.

If a change is ambiguous between the two (e.g. a rule id is deprecated and replaced by
a near-identical one with a different id), treat it as MAJOR and say so explicitly in
the changelog entry -- ambiguity resolves toward the safer (larger) bump, never the
smaller one.

## No fake confidence (hard rule #9)

This policy assigns no "maturity score" or "stability rating" beyond the semver
number itself. A version number is a discrete, owner-approved classification -- never
a computed or fabricated confidence value. `docs/operations/dependency-update-policy.md`
states the same discipline for incoming dependency updates; this is its outgoing
mirror.

## What this policy MUST NOT do

- Auto-bump the version from CI or from an agent's own decision (Principle V).
- Publish to any package index -- that is a separate owner decision, out of scope for
  this spec (see `specs/108-release-distribution-maturity/spec.md`, "Out of scope").
- Retroactively re-tag or renumber a version once released.
- Skip a bump class because a change is "small" -- the table's classification is by
  blast radius, not by diff size.

## See also

- `CHANGELOG.md` -- records what changed at each version, per Keep a Changelog.
- `docs/operations/dependency-update-policy.md` -- the mirror-image policy for
  *incoming* dependency/adapter updates (the lane table).
- `pyproject.toml` -- the single source of truth for the current version.
- `scripts/install_smoke_test.py` -- proves a built artifact at the current version
  installs and its console scripts resolve (FR-003).
- The spec: `specs/108-release-distribution-maturity/spec.md`.
