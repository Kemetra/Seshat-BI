# Research: Seshat BI Public Beta Distribution

**Date**: 2026-07-13
**Scope**: Research and decisions only; no implementation or publication

## Baseline Findings

### Decision: treat current `main` as complete baseline

- Baseline revision inspected: `785299e` (`feat: add generic KPI contract authoring support (spec 124) (#264)`).
- The authoritative `skills/retail-kpi-knowledge/registry.yaml` contains `KPI-MC-15` and points to `contracts/average-basket-size-units.md`.
- `skills/retail-kpi-knowledge/references/id-conventions.md` also projects `KPI-MC-15`.
- Existing KR1 tests validate the registry count/shape but do not explicitly pin the reported identifier. The remaining work is audit evidence and an explicit regression assertion, not another registry entry.

**Rationale**: Recreating merged Spec 124 work would risk duplicate identifiers and violate the owner's baseline constraint.

### Decision: publication history must be reconciled before version approval

- `pyproject.toml` reports `0.1.0`.
- The repository already contains an annotated `v0.1.0` tag.
- `CHANGELOG.md` includes wording that no prior tag/release exists.
- Current public package-index ownership/availability could not be conclusively established from the no-account research context and must be rechecked by the owner immediately before Trusted Publisher configuration.

**Rationale**: A version cannot be safely reused or described as first-tagged when the immutable repository tag already exists. The likely additive-change proposal is `0.2.0`, consistent with the repository's minor-version policy, but only the named owner may ratify it.

**Rejected alternative**: Delete or move `v0.1.0`. Tags are release evidence and moving/deleting them would be an irreversible owner action that can break consumers.

## Python Distribution

### Decision: strengthen metadata and validate wheel and sdist as public products

The current package declares name, version, description, Python range, license expression, runtime dependency, entry points, and selected force-included demo resources. The release candidate must add/verify readme metadata, public URLs, classifiers/license file policy, and exact contents. Build exactly one wheel and one sdist; run `twine check --strict`; rebuild a wheel from the sdist in isolation; compare metadata/content expectations; and scan both artifacts for prohibited material.

The normal install must retain only `PyYAML` as a mandatory runtime dependency. Database drivers, browser tooling, test/build tools, and other extras remain opt-in.

**Rationale**: A wheel-only smoke can pass even when the sdist is incomplete or metadata fails on the package index. The sdist is an independent public artifact.

**Official sources**:

- [Twine documentation](https://twine.readthedocs.io/en/stable/)
- [Python Packaging User Guide: package publication with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

### Decision: expand pipx smoke into a lifecycle test

Use throwaway pipx homes and temporary projects to test clean install, both entry points, first-success behavior, upgrade from the prior supported artifact, uninstall, command removal, and project preservation. Keep Windows blocking. Declare Linux/macOS status in release policy rather than allowing an unlabeled `continue-on-error` result to imply support.

**Rationale**: Public Beta acceptance covers the user lifecycle, not merely whether a wheel can be imported.

### Decision: use protected PyPI Trusted Publishing

Build and validation run without publication credentials. A distinct publish job downloads only the validated immutable distribution artifact, is bound to the canonical repository/workflow/environment, and alone receives `id-token: write`. The GitHub `pypi` environment requires a named eligible reviewer. Package-name/owner checks and Trusted Publisher registration are manual external configuration tasks.

**Rationale**: PyPI Trusted Publishing uses short-lived OIDC identity rather than a long-lived API token. PyPA explicitly recommends manual approval for the `pypi` environment.

**Official sources**:

- [PyPI: Publishing with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [PyPI Trusted Publisher security model](https://docs.pypi.org/trusted-publishers/security-model/)
- [Python Packaging User Guide: GitHub Actions publication](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

## Canonical Knowledge and Deterministic Export

### Decision: one explicit allowlist, one exporter, two native bundles

The canonical Knowledge Base entrypoints remain:

- `skills/bi-sql-knowledge/SKILL.md`
- `skills/bi-dax-knowledge/SKILL.md`
- `skills/bi-python-knowledge/SKILL.md`
- `skills/bi-bigdata-knowledge/SKILL.md`
- `skills/retail-kpi-knowledge/SKILL.md`

`distribution/public-knowledge-allowlist.yaml` will explicitly enumerate every public file and permitted destination. A single Python exporter applies reviewed platform templates, copies allowlisted canonical content, normalizes generated JSON/YAML/Markdown, and writes stable SHA-256 manifests. CI regenerates into temporary directories and compares them with committed public bundles.

**Rationale**: Explicit enumeration makes inclusion a review decision. A common exporter prevents Claude/Codex knowledge drift while platform templates preserve manifest/layout differences.

**Rejected alternatives**:

- **Recursive directory copy**: silently publishes newly added or client-specific files.
- **Symlinked bundle content**: installed plugins may omit or dereference targets differently, and external consumers do not have the development tree.
- **Hand-maintained duplicated Knowledge Bases**: creates multiple sources of truth and non-reviewable drift.
- **Generate only during release**: public Git/subdirectory installs need the self-contained bundle present at the selected revision.

## Claude Code

### Decision: keep one root marketplace and make the plugin self-contained

The canonical repository root `.claude-plugin/marketplace.json` is the public marketplace. The duplicate integration-local marketplace is removed or made non-authoritative. Its `seshat-bi` entry points to `integrations/claude-code/seshat-bi`. Skills and commands stay at the plugin root; only `plugin.json` stays inside `.claude-plugin/`.

The installed plugin must include its operating contract and knowledge payload. It cannot require workspace `AGENTS.md`, `CLAUDE.md`, a development checkout, or parent-directory references. Fresh-workspace acceptance tests the documented GitHub marketplace add/install/update flow.

**Rationale**: Claude Code copies marketplace plugins to an isolated cache and installed plugins cannot reference files outside their plugin root.

**Official sources**:

- [Claude Code: plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [Claude Code: plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Claude Code: discover and install plugins](https://code.claude.com/docs/en/discover-plugins)

### Decision: repository installation and public-catalog submission are separate

Public GitHub marketplace installation is the primary release path. Any submission to Anthropic's official catalog is an optional, separately approved owner action whose current form, eligibility, and review requirements must be rechecked at execution time.

## Codex

### Decision: use Codex-native skills and plugin structure

Official current guidance distinguishes repository instructions, repository skills, plugins, and catalogs:

- Codex discovers repository skills under `.agents/skills/<skill>/SKILL.md`.
- A plugin uses `.codex-plugin/plugin.json` and may point to `skills/`.
- A minimal skill is `skills/<skill-name>/SKILL.md` with `name` and `description` frontmatter.
- CLI/IDE users can explicitly invoke a skill by typing `$` or using `/skills`.
- A repository catalog is `.agents/plugins/marketplace.json` and resolves plugin source paths relative to repository root.
- Public review uses OpenAI's current public plugin submission process and portal.

Create `integrations/codex/seshat-bi/` as a skills-only plugin with no implicit MCP server, connector, app, or hook. Add `.agents/plugins/marketplace.json` as the repository catalog. Keep root `AGENTS.md` compatible with Codex repository discovery, but carry the portable Seshat operating contract inside the plugin skill for fresh workspaces.

**Rationale**: A skills-only plugin is the narrowest public reusable unit and avoids unnecessary network/service permissions. It preserves `$` invocation in CLI/IDE and is eligible for a separate owner-approved public plugin submission.

**Rejected alternatives**:

- **Rename/copy Claude plugin**: manifest and component rules differ.
- **Ship only `AGENTS.md`**: it is repository guidance, not an installable portable bundle.
- **Call OpenAI's public process a marketplace or directory**: current official terminology is public plugin submission/review/listing; “marketplace” is retained only for repository/personal catalog commands and files.
- **Add MCP/app wiring now**: the Knowledge Bases and governed workflow need no remote service, so it would broaden permissions and publication review without user value.

**Official sources**:

- [OpenAI: Build plugins](https://developers.openai.com/codex/plugins/build)
- [OpenAI: Build skills](https://developers.openai.com/codex/skills)
- [OpenAI: AGENTS.md discovery](https://developers.openai.com/codex/guides/agents-md)
- [OpenAI: Submit plugins](https://learn.chatgpt.com/docs/submit-plugins)

### Decision: repository distribution and OpenAI public plugin submission are separate

The public repository catalog/plugin may be installable before directory review. Submission requires a publisher with Apps Management Write access, a verified individual/business identity, listing and support/privacy/terms data, tests, policy attestations, and review. Those external facts and eligibility must be owner-verified at submission time.

## Cross-Agent Acceptance

### Decision: one synthetic truth table, separate platform runners

Use one fictional retail fixture and expected-outcome matrix across Python, Claude, and Codex. It contains enough structure to demonstrate inspection and deliberately includes ambiguous grain and PII-shaped fields. Expected outcomes are next-action classes and blockers, never exact prose or a score. Platform-specific runners record versions, source revision, install source, invocation, evidence, and output classification.

The tests fail if either agent invents a mapping, reveals a synthetic PII value unnecessarily, writes silver SQL before approval, skips a readiness gate, claims a live pass without a DSN, or self-grants approval.

**Rationale**: Shared input/outcome rules test semantic parity without requiring byte-identical natural-language responses.

## Version Synchronization and Rollback

### Decision: one proposed version projected everywhere, approval still external

The implementation will use the Python project version as the machine-readable candidate source and verify all projections: Claude manifest/catalog, Codex manifest/catalog, bundle manifests, changelog/release-note heading, proposed tag, and GitHub Release title. A version proposal is not an approved release; a named-owner decision record binds the approved value to one immutable source revision and artifact digest set.

### Decision: rollback is containment plus truthful status, never overwrite

- PyPI: yank the affected version where appropriate; never replace files for an existing version.
- GitHub: preserve/revise release evidence; do not move the immutable tag to different source.
- Claude/Codex repository distribution: revert the catalog/plugin pointer or corrective commit and document the actually available version.
- Official directories: use the platform's correction/withdrawal flow under owner authority.
- Replacement: approve a new version, rebuild, rerun every gate, and republish.

**Rationale**: Package indexes and release tags are immutable identity boundaries. Rollback evidence grants no replacement-release approval.

## Open Checks Reserved for Execution

- Confirm `seshat-bi` project name availability/ownership and exact publication history from the owner's package-index account.
- Confirm the named GitHub environment reviewer is eligible under the repository's plan and ownership model.
- Recheck exact Claude Code and Codex CLI/IDE versions and current manifest validators.
- Recheck public-catalog submission terminology, eligibility, forms, and policy documents immediately before submission.
- Approve the actual Public Beta version and immutable source only after all repository evidence passes.
