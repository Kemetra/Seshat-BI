# Coordinated release workflow

Seshat BI uses one owner-triggered workflow to prepare one synchronized release pull request for the Python package, Claude Code plugin, and Codex plugin.

The workflow is `.github/workflows/prepare-coordinated-release.yml` and appears in GitHub Actions as **prepare-coordinated-release**.

## What the button does

Given an owner-approved stable version such as `0.2.1`, the workflow:

1. verifies that the run was started from `main`;
2. rejects an existing or non-increasing version/tag/branch;
3. updates `pyproject.toml` as the single version source;
4. updates Claude marketplace metadata;
5. regenerates the Claude and Codex bundles from the reviewed source files;
6. moves the non-empty `[Unreleased]` changelog body into the selected version;
7. runs the repository's version, bundle, and release-candidate checks;
8. creates `release/v<version>` and opens a draft release PR.

It never creates a tag, uploads to PyPI, creates a GitHub Release, or submits either plugin to a public catalog.

## Before running it

- Merge the intended feature/fix PRs into `main`.
- Add truthful entries under `CHANGELOG.md` `[Unreleased]` as those PRs merge.
- Ensure `docs/releases/v<major>.<minor>.md` exists for the selected version line.
- Decide the version as the named owner action required by `versioning-policy.md`.

## Run it

1. Open **Actions** in GitHub.
2. Select **prepare-coordinated-release**.
3. Select **Run workflow**.
4. Keep the branch selector on `main`.
5. Enter a stable version without `v`, for example `0.2.1`.

The result is a draft PR titled `release: prepare v<version>`.

## Review and publish

Review the generated PR, require normal checks, and merge it only when the synchronized diff is correct.

**Merge it with a merge commit. Do not squash and do not rebase.** The workflow builds two commits -- `chore: project v<version> version metadata` and `chore: generate v<version> agent bundles` -- and both generated bundle manifests record the first one by SHA:

```json
"source_revision": "<the version-projection commit>"
```

Squashing collapses the two into one new commit, so the recorded SHA is no longer an ancestor of `main` and `scripts/bundle_provenance.py` fails with `source_revision <sha> is not an ancestor of current HEAD`. `check_release_versions.py` then reports `status: blocked`. Because `release.yml` runs `check_release_versions.py --check` inside `build-validate`, the publish leg fails -- and if the tag was already pushed, it fails *after* an immutable tag exists with nothing published behind it.

If a release PR is squashed by mistake, do not tag. Re-run `python scripts/export_agent_bundles.py` on `main` and merge the restamped manifests in a normal PR first; that repoints `source_revision` at a commit that is genuinely in history. Confirm `python scripts/check_release_versions.py --check` exits zero on `main` before tagging.

After merge:

1. confirm `python scripts/check_release_versions.py --check` exits zero on `main`;
2. create the immutable annotated tag `v<version>` at the merged release commit;
3. run the existing **release-candidate** workflow from that tag with `publication_action=publish-pypi`. Dispatch it *from the tag*, and pass the full ref -- `candidate_ref=refs/tags/v<version>` -- because the workflow asserts `github.ref == candidate_ref` and rejects anything that is not `refs/tags/v*`;
4. create the GitHub Release. `release.yml` publishes to PyPI and npm but does not cut the Release; that is a separate `gh release create v<version>` step;
5. verify all three packages independently -- `seshat-bi` on PyPI, `@kemetra/seshat-bi` on npm, and the unscoped `seshat-bi` alias. The three publishes are ordered but not atomic, so a green PyPI job is not evidence that npm succeeded;
6. verify Claude and Codex repository-plugin update paths.

Claude and Codex repository plugins do not require a separate package upload: their generated bundles and marketplace metadata live in this repository. Public Claude/OpenAI catalog submission remains a separate owner action.

## Common blockers

| Blocker | Required action |
|---|---|
| `[Unreleased]` is empty | Merge and document real changes before preparing a release. |
| Release note file is missing | Add `docs/releases/v<major>.<minor>.md` in a normal reviewed PR. |
| Tag or release branch already exists | Choose a new version; never move or reuse an immutable release. |
| Draft PR creation is denied | Enable repository Actions permission to create pull requests, then rerun. |
| Bot-created PR checks await approval | Approve the displayed workflow runs before merging. |
| `source_revision <sha> is not an ancestor of current HEAD` | The release PR was squashed or rebased. Restamp the bundle manifests onto `main` before tagging; see *Review and publish*. |
