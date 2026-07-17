"""Spec-136 resolve mechanics and the --check gate mode -- offline unit
tests (FR-017; stubs in tests/unit/_dep_coresolve_fixtures.py)."""

from __future__ import annotations

import pytest

from tests.unit._dep_coresolve_fixtures import (
    INFRA_STDERR,
    REPORT_PASS_JSON,
    RESOLUTION_STDERR,
)

pytestmark = pytest.mark.unit

# --------------------------------------------------------------------------- #
# T007-T010 [US1] Per-environment resolve classification + cross-product union.
# --------------------------------------------------------------------------- #


def _one_env_manifest(tmp_path, extras=("dbt",)):
    """A one-local-environment manifest whose pyproject defines the extras."""
    opt = "\n".join(f"{x} = []" for x in extras)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "seshat-bi"\ndependencies = []\n'
        f"[project.optional-dependencies]\n{opt}\n",
        encoding="utf-8",
    )
    extras_yaml = ", ".join(extras)
    manifest = tmp_path / "dependency-environments.yaml"
    manifest.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: root-dbt\n"
        "    pyproject: pyproject.toml\n"
        f"    extras: [{extras_yaml}]\n"
        "    local: true\n"
        '    path: "."\n',
        encoding="utf-8",
    )
    return manifest


def test_resolution_impossible_classifies_and_redacts(stub_resolve, tmp_path):
    """FR-003: a stubbed ResolutionImpossible resolve -> RESOLUTION, capturing
    the (redacted) resolver text."""
    import scripts.dep_coresolve as dc

    stub_resolve(returncode=1, stdout="", stderr=RESOLUTION_STDERR)
    manifest = dc.load_manifest(_one_env_manifest(tmp_path))
    result = dc.resolve_environment(manifest, manifest.environments[0])

    assert result.outcome is dc.ResolveOutcome.RESOLUTION
    assert "ResolutionImpossible" in result.detail
    assert "dbt-core" in result.detail


def test_successful_dry_run_report_classifies_pass_no_local_install(
    stub_resolve, tmp_path
):
    """FR-002/SC-002: a stubbed successful --dry-run --report -> PASS, and the
    resolve NEVER installs into the current interpreter (the stubbed
    ephemeral-venv seam is the only path; no real subprocess runs)."""
    import scripts.dep_coresolve as dc

    stub_resolve(returncode=0, stdout=REPORT_PASS_JSON, stderr="")
    manifest = dc.load_manifest(_one_env_manifest(tmp_path))
    result = dc.resolve_environment(manifest, manifest.environments[0])

    assert result.outcome is dc.ResolveOutcome.PASS
    # The stub recorded exactly one resolve call routed through the venv seam;
    # nothing touched this interpreter's site-packages.
    assert len(stub_resolve.state["calls"]) == 1
    # The requirement handed to the resolve seam is the LOCAL PATH (D1).
    reqs = stub_resolve.state["calls"][0]
    assert any(r.endswith("[dbt]") for r in reqs)
    assert not any(r.startswith("seshat-bi") for r in reqs)


def test_network_failure_classifies_infra_distinct_exit(stub_resolve, tmp_path):
    """FR-004/SC-004: a stubbed network failure -> INFRA, with a distinct exit
    code from RESOLUTION."""
    import scripts.dep_coresolve as dc

    stub_resolve(returncode=1, stdout="", stderr=INFRA_STDERR)
    manifest = dc.load_manifest(_one_env_manifest(tmp_path))
    result = dc.resolve_environment(manifest, manifest.environments[0])

    assert result.outcome is dc.ResolveOutcome.INFRA
    assert dc.EXIT_INFRA != dc.EXIT_RESOLUTION


def test_cross_product_unions_members_and_resolves_as_one(stub_resolve, tmp_path):
    """FR-002/T010: a cross-product unions its members' requirement sets and
    resolves them together; the historical dbt-core vs dagster-dbt shape ->
    RESOLUTION."""
    import scripts.dep_coresolve as dc

    # Two local members: root (dbt extra) + orchestration.
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "seshat-bi"\ndependencies = []\n'
        "[project.optional-dependencies]\ndbt = []\n",
        encoding="utf-8",
    )
    orch = tmp_path / "orchestration" / "dagster"
    orch.mkdir(parents=True)
    (orch / "pyproject.toml").write_text(
        '[project]\nname = "tower-bi-orchestration"\ndependencies = []\n'
        "[project.optional-dependencies]\ndev = []\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "dependency-environments.yaml"
    manifest_path.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: root-dbt\n"
        "    pyproject: pyproject.toml\n"
        "    extras: [dbt]\n"
        "    local: true\n"
        '    path: "."\n'
        "  - id: orchestration\n"
        "    pyproject: orchestration/dagster/pyproject.toml\n"
        "    extras: [dev]\n"
        "    local: true\n"
        '    path: "orchestration/dagster"\n'
        "cross_products:\n"
        "  - id: root-dbt-plus-orchestration\n"
        "    combine: [root-dbt, orchestration]\n",
        encoding="utf-8",
    )
    manifest = dc.load_manifest(manifest_path)

    # Assembly unions BOTH members' local-path requirements.
    reqs = dc.assemble_cross_product(manifest, manifest.cross_products[0])
    assert len(reqs) == 2
    assert any(r.endswith("[dbt]") for r in reqs)

    # The historical conflict resolves to RESOLUTION.
    stub_resolve(returncode=1, stdout="", stderr=RESOLUTION_STDERR)
    result = dc.resolve_cross_product(manifest, manifest.cross_products[0])
    assert result.outcome is dc.ResolveOutcome.RESOLUTION
    assert len(stub_resolve.state["calls"][0]) == 2


# --------------------------------------------------------------------------- #
# T013 [US1] The --check entry mode (fail-closed exit codes + PASS lines).
# --------------------------------------------------------------------------- #


def test_check_all_pass_exits_zero(stub_resolve, tmp_path, capsys):
    """FR-006: all environments resolve -> exit 0, one PASS line per env."""
    import scripts.dep_coresolve as dc

    stub_resolve(returncode=0, stdout=REPORT_PASS_JSON, stderr="")
    code = dc.run_check(_one_env_manifest(tmp_path))
    out = capsys.readouterr().out

    assert code == dc.EXIT_OK
    assert "PASS" in out
    assert "root-dbt" in out


def test_check_resolution_conflict_exits_nonzero_with_text(
    stub_resolve, tmp_path, capsys
):
    """FR-003: a RESOLUTION conflict -> non-zero exit, redacted resolver text
    printed naming the failing environment."""
    import scripts.dep_coresolve as dc

    stub_resolve(returncode=1, stdout="", stderr=RESOLUTION_STDERR)
    code = dc.run_check(_one_env_manifest(tmp_path))
    out = capsys.readouterr().out

    assert code == dc.EXIT_RESOLUTION
    assert "root-dbt" in out
    assert "ResolutionImpossible" in out


def test_check_infra_only_exits_distinct_infra_code(stub_resolve, tmp_path, capsys):
    """FR-004/SC-004: when ONLY INFRA occurred, exit with the distinct INFRA
    code, not the RESOLUTION code."""
    import scripts.dep_coresolve as dc

    stub_resolve(returncode=1, stdout="", stderr=INFRA_STDERR)
    code = dc.run_check(_one_env_manifest(tmp_path))

    assert code == dc.EXIT_INFRA


def test_check_config_error_exits_nonzero(tmp_path, capsys):
    """FR-005: a bad manifest entry (missing pyproject) -> non-zero exit."""
    import scripts.dep_coresolve as dc

    manifest = tmp_path / "dependency-environments.yaml"
    manifest.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: gone\n"
        "    pyproject: nope.toml\n"
        "    extras: [dev]\n"
        "    local: true\n"
        '    path: "."\n',
        encoding="utf-8",
    )
    code = dc.run_check(manifest)
    out = capsys.readouterr().out

    # CONFIG has its OWN exit code -- distinguishable from RESOLUTION and INFRA
    # (FR-005) -- but still fails closed (non-zero).
    assert code == dc.EXIT_CONFIG
    assert code != dc.EXIT_RESOLUTION
    assert code != dc.EXIT_INFRA
    assert code != dc.EXIT_OK
    assert "nope.toml" in out


def test_check_resolution_wins_over_infra(monkeypatch, tmp_path):
    """A real RESOLUTION anywhere fails closed even if an INFRA also occurred
    (a conflict is never excused by a co-occurring network blip)."""
    import scripts.dep_coresolve as dc

    # Two envs: first RESOLUTION, second INFRA.
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = []\n'
        "[project.optional-dependencies]\ndev = []\ndbt = []\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "dependency-environments.yaml"
    manifest_path.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: a\n"
        "    pyproject: pyproject.toml\n"
        "    extras: [dev]\n"
        "    local: true\n"
        '    path: "."\n'
        "  - id: b\n"
        "    pyproject: pyproject.toml\n"
        "    extras: [dbt]\n"
        "    local: true\n"
        '    path: "."\n',
        encoding="utf-8",
    )

    # Program per-call stderr: first RESOLUTION, then INFRA.
    seq = [RESOLUTION_STDERR, INFRA_STDERR]

    def fake_run_resolve(requirements, report_path):
        stderr = seq.pop(0)
        return dc.ResolveRun(returncode=1, stdout="", stderr=stderr, report_json=None)

    monkeypatch.setattr(dc, "_run_resolve", fake_run_resolve)
    code = dc.run_check(manifest_path)
    assert code == dc.EXIT_RESOLUTION
