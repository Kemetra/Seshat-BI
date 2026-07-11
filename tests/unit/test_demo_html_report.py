from __future__ import annotations

from pathlib import Path

import pytest

from seshat.demo.html_report import render_html
from seshat.demo.report import run_report

pytestmark = pytest.mark.unit
_REPO = Path(__file__).resolve().parents[2]


def _snapshot() -> dict:
    statuses = [
        "pass",
        "pass",
        "pass",
        "blocked",
        "not_started",
        "not_started",
        "not_started",
    ]
    names = [
        "source_ready",
        "mapping_ready",
        "silver_ready",
        "gold_ready",
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    ]
    return {
        "table": "demo_sample_orders",
        "live_reachable": False,
        "stages": {
            name: {
                "status": status,
                "evidence": [f"{name}.md"] if status == "pass" else [],
                "blocking_reasons": ["live validation is unavailable"]
                if status == "blocked"
                else [],
            }
            for name, status in zip(names, statuses, strict=True)
        },
        "next_action": "Run live validation when a database is available.",
        "approvals": [],
    }


def test_html_contains_all_stages_truthful_boundary_and_brand() -> None:
    output = render_html(_snapshot(), repo=_REPO)
    for label in (
        "Source",
        "Mapping",
        "Silver",
        "Gold",
        "Semantic Model",
        "Dashboard",
        "Publish",
    ):
        assert label in output
    assert "live validation is unavailable" in output
    assert "offline mode" in output
    assert "data:image/svg+xml;base64," in output
    assert "No readiness score" in output


def test_html_escapes_untrusted_text() -> None:
    snapshot = _snapshot()
    snapshot["next_action"] = '<script>alert("x")</script>'
    output = render_html(snapshot, repo=_REPO)
    assert '<script>alert("x")</script>' not in output
    assert "&lt;script&gt;" in output


def test_run_report_writes_only_under_generated_output(tmp_path: Path, capsys) -> None:
    _seed_status(tmp_path)

    class Args:
        repo = str(tmp_path)
        format = "html"
        output = ".seshat-output/demo/proof.html"

    assert run_report(Args()) == 0
    output = tmp_path / Args.output
    assert output.is_file()
    assert "HTML readiness proof" in capsys.readouterr().out
    assert not (tmp_path / "mappings" / "demo_sample_orders" / "changed").exists()


def test_run_report_rejects_output_outside_generated_root(
    tmp_path: Path, capsys
) -> None:
    _seed_status(tmp_path)

    class Args:
        repo = str(tmp_path)
        format = "html"
        output = "public/index.html"

    assert run_report(Args()) == 2
    assert "must stay under .seshat-output" in capsys.readouterr().out


def _seed_status(root: Path) -> None:
    target = root / "mappings" / "demo_sample_orders"
    target.mkdir(parents=True)
    source = _REPO / "mappings" / "demo_sample_orders" / "readiness-status.yaml"
    (target / "readiness-status.yaml").write_bytes(source.read_bytes())
