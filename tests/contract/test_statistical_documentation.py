"""Publication contract for the governed statistical evidence engine."""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _yaml(path: str) -> dict:
    return yaml.safe_load(_text(path))


def test_active_analyst_docs_route_governed_statistics() -> None:
    analyst = _text("skills/bi-analyst-knowledge/SKILL.md")
    index = _text("skills/bi-analyst-knowledge/INDEX.md")
    signal = _text("skills/bi-analyst-knowledge/framing-signal-vs-noise.md")
    trend = _text("skills/bi-analyst-knowledge/framing-trend-anomaly.md")

    assert "statistical-evidence-workflow.md" in analyst
    assert "seshat analyze" in analyst
    assert "statistical-evidence-workflow.md" in index
    assert "no regression, forecasting" not in analyst.lower()
    assert "regression, forecasting, significance/hypothesis testing" not in signal
    assert (
        "Regression, forecasting, and significance testing are out of scope"
        not in trend
    )


def test_architecture_declares_authority_methods_and_live_boundary() -> None:
    architecture = _text("docs/architecture/statistical-evidence-engine.md")
    lowered = architecture.lower()

    assert "product module" in lowered
    assert "execution adapter" in lowered
    assert "derived evidence" in lowered
    assert "gold-only" in lowered
    assert "no truth creation" in lowered
    assert "postgresql-only" in lowered
    for method_id in (
        "describe",
        "compare_groups",
        "proportion",
        "correlate",
        "regress",
        "detect_anomalies",
        "detect_change_points",
        "forecast",
    ):
        assert f"`{method_id}`" in architecture


def test_workflow_routes_to_named_human_review_without_self_approval() -> None:
    workflow = _text("skills/bi-analyst-knowledge/statistical-evidence-workflow.md")

    assert "seshat analyze validate" in workflow
    assert "seshat analyze run" in workflow
    assert "accepted review evidence" in workflow
    assert "never self-grant" in workflow.lower()
    assert "readiness_effect" in workflow


def test_install_docs_publish_exact_pinned_statistics_commands() -> None:
    user = _text("docs/install/user-install.md")
    agent = _text("docs/install/agent-install.md")
    developer = _text("docs/install/developer-install.md")
    quickstart = _text("docs/install/client-quickstart.md")
    support = _text("docs/install/support-matrix.md")

    assert 'pipx install "seshat-bi[stats]"' in user
    for pin in (
        '"numpy==2.5.1"',
        '"scipy==1.18.0"',
        '"statsmodels==0.14.6"',
        '"ruptures==1.1.10"',
    ):
        assert pin in user
        assert pin in agent
    assert ".[dev,stats,stats-change]" in developer
    assert "seshat analyze" in quickstart
    assert "`stats`" in support
    assert "`stats-change`" in support


def test_capability_and_status_manifests_publish_both_authority_classes() -> None:
    capabilities = {
        item["id"]: item
        for item in _yaml("docs/capabilities/capabilities.yaml")["capabilities"]
    }
    core = capabilities["governed-statistical-core"]
    adapter = capabilities["governed-statistical-gold-adapter"]

    assert core["state"] == "shipped"
    assert core["surface"] == "product-module"
    assert core["provenance"] == "locally-verified"
    assert core["readiness_stage"] == "not-stage-scoped"
    assert adapter["state"] == "shipped"
    assert adapter["surface"] == "execution-adapter"
    assert adapter["requirements"] == ["database", "optional-dependency"]
    assert adapter["readiness_stage"] == "not-stage-scoped"

    claims = {
        item["id"]: item for item in _yaml("docs/quality/status-claims.yaml")["claims"]
    }
    claim = claims["governed-statistical-engine-built"]
    assert claim["claimed-artifact"] == "src/seshat/statistical/runtime.py"
    assert claim["claimed-status"] == "built"


def test_schemas_and_public_workflow_are_packaged() -> None:
    project = tomllib.loads(_text("pyproject.toml"))
    force_include = project["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]
    assert force_include["schemas/statistical-analysis-spec.schema.json"] == (
        "seshat/statistical/schemas/statistical-analysis-spec.schema.json"
    )
    assert force_include["schemas/statistical-analysis-evidence.schema.json"] == (
        "seshat/statistical/schemas/statistical-analysis-evidence.schema.json"
    )

    allowlist = _yaml("distribution/public-knowledge-allowlist.yaml")
    entries = {item["source"]: item for item in allowlist["entries"]}
    workflow = entries["skills/bi-analyst-knowledge/statistical-evidence-workflow.md"]
    destination = "knowledge/bi-analyst-knowledge/statistical-evidence-workflow.md"
    assert workflow["targets"] == {"claude": destination, "codex": destination}


def test_active_product_surfaces_and_changelog_supersede_old_exclusion() -> None:
    assert "seshat analyze" in _text("COMPASS.md")
    assert "seshat analyze" in _text("README.md")
    assert "Governed statistical evidence engine" in _text("CHANGELOG.md")
    assert "forecasting, a universal" not in _text("docs/roadmap/roadmap.md")
    assert "not an ML/forecasting system" not in _text(
        "docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md"
    )
