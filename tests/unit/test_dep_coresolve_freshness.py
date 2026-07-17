"""Spec-136 advisory freshness reporter -- offline unit tests (FR-017;
stubs in tests/unit/_dep_coresolve_fixtures.py)."""

from __future__ import annotations

import json

import pytest

from tests.unit._dep_coresolve_fixtures import (
    REPORT_PASS_JSON,
    RESOLUTION_STDERR,
    _pypi_json,
)

pytestmark = pytest.mark.unit

# --------------------------------------------------------------------------- #
# T015-T019 [US2] Advisory freshness: latest-stable, proposals, solve-proof.
# --------------------------------------------------------------------------- #


def _freshness_manifest(tmp_path, pin_spec: str, extra: str = "dbt", dist="dbt-core"):
    """A one-env manifest whose root pyproject declares one governed pin under
    ``extra`` with the given specifier (e.g. ``dbt-core==1.12.0``)."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "seshat-bi"\ndependencies = []\n'
        f'[project.optional-dependencies]\n{extra} = ["{pin_spec}"]\n',
        encoding="utf-8",
    )
    manifest = tmp_path / "dependency-environments.yaml"
    manifest.write_text(
        "version: 1\n"
        "environments:\n"
        "  - id: root-dbt\n"
        "    pyproject: pyproject.toml\n"
        f"    extras: [{extra}]\n"
        "    local: true\n"
        '    path: "."\n'
        f"governed_pins:\n  - dist: {dist}\n",
        encoding="utf-8",
    )
    return manifest


def test_latest_stable_excludes_yanked_and_prereleases():
    """FR-007: latest stable EXCLUDES pre-release/dev/rc and fully-yanked
    releases. Yanked is PER-FILE: a release counts yanked only when ALL its
    files are yanked (plan-review D5)."""
    import scripts.dep_coresolve as dc

    body = _pypi_json(
        "dbt-core",
        {
            "1.10.0": [{"yanked": False}],
            "1.11.0": [{"yanked": True}, {"yanked": True}],  # fully yanked -> skip
            "1.12.0": [{"yanked": True}, {"yanked": False}],  # half-yanked -> KEEP
            "1.13.0rc1": [{"yanked": False}],  # pre-release -> skip
            "1.13.0.dev1": [{"yanked": False}],  # dev -> skip
        },
        {},
    )
    latest = dc.latest_stable(json.loads(body))
    assert latest == "1.12.0"


def test_prerelease_pin_reported_but_not_proposed_as_stable():
    """FR-007 edge: a pin already on a pre-release is reported, but a
    pre-release is never proposed as the stable target."""
    import scripts.dep_coresolve as dc

    body = _pypi_json(
        "mcp",
        {"1.0.0": [{"yanked": False}], "2.0.0b1": [{"yanked": False}]},
        {},
    )
    # Only 1.0.0 is stable; 2.0.0b1 is a pre-release and is not the target.
    assert dc.latest_stable(json.loads(body)) == "1.0.0"


def test_version_ordering_is_numeric_not_lexical():
    import scripts.dep_coresolve as dc

    body = _pypi_json(
        "pkg",
        {"1.9.0": [{"yanked": False}], "1.10.0": [{"yanked": False}]},
        {},
    )
    # 1.10.0 > 1.9.0 numerically (lexical string sort would wrongly pick 1.9.0).
    assert dc.latest_stable(json.loads(body)) == "1.10.0"


def test_proposal_behind_latest_carries_solve_proof(stub_resolve, stub_pypi, tmp_path):
    """FR-009: a governed pin behind latest yields a PROPOSAL carrying a
    solve-proof result for the PROPOSED-version substitution."""
    import scripts.dep_coresolve as dc

    manifest_path = _freshness_manifest(tmp_path, "dbt-core==1.12.0")
    stub_pypi(
        "dbt-core",
        _pypi_json(
            "dbt-core",
            {"1.12.0": [{"yanked": False}], "1.13.0": [{"yanked": False}]},
            {},
        ),
    )
    stub_resolve(returncode=0, stdout=REPORT_PASS_JSON, stderr="")

    manifest = dc.load_manifest(manifest_path)
    proposals = dc.propose_bumps(manifest)

    assert len(proposals) == 1
    p = proposals[0]
    assert p.dist == "dbt-core"
    assert p.current == "1.12.0"
    assert p.latest_stable == "1.13.0"
    assert p.solve_outcome is dc.ResolveOutcome.PASS
    # REPLACE semantics: the resolve saw dbt-core==1.13.0, NOT the local
    # path (which would re-impose ==1.12.0 and trivially conflict).
    reqs = stub_resolve.state["calls"][0]
    assert any("dbt-core==1.13.0" in r for r in reqs)
    assert not any(r.endswith("[dbt]") for r in reqs)


def test_proposal_with_failing_solve_still_renders(stub_resolve, stub_pypi, tmp_path):
    """FR-010: a proposed bump whose solve FAILS is still rendered, marked
    non-resolving; it is not crashed or omitted."""
    import scripts.dep_coresolve as dc

    manifest_path = _freshness_manifest(tmp_path, "dbt-core==1.12.0")
    stub_pypi(
        "dbt-core",
        _pypi_json(
            "dbt-core",
            {"1.12.0": [{"yanked": False}], "1.13.0": [{"yanked": False}]},
            {},
        ),
    )
    stub_resolve(returncode=1, stdout="", stderr=RESOLUTION_STDERR)

    manifest = dc.load_manifest(manifest_path)
    proposals = dc.propose_bumps(manifest)

    assert len(proposals) == 1
    assert proposals[0].solve_outcome is dc.ResolveOutcome.RESOLUTION
    # The report renders it (does not omit) -- see the markdown render test below.
    report = dc.render_freshness_markdown(proposals)
    assert "dbt-core" in report
    assert "does not resolve" in report.lower()


def test_upper_bounded_pin_reports_honestly_and_ceiling_forbids(stub_pypi, tmp_path):
    """Edge case + D3: an upper-bounded pin (mcp>=1.28,<2) whose latest stable
    sits ABOVE the ceiling is reported honestly; the solve-proof substitutes
    the proposed version and, because the DECLARED CEILING forbids it, records
    RESOLUTION naming the forbidding ceiling -- by construction, not by a
    resolver round-trip."""
    import scripts.dep_coresolve as dc

    manifest_path = _freshness_manifest(
        tmp_path, "mcp>=1.28,<2", extra="mcp", dist="mcp"
    )
    stub_pypi(
        "mcp",
        _pypi_json(
            "mcp", {"1.28.0": [{"yanked": False}], "2.1.0": [{"yanked": False}]}, {}
        ),
    )

    manifest = dc.load_manifest(manifest_path)
    proposals = dc.propose_bumps(manifest)

    assert len(proposals) == 1
    p = proposals[0]
    assert p.latest_stable == "2.1.0"  # reported honestly, above the ceiling
    assert p.solve_outcome is dc.ResolveOutcome.RESOLUTION
    assert "<2" in p.solve_detail  # the forbidding ceiling is named


def test_freshness_run_mutates_no_pin_and_opens_no_pr(
    stub_resolve, stub_pypi, tmp_path
):
    """FR-008/FR-012: a freshness run changes NO tracked pin value and opens NO
    PR. The reporter is read-only over pyproject files."""
    import scripts.dep_coresolve as dc

    manifest_path = _freshness_manifest(tmp_path, "dbt-core==1.12.0")
    pyproject = tmp_path / "pyproject.toml"
    before = pyproject.read_text(encoding="utf-8")
    stub_pypi(
        "dbt-core",
        _pypi_json(
            "dbt-core",
            {"1.12.0": [{"yanked": False}], "1.13.0": [{"yanked": False}]},
            {},
        ),
    )
    stub_resolve(returncode=0, stdout=REPORT_PASS_JSON, stderr="")

    manifest = dc.load_manifest(manifest_path)
    dc.propose_bumps(manifest)

    # The pyproject is byte-identical: no pin mutated.
    assert pyproject.read_text(encoding="utf-8") == before
    # The reporter exposes no PR-opening capability.
    assert not hasattr(dc, "open_pull_request")


def test_no_newer_stable_yields_no_proposal(stub_pypi, tmp_path):
    """A pin already at latest stable yields no proposal (empty-delta PASS)."""
    import scripts.dep_coresolve as dc

    manifest_path = _freshness_manifest(tmp_path, "dbt-core==1.13.0")
    stub_pypi(
        "dbt-core",
        _pypi_json(
            "dbt-core",
            {"1.12.0": [{"yanked": False}], "1.13.0": [{"yanked": False}]},
            {},
        ),
    )
    manifest = dc.load_manifest(manifest_path)
    proposals = dc.propose_bumps(manifest)
    assert proposals == []


# --------------------------------------------------------------------------- #
# T022 [US2] The --freshness entry mode (render JSON + Markdown, read-only).
# --------------------------------------------------------------------------- #


def test_run_freshness_writes_report_and_is_read_only(
    stub_resolve, stub_pypi, tmp_path
):
    """FR-011/FR-008: --freshness writes a report artifact (JSON + Markdown)
    and mutates no tracked pin."""
    import scripts.dep_coresolve as dc

    manifest_path = _freshness_manifest(tmp_path, "dbt-core==1.12.0")
    pyproject = tmp_path / "pyproject.toml"
    before = pyproject.read_text(encoding="utf-8")
    stub_pypi(
        "dbt-core",
        _pypi_json(
            "dbt-core",
            {"1.12.0": [{"yanked": False}], "1.13.0": [{"yanked": False}]},
            {},
        ),
    )
    stub_resolve(returncode=0, stdout=REPORT_PASS_JSON, stderr="")

    out_json = tmp_path / "report.json"
    code = dc.run_freshness(manifest_path, str(out_json))

    assert code == dc.EXIT_OK
    assert out_json.is_file()
    body = json.loads(out_json.read_text(encoding="utf-8"))
    assert body["proposals"][0]["dist"] == "dbt-core"
    # The sibling Markdown is written next to the JSON.
    assert (tmp_path / "report.md").is_file()
    # Read-only over pyproject.
    assert pyproject.read_text(encoding="utf-8") == before


def test_governed_pin_in_base_dependencies_is_found_and_proposed(
    stub_resolve, stub_pypi, tmp_path
):
    """A governed pin living in [project].dependencies (the orchestration
    project's dagster shape) is found and proposed -- not silently skipped
    because the search only looked at extras (Codex review on PR #308)."""
    import scripts.dep_coresolve as dc

    root = tmp_path
    pyproject = "\n".join(
        [
            "[project]",
            'name = "orch"',
            'version = "0"',
            'dependencies = ["dagster==1.13.14"]',
        ]
    )
    (root / "pyproject.toml").write_text(pyproject + "\n", encoding="utf-8")
    manifest_text = "\n".join(
        [
            "version: 1",
            "environments:",
            "  - id: orch",
            "    pyproject: pyproject.toml",
            "    extras: []",
            "    local: true",
            "    path: '.'",
            "governed_pins:",
            "  - dist: dagster",
        ]
    )
    (root / "manifest.yaml").write_text(manifest_text + "\n", encoding="utf-8")
    stub_pypi(
        "dagster",
        _pypi_json(
            "dagster",
            {"1.13.14": [{"yanked": False}], "1.14.0": [{"yanked": False}]},
            {"version": "1.14.0"},
        ),
    )
    manifest = dc.load_manifest(root / "manifest.yaml")
    proposals = dc.propose_bumps(manifest)
    assert len(proposals) == 1
    assert proposals[0].dist == "dagster"
    assert proposals[0].latest_stable == "1.14.0"
    # the solve-proof substituted into the BASE requirement list
    assert any("dagster==1.14.0" in " ".join(c) for c in stub_resolve.state["calls"])
