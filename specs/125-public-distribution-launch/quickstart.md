# Quickstart: validate the Public Beta repository candidate without publishing

**Status:** implemented and locally validated on 2026-07-13.

This path does not configure an account, approve a version, tag, upload,
publish, submit a plugin, or run a rollback. Expected release blockers remain
blockers; repository validation is not publication approval.

## 1. Confirm source identity

From a clean checkout of the candidate revision:

```powershell
git status --short
git rev-parse HEAD
git tag --points-at HEAD
python scripts/release_candidate_audit.py --repository-check --output release-staging/release-candidate.json
```

The repository check must pass. The overall candidate may truthfully remain
`blocked`: the current `0.1.0` value already has an immutable historical tag at
another revision, and no owner has approved a replacement version. Do not move
that tag or silently choose a version.

## 2. Verify deterministic public knowledge

```powershell
python scripts/export_agent_bundles.py --check
python -m pytest tests/contract/test_public_knowledge_allowlist.py tests/contract/test_generated_agent_bundles.py -q
```

Edit only canonical Knowledge Bases, the explicit allowlist, or bundle
templates; then regenerate. Never repair `integrations/*/seshat-bi/` by hand.

## 3. Validate both native agent distributions

```powershell
claude plugin validate .claude-plugin/marketplace.json --strict
claude plugin validate integrations/claude-code/seshat-bi --strict
python scripts/external_agent_acceptance.py --platform claude-code --validate-bundle
python scripts/external_agent_acceptance.py --platform codex --validate-bundle
python -m pytest tests/contract/test_claude_plugin_bundle.py tests/contract/test_codex_plugin_bundle.py tests/integration/test_external_agent_acceptance.py -q
```

Run the current Codex plugin validator against
`integrations/codex/seshat-bi` when that validator is installed. Claude and
Codex must use their own manifests; both must project identical canonical
knowledge provenance and the same governed outcome class.

Credential-free fixture classification is CI evidence, not real public-install
evidence. The latter is recorded only after an external fresh-profile run.

## 4. Build and inspect Python artifacts

```powershell
python -m build --wheel --sdist --outdir dist
python -m twine check --strict dist\*
python scripts/inspect_release_artifacts.py --dist dist --output release-staging/python-artifact-report.json
python -m pytest tests/contract/test_release_artifact_contents.py tests/integration/test_python_release_artifacts.py -q
```

The inspector requires exactly one wheel and one sdist, compares their metadata
and contents, scans prohibited material, and rebuilds the wheel from the sdist
in isolation by default.

## 5. Exercise the full isolated pipx lifecycle

```powershell
python scripts/install_smoke_test.py
```

This builds local candidate artifacts in a temporary directory, installs with
an isolated pipx home, checks both commands and dependencies, creates a new
project, upgrades, uninstalls, verifies command removal, and proves the project
is unchanged. Windows is blocking beta evidence; Linux/macOS CI is best effort.

## 6. Validate authorization and rollback boundaries

```powershell
python -m pytest tests/contract/test_release_workflow.py tests/contract/test_publication_authorization.py tests/integration/test_release_authorization_and_rollback.py -q
```

Expected: validation is the workflow default; build jobs have no OIDC authority;
publication requires the protected `pypi` environment, exact same-run artifacts,
matching protected tag/ref, and verified digests. Approval reuse, scope mismatch,
partial-launch wording, and rollback without reapproval fail.

## 7. Run repository gates

```powershell
ruff format --check src tests
ruff check src tests
pytest
seshat check
seshat semantic-check --repo .
seshat kit-lint --repo .
```

Attach only sanitized status/count evidence to the release checklist. Do not
commit raw external-agent transcripts, tokens, real PII/client data, DSNs, or
machine-specific paths.

## 8. Stop at the owner boundary

At this point the implementation can be reviewed and merged. External
configuration, version selection/projection, tag creation, PyPI/GitHub release,
public Claude/Codex installation verification, public submission, and rollback
remain separate named-owner actions. A replacement release requires a new
version and a complete new gate cycle.
