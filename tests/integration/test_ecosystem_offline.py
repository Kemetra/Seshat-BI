"""Complete no-network / no-DB regression (spec 120, T101).

Every independently shipped surface -- the MVP demo proof, passports, packs,
the reference benchmark, and the explorer -- must work with sockets disabled
and no database driver configured. Live-dependent facts stay pending or
blocked; nothing fabricates a live result.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.integration

_REPO = Path(__file__).parents[2]


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted during offline regression")

    monkeypatch.setattr(socket, "socket", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)


def _write_table(root: Path) -> None:
    table_dir = root / "mappings/orders"
    table_dir.mkdir(parents=True)
    (table_dir / "source-profile.md").write_text("profile\n", encoding="utf-8")
    (table_dir / "readiness-status.yaml").write_text(
        """\
table: orders
current_stage: mapping_ready
stages:
  source_ready:
    status: pass
    evidence: [mappings/orders/source-profile.md]
    blocking_reasons: []
  mapping_ready:
    status: blocked
    evidence: []
    blocking_reasons: [grain needs owner approval]
blocking_reasons: [grain needs owner approval]
approvals: []
next_action: Resolve grain with the data owner.
""",
        encoding="utf-8",
    )


def test_mvp_demo_proof_works_offline(tmp_path: Path) -> None:
    assert main(["demo", "init", "--repo", str(tmp_path)]) == 0
    assert main(["demo", "run", "--repo", str(tmp_path)]) == 0
    assert main(["demo", "report", "--repo", str(tmp_path), "--format", "html"]) == 0
    html = (tmp_path / ".seshat-output/demo/index.html").read_text(encoding="utf-8")
    assert "Readiness proof" in html


def test_passport_export_and_verify_work_offline(tmp_path: Path) -> None:
    _write_table(tmp_path)
    assert main(["passport", "export", "--repo", str(tmp_path)]) == 0
    passport = tmp_path / ".seshat-output/passports/passport.json"
    assert (
        main(
            ["passport", "verify", "--repo", str(tmp_path), "--passport", str(passport)]
        )
        == 0
    )


def test_pack_scaffold_and_validate_work_offline(tmp_path: Path) -> None:
    assert (
        main(
            [
                "pack",
                "scaffold",
                "--repo",
                str(tmp_path),
                "--id",
                "acme.offline",
                "--category",
                "kpi",
                "--owner",
                "Casey Analyst",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "pack",
                "validate",
                "--repo",
                str(tmp_path),
                "--pack",
                "packs/local/offline/seshat-pack.yaml",
            ]
        )
        == 0
    )


def test_reference_benchmark_works_offline(tmp_path: Path) -> None:
    output = ".seshat-output/benchmark/offline-run.json"
    assert (
        main(
            [
                "benchmark",
                "run",
                "--repo",
                str(_REPO),
                "--scenarios",
                "benchmark/scenarios/hard-stops.yaml",
                "--output",
                output,
            ]
        )
        == 0
    )
    run_path = _REPO / output
    assert main(["benchmark", "report", "--run", str(run_path)]) == 0
    run_path.unlink()


def test_explorer_works_offline_and_live_facts_stay_deferred(
    tmp_path: Path,
) -> None:
    _write_table(tmp_path)
    status = tmp_path / "mappings/orders/readiness-status.yaml"
    status.write_text(
        status.read_text(encoding="utf-8").replace(
            "evidence: [mappings/orders/source-profile.md]",
            'evidence: ["[PENDING LIVE PROFILE]"]',
        ),
        encoding="utf-8",
    )
    assert main(["explorer", "build", "--repo", str(tmp_path)]) == 0
    html = (tmp_path / ".seshat-output/explorer/index.html").read_text(encoding="utf-8")
    assert "deferred" in html
    assert "PENDING LIVE PROFILE" in html


def test_offline_outputs_never_claim_live_results(tmp_path: Path) -> None:
    _write_table(tmp_path)
    assert main(["passport", "export", "--repo", str(tmp_path)]) == 0
    document = json.loads(
        (tmp_path / ".seshat-output/passports/passport.json").read_text(
            encoding="utf-8"
        )
    )
    assert document["validation_boundary"]["live"] == "unavailable"
