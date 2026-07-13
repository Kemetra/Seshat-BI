# Quickstart: Validate a Public Beta Candidate Without Publishing

**Audience**: future implementer/release maintainer
**Status**: planned workflow; referenced scripts/options do not exist until the tasks are implemented
**Safety**: this quickstart builds and validates locally/CI only. It does not tag, upload, publish, configure an account, submit a plugin, or record approval.

## 1. Establish the immutable candidate facts

Start from a clean checkout of the candidate revision and record:

```powershell
git status --short
git rev-parse HEAD
git tag --points-at HEAD
python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"
```

Expected: clean status; a full SHA; one proposed SemVer. A tag is not created by this flow. If `v{version}` already exists at another revision or publication history is unresolved, stop with a concrete blocker.

Run the planned release-blocker and version checks:

```powershell
python scripts/check_release_versions.py --check --source-revision (git rev-parse HEAD)
python -m pytest tests/unit/test_rule_kr1.py -q
```

Expected: every version projection matches; `KPI-MC-15` exists once and resolves to its canonical contract. No pass is inferred from missing evidence.

## 2. Generate and prove the agent bundles

```powershell
python scripts/export_agent_bundles.py --check
python -m pytest tests/contract/test_public_knowledge_allowlist.py tests/contract/test_generated_agent_bundles.py -q
```

Then export twice into two fresh temporary roots and compare the reported file lists and SHA-256 digests:

```powershell
python scripts/export_agent_bundles.py --output-root "$env:TEMP\seshat-export-a"
python scripts/export_agent_bundles.py --output-root "$env:TEMP\seshat-export-b"
```

Expected:

- both trees are byte-stable;
- every output has allowlist or reviewed-template provenance;
- no symlink, secret, PII/client value, absolute path, cache, or unlisted file appears;
- all references resolve inside each plugin root;
- committed generated bundles match regeneration.

Do not repair drift by editing `integrations/*/seshat-bi/knowledge/`. Edit the canonical source/allowlist/template and regenerate.

## 3. Build and inspect Python artifacts

Use a clean isolated build environment:

```powershell
python -m build
python -m twine check --strict dist\*
python scripts/inspect_release_artifacts.py --dist dist --strict
python -m pytest tests/contract/test_release_artifact_contents.py -q
```

Expected: exactly one wheel and one sdist, matching metadata/version, complete readme/license/URLs, only declared runtime dependencies, and no prohibited content.

Rebuild from the sdist in another isolated environment and compare governed wheel metadata/content:

```powershell
python scripts/inspect_release_artifacts.py --dist dist --rebuild-sdist --strict
```

Any extra/missing artifact, Twine warning, rebuild dependency on the checkout, or unexplained content difference blocks the candidate.

## 4. Exercise clean pipx install, upgrade, and uninstall

Run the blocking Windows lifecycle smoke with throwaway pipx and project roots:

```powershell
python scripts/install_smoke_test.py --wheel dist\<candidate>.whl --lifecycle --strict
```

The implemented smoke must prove:

1. normal install contains no optional database/browser/dev/test engines;
2. `seshat` and `retail` resolve and report the candidate version;
3. a new project reports the earliest truthful governed action with evidence/blockers and no score;
4. upgrade from the prior supported artifact preserves project files;
5. uninstall removes the package and both commands while leaving the project intact.

The CI policy must label which other operating systems are blocking or informational.

## 5. Run Claude acceptance outside the repository

Create an isolated Claude profile and temporary workspace with no `AGENTS.md`, `CLAUDE.md`, or Seshat checkout. Use the exact current public GitHub marketplace add/install flow documented by implementation.

```text
add canonical marketplace
install seshat-bi
reload/refresh
discover skill and commands
inspect distribution/synthetic-retail fixture copied into external workspace
attempt gate-skipping prompt
update, then uninstall/rollback
```

Record the evidence fields in [External Claude Acceptance](contracts/external-claude-acceptance.md). Expected: the plugin loads its own operating contract/knowledge, returns the earliest governed action or concrete stop, and never invents mapping/approval or leaves the plugin root.

This pre-release run may use an immutable candidate Git ref through the same external installation mechanism. The post-publication run must use only the documented public source/version.

## 6. Run Codex CLI and IDE acceptance outside the repository

Create isolated Codex profiles and the same external workspace. Use the current official catalog/plugin flow:

```text
add/resolve canonical repository catalog
install seshat-bi
discover skills
invoke $seshat-bi
invoke one exported knowledge skill
run the synthetic inspection and gate-skipping scenarios in CLI
repeat in the supported IDE extension
update, then uninstall/rollback
```

Record [External Codex Acceptance](contracts/external-codex-acceptance.md), including product versions and `$` invocation evidence. Expected semantic outcome must match Claude even when wording differs.

Do not describe this repository catalog as acceptance into OpenAI's public Plugins Directory.

## 7. Assemble the no-publication evidence pack

The planned evidence pack contains:

- candidate full SHA and proposed version;
- registry audit including `KPI-MC-15`;
- version-sync result;
- wheel/sdist/bundle filenames and SHA-256 digests;
- metadata/content/sdist-rebuild results;
- Windows pipx lifecycle result and declared cross-platform status;
- Claude and Codex external acceptance records/parity matrix;
- zero unresolved blockers or a concrete blocked result;
- owner-action checklist with no approval pre-filled.

At this point stop. `validated` is not `approved`.

## 8. Owner-only configuration and release runbook (not executed here)

After separately reviewing the evidence, named owners may perform the distinct actions below under [Publication Authorization Boundary](contracts/publication-authorization-boundary.md):

1. verify the PyPI project name/ownership and configure the exact Trusted Publisher identity;
2. configure GitHub tag protections and a `pypi` environment with named reviewer approval;
3. approve the version and immutable candidate;
4. separately authorize tag creation, PyPI upload, and GitHub Release publication;
5. separately decide whether/when to submit Claude and Codex to their official public directories.

No step inherits authority from the prior step.

## 9. Post-publication verification and rollback

For each actually published surface, immediately repeat its clean external public path and record exact version/source/timestamp. Documentation must mark unpublished or pending-review surfaces truthfully.

If verification fails:

- stop further surface publication;
- preserve defect and candidate evidence;
- obtain owner approval for affected-surface containment;
- yank/withdraw/revert a pointer or correct public wording as the channel permits;
- never overwrite a package file or move a tag to new source;
- choose a new proposed version for replacement;
- rerun all validation, approval, publication, and public-verification gates.

Rollback grants no approval for the replacement release.
