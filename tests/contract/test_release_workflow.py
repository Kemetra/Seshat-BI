from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_build_job_is_unprivileged_and_hands_off_exact_validated_artifacts() -> None:
    workflow = _workflow()
    assert workflow["permissions"] == {}
    build = workflow["jobs"]["build-validate"]
    assert build["permissions"] == {"contents": "read"}
    assert "id-token" not in build["permissions"]
    rendered = WORKFLOW.read_text(encoding="utf-8")
    assert "inspect_release_artifacts.py" in rendered
    assert "--require-release-ready" in rendered
    assert "if-no-files-found: error" in rendered
    assert "compression-level: 0" in rendered
    assert "SOURCE_REVISION" in rendered


def test_publish_job_uses_protected_environment_oidc_and_exact_handoff() -> None:
    workflow = _workflow()
    publish = workflow["jobs"]["publish-pypi"]
    assert publish["needs"] == "build-validate"
    assert publish["environment"] == "pypi"
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    rendered = WORKFLOW.read_text(encoding="utf-8")
    # SHA-pinned (security finding `actions-tag-pinned-not-sha`): the publish
    # action must be a 40-char commit SHA, never the mutable `@release/v1` branch,
    # because it runs in the `id-token: write` OIDC-privileged job.
    assert "pypa/gh-action-pypi-publish@release/v1" not in rendered
    assert re.search(r"pypa/gh-action-pypi-publish@[0-9a-f]{40}\b", rendered), (
        "publish action must be pinned to a 40-char commit SHA"
    )
    assert "sha256sum --check SHA256SUMS" in rendered
    assert "refs/tags/v*" in rendered
    reject_step = next(
        step
        for step in publish["steps"]
        if step["name"] == "Reject forks and non-tag publication"
    )
    assert reject_step["env"] == {
        "ACTUAL_REPOSITORY": "${{ github.repository }}",
        "CANDIDATE_REF": "${{ inputs.candidate_ref }}",
        "REF_PROTECTED": "${{ github.ref_protected }}",
        "RUN_REF": "${{ github.ref }}",
    }
    assert 'test "$REF_PROTECTED" = "true"' in reject_step["run"]
    assert 'test "$RUN_REF" = "$CANDIDATE_REF"' in reject_step["run"]
    assert "password:" not in rendered
    assert "PYPI_API_TOKEN" not in rendered
    # Slice the publish-pypi job ONLY -- not "everything after its heading".
    # The guarantee below is that the PyPI job publishes exactly the artifact
    # `build-validate` handed it and never a fresh checkout it could rebuild
    # from. That is a property of THIS job; a later job (publish-npm) legitimately
    # checks out the tag to build a different artifact, and an open-ended slice
    # would read its steps as violations of a rule that was never about it.
    pypi_onward = rendered.split("  publish-pypi:", 1)[1]
    publish_text = pypi_onward.split("\n  publish-npm-scoped:", 1)[0]
    assert "actions/checkout" not in publish_text
    assert "github.run_id" in publish_text
    assert "grep -Eq '^[0-9a-f]{40}$' SOURCE_REVISION" in publish_text
    publish_step = publish["steps"][-1]
    assert publish_step["with"]["packages-dir"] == "release-staging/dist/"
    assert "release-staging/dist -maxdepth 1 -type f" in rendered
    assert "cp dist/*.whl dist/*.tar.gz release-staging/dist/" in rendered


def test_untrusted_dispatch_ref_is_not_interpolated_into_bash() -> None:
    workflow = _workflow()
    build = workflow["jobs"]["build-validate"]
    identity_step = next(
        step for step in build["steps"] if step.get("name") == "Verify source identity"
    )
    assert identity_step["env"] == {"CANDIDATE_REF": "${{ inputs.candidate_ref }}"}
    assert "${{ inputs.candidate_ref }}" not in identity_step["run"]
    assert '"$CANDIDATE_REF^{commit}"' in identity_step["run"]

    publish = workflow["jobs"]["publish-pypi"]
    reject_step = next(
        step
        for step in publish["steps"]
        if step["name"] == "Reject forks and non-tag publication"
    )
    assert "${{ inputs.candidate_ref }}" not in reject_step["run"]


def test_validation_is_default_and_publish_has_no_implicit_approval() -> None:
    workflow = _workflow()
    triggers = workflow.get("on", workflow.get(True))
    action_input = triggers["workflow_dispatch"]["inputs"]["publication_action"]
    assert action_input["default"] == "validate-only"
    assert workflow["jobs"]["publish-pypi"]["if"] == (
        "${{ inputs.publication_action == 'publish-pypi' }}"
    )
    rendered = WORKFLOW.read_text(encoding="utf-8")
    assert "environment: pypi" in rendered
    assert "environment: production" not in rendered


def test_npm_packages_are_prebuilt_handed_off_and_published_in_resumable_jobs() -> None:
    """An alias retry must not republish an immutable scoped npm version."""

    workflow = _workflow()
    jobs = workflow["jobs"]
    build_steps = "\n".join(
        str(step.get("run", "")) for step in jobs["build-validate"]["steps"]
    )

    assert (
        "node npm/stage-release-packages.js --output release-staging/npm" in build_steps
    )

    scoped = jobs["publish-npm-scoped"]
    alias = jobs["publish-npm-alias"]
    assert scoped["needs"] == "publish-pypi"
    assert alias["needs"] == "publish-npm-scoped"

    scoped_steps = "\n".join(str(step.get("run", "")) for step in scoped["steps"])
    alias_steps = "\n".join(str(step.get("run", "")) for step in alias["steps"])
    assert "npm publish release-staging/npm/scoped/" in scoped_steps
    assert "npm publish release-staging/npm/alias/" in alias_steps
    assert "sha256sum --check NPM_SHA256SUMS" in scoped_steps
    assert "sha256sum --check NPM_SHA256SUMS" in alias_steps
    assert "actions/download-artifact" in "\n".join(
        str(step.get("uses", "")) for step in scoped["steps"]
    )
    assert "actions/download-artifact" in "\n".join(
        str(step.get("uses", "")) for step in alias["steps"]
    )
    assert all(
        "actions/checkout" not in step.get("uses", "") for step in scoped["steps"]
    )
    assert all(
        "actions/checkout" not in step.get("uses", "") for step in alias["steps"]
    )
    assert "cd npm/alias" not in alias_steps
    assert "fs.writeFileSync" not in alias_steps


def test_every_release_job_has_a_timeout() -> None:
    workflow = _workflow()

    for job_name, job in workflow["jobs"].items():
        assert isinstance(job.get("timeout-minutes"), int), job_name
        assert job["timeout-minutes"] > 0, job_name
