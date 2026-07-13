# Release acceptance checklist: public-beta first success

Use this checklist only when an owner is preparing a real release. It does not authorize publishing.

## Planned evidence files

Store only sanitized evidence, using these stable names, under the release's
reviewed evidence directory:

- `release-candidate.json` -- source revision, version, exact artifact hashes,
  factual status, and blockers.
- `python-artifact-report.json` -- wheel/sdist metadata, contents, rebuild, and
  clean pipx lifecycle results.
- `claude-acceptance.json` and `codex-acceptance.json` -- external fresh-profile
  CLI/IDE observations against the fictional retail fixture.
- `publication-approval-<action>.json` -- named owner, exact candidate, version,
  action, scope, and expiry.
- `rollback-<surface>.json` -- trigger, actor, action, and outcome.

Evidence reports status, facts, and concrete blockers. It MUST NOT contain a
numeric readiness/confidence score or imply that validation grants approval.
Only sanitized durable evidence is committed. Tokens, real account identifiers,
machine paths, raw external-agent transcripts, and real/client data remain in
the ignored private evidence area and follow the platform owner's retention
policy.

- [ ] Owner has selected and recorded the version bump in `pyproject.toml` and `CHANGELOG.md`.
- [x] Baseline audit: `KPI-MC-15` is present exactly once in the canonical registry,
  resolves to `contracts/average-basket-size-units.md`, and is protected by
  `test_kpi_mc_15_exists_exactly_once_and_resolves_to_its_contract`. Do not add a
  duplicate entry.
- [ ] Build exactly one wheel and one source distribution from the tagged source.
- [x] Run the Windows clean-install smoke: `seshat --help`, `init-project`, Git initialization, `status`, `next`, and `check` all pass.
- [x] Confirm `status` / `next` contain no fabricated pass or numeric score.
- [x] Confirm the normal install contains no `dev`, `livetest`, database-driver, or file-reader dependency.
- [x] Verify both `seshat` and legacy `retail` console scripts resolve to `seshat.cli:main`.
- [x] Verify `python -m seshat.cli check` and legacy `python -m retail.cli check` work.
- [x] Validate the plugin manifest, its skill, and all `/seshat-*` commands; use the public marketplace flow only after release.
- [x] Run `seshat check` and `seshat kit-lint` over the release tree.
- [x] Inspect artifacts and tracked changes for secrets, credentials, hostnames, and machine-specific paths.
- [x] Confirm upgrade (`pipx upgrade seshat-bi`) and uninstall (`pipx uninstall seshat-bi`) instructions remain accurate.

macOS and Linux smoke coverage is best-effort beta evidence. Windows is the release gate.

## Five separate release lanes

| Lane | Repository evidence | External authority still required |
|---|---|---|
| Repository implementation | reviewed code, generated bundles, CI, local acceptance classifiers | normal PR review only; grants no publication authority |
| PyPI/GitHub configuration | protected-workflow contract and exact identity tuple | named GitHub/PyPI owner configures environment, reviewer, tag protection, and Trusted Publisher |
| Claude publication | strict plugin validation and external Claude acceptance | repository owner for Git availability; eligible publisher separately for any public catalog |
| Codex publication | current manifest validation plus CLI/IDE acceptance | repository owner for Git availability; verified publisher separately for public submission |
| Irreversible release | exact SHA/version/digest evidence pack | a fresh named-owner decision for each tag, upload, release, submission, or rollback action |

Configuration, a green check, merge approval, or a prior decision cannot approve
another lane.

## Action-scoped decision placeholders

Every row defaults to **not approved**. An owner records a separate sanitized
`publication-approval-<action>.json` only after reviewing the exact immutable
candidate. Do not change a row based on an agent recommendation.

| Action | Default | Required binding before execution |
|---|---|---|
| configure GitHub `pypi` environment/tag protection | not approved | named eligible repository owner, exact repository/workflow/environment |
| configure PyPI Trusted Publisher | not approved | named package owner, exact repository/workflow/environment tuple |
| approve candidate version | not approved | SemVer, full source SHA, all candidate digests, zero release blockers |
| create immutable tag | not approved | exact candidate/version and `create_release_tag` action |
| publish PyPI artifacts | not approved | exact wheel/sdist digests and `publish_pypi` action |
| publish GitHub Release | not approved | exact tag and `publish_github_release` action |
| make Claude repository marketplace available | not approved | passing external Claude public-path evidence |
| submit/publish any Claude public catalog entry | not approved | separate eligible-publisher decision and current requirements |
| make Codex repository marketplace available | not approved | passing external Codex CLI and IDE public-path evidence |
| submit/publish through OpenAI's public plugin process | not approved | separate verified-publisher decision and current requirements |
| contain/rollback one affected surface | not approved | new surface-specific rollback approval; replacement not included |

## Actual availability record

For Python, Claude repository, Codex repository, Claude public catalog, and the
OpenAI public plugin listing, record exactly one of `available`, `unavailable`,
`unverified`, or `blocked`. Every non-available state needs a concrete reason.
The coordinated release is not `available` until Python plus both repository
agent distributions have clean public-path evidence.

## Repository candidate evidence (2026-07-13)

- [x] Full repository suite passes: 2,235 tests passed and 9 optional tests
  skipped on Windows/Python 3.13; the MCP contract extra was installed for the
  complete contract run.
- [x] Ruff formatting and lint pass across 399 repository Python files,
  including the release/export/acceptance scripts now enforced by CI.
- [x] `seshat check`, `seshat semantic-check --repo .`, and `seshat kit-lint`
  pass without governance, semantic, or projection drift.
- [x] Exactly one candidate wheel and one sdist build successfully; strict Twine
  validation, content inspection, and isolated sdist-to-wheel rebuild pass.
- [x] The Windows isolated pipx lifecycle passes install, first success,
  dependency exclusion, upgrade, uninstall, command removal, and project
  preservation.
- [x] Deterministic Claude and Codex bundles validate against their distinct schemas.
- [x] Installed Claude Code strict validator accepts the root marketplace and plugin.
- [x] Current Codex plugin validator accepts the skills-only plugin.
- [x] Credential-free synthetic acceptance classification passes for Claude CLI,
  Codex CLI, and Codex IDE fixtures with semantic parity.
- [x] Authorization/rollback contracts reject mismatched, expired, reused, or
  cross-action approvals.
- [ ] Real external public GitHub/PyPI/Claude/Codex installation evidence is
  intentionally absent until the repository implementation is merged and the
  applicable named owner authorizes that external action.

These are pre-publication repository facts, not final tagged-candidate or public
installation evidence. The credential-free audit remains truthfully blocked by
the historical `v0.1.0` tag pointing to a different immutable revision; version
selection and every public action remain owner-only.
