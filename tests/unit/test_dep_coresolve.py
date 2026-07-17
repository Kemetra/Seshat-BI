"""Spec-136 manifest loading, requirement assembly, outcome classification,
and redaction -- offline unit tests (FR-017; stubs in
tests/unit/_dep_coresolve_fixtures.py)."""

from __future__ import annotations

import pytest

from tests.unit._dep_coresolve_fixtures import (
    INFRA_STDERR,
    RESOLUTION_STDERR,
)

pytestmark = pytest.mark.unit

# --------------------------------------------------------------------------- #
# T003 [US1] Manifest loader + CONFIG classification.
# --------------------------------------------------------------------------- #


def test_valid_manifest_parses_into_typed_records(tmp_path):
    import scripts.dep_coresolve as dc

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = []\n'
        "[project.optional-dependencies]\ndev = []\ndbt = []\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "dependency-environments.yaml"
    manifest.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: root-dev\n"
        "    pyproject: pyproject.toml\n"
        "    extras: [dev]\n"
        "    local: true\n"
        '    path: "."\n'
        "cross_products:\n"
        "  - id: cp\n"
        "    combine: [root-dev]\n"
        "governed_pins:\n"
        "  - dist: dbt-core\n",
        encoding="utf-8",
    )

    loaded = dc.load_manifest(manifest)

    assert [e.id for e in loaded.environments] == ["root-dev"]
    env = loaded.environments[0]
    assert env.extras == ("dev",)
    assert env.local is True
    assert [cp.id for cp in loaded.cross_products] == ["cp"]
    assert loaded.cross_products[0].combine == ("root-dev",)
    assert [p.dist for p in loaded.governed_pins] == ["dbt-core"]


def test_manifest_missing_pyproject_is_config_outcome(tmp_path):
    import scripts.dep_coresolve as dc

    manifest = tmp_path / "dependency-environments.yaml"
    manifest.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: gone\n"
        "    pyproject: does-not-exist.toml\n"
        "    extras: [dev]\n"
        "    local: true\n"
        '    path: "."\n',
        encoding="utf-8",
    )

    loaded = dc.load_manifest(manifest)
    result = dc.resolve_environment(loaded, loaded.environments[0])

    assert result.outcome is dc.ResolveOutcome.CONFIG
    assert "does-not-exist.toml" in result.detail


def test_manifest_undefined_extra_is_config_outcome(tmp_path):
    import scripts.dep_coresolve as dc

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = []\n'
        "[project.optional-dependencies]\ndev = []\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "dependency-environments.yaml"
    manifest.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: bad\n"
        "    pyproject: pyproject.toml\n"
        "    extras: [nope]\n"
        "    local: true\n"
        '    path: "."\n',
        encoding="utf-8",
    )

    loaded = dc.load_manifest(manifest)
    result = dc.resolve_environment(loaded, loaded.environments[0])

    assert result.outcome is dc.ResolveOutcome.CONFIG
    assert "nope" in result.detail


# --------------------------------------------------------------------------- #
# T004 [US1] Local-path assembly (plan-review D1) + old-pip CONFIG (D5) +
# classification defaults (D2).
# --------------------------------------------------------------------------- #


def test_local_members_assemble_as_paths_never_dist_names(tmp_path):
    """plan-review D1: a repository-local member is assembled as a LOCAL PATH
    requirement, never by distribution name. The oracle sits on the assembled
    requirement strings themselves."""
    import scripts.dep_coresolve as dc

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "seshat-bi"\ndependencies = []\n'
        "[project.optional-dependencies]\ndbt = []\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "dependency-environments.yaml"
    manifest.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: root-dbt\n"
        "    pyproject: pyproject.toml\n"
        "    extras: [dbt]\n"
        "    local: true\n"
        '    path: "."\n',
        encoding="utf-8",
    )

    loaded = dc.load_manifest(manifest)
    reqs = dc.assemble_requirements(loaded, loaded.environments[0])

    joined = " ".join(reqs)
    # The assembled requirement is a local PATH carrying the extras...
    assert any(r.endswith("[dbt]") for r in reqs)
    assert any(("/" in r or r.startswith(".")) for r in reqs)
    # ...and the seshat-bi DISTRIBUTION NAME never appears as a requirement.
    assert "seshat-bi[dbt]" not in joined
    assert not any(r == "seshat-bi" or r.startswith("seshat-bi") for r in reqs)


def test_ambiguous_resolver_error_defaults_to_resolution(tmp_path):
    """plan-review D2: an unrecognized non-zero resolve fails CLOSED as
    RESOLUTION, never excused as INFRA."""
    import scripts.dep_coresolve as dc

    outcome = dc.classify_resolve(
        returncode=1,
        stderr="ERROR: some unexpected message the classifier does not recognize\n",
    )
    assert outcome is dc.ResolveOutcome.RESOLUTION


def test_explicit_network_signature_is_infra(tmp_path):
    """plan-review D2: INFRA only on an explicit, fixture-tested network
    signature."""
    import scripts.dep_coresolve as dc

    outcome = dc.classify_resolve(returncode=1, stderr=INFRA_STDERR)
    assert outcome is dc.ResolveOutcome.INFRA


def test_resolution_signature_is_resolution(tmp_path):
    import scripts.dep_coresolve as dc

    outcome = dc.classify_resolve(returncode=1, stderr=RESOLUTION_STDERR)
    assert outcome is dc.ResolveOutcome.RESOLUTION


def test_venv_pip_too_old_is_config(tmp_path):
    """plan-review D5: an ephemeral-venv pip too old for --report yields CONFIG,
    not a crash."""
    import scripts.dep_coresolve as dc

    assert dc.pip_supports_report("22.2") is True
    assert dc.pip_supports_report("22.1.2") is False
    assert dc.pip_supports_report("21.3") is False


# --------------------------------------------------------------------------- #
# T005 [US1] Redaction of a surfaced resolver error via the C2 shapes.
# --------------------------------------------------------------------------- #


def test_redaction_masks_credential_shaped_token():
    """FR-016: a resolver error carrying a C2 connection-string shape is masked
    before it is surfaced. Reuses the repo's C2 secret-shape posture."""
    import scripts.dep_coresolve as dc

    dirty = (
        "ERROR: Could not install from "
        "postgres://admin:s3cr3t@prod-host:5432/warehouse -- ResolutionImpossible"
    )
    cleaned = dc.redact(dirty)
    assert "s3cr3t" not in cleaned
    assert "postgres://admin:s3cr3t@" not in cleaned
    assert "[REDACTED]" in cleaned


def test_redaction_masks_digitalocean_endpoint():
    import scripts.dep_coresolve as dc

    dirty = "ERROR: host db-postgresql-fra1-12345.db.ondigitalocean.com refused"
    cleaned = dc.redact(dirty)
    assert "db.ondigitalocean.com" not in cleaned
    assert "[REDACTED]" in cleaned


def test_redaction_passes_clean_conflict_message_unchanged():
    """A clean resolver conflict (no secret shape) is passed through verbatim."""
    import scripts.dep_coresolve as dc

    assert dc.redact(RESOLUTION_STDERR) == RESOLUTION_STDERR
