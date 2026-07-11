"""US1/US3: offline demo flow -- init, load(offline), run, report (spec 083).

All offline; no network, no DB. Uses the real committed fixtures via a --repo
pointing at the worktree root so the flow exercises the true mapping/readiness
artifacts. Every run targets a tmp working dir so no tracked file is touched.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Repo root = three parents up from this test file (tests/unit/ -> repo).
_REPO = Path(__file__).resolve().parents[2]


def test_demo_init_idempotent(tmp_path):
    """T010: demo init materializes fixtures and is idempotent without --force."""
    from seshat.demo import fixtures

    # Seed a tmp "repo" with just the committed fixture files the demo reads.
    _seed_repo(tmp_path)
    wd = fixtures.materialize(tmp_path)
    marker = wd / "demo_sample_orders" / "readiness-status.yaml"
    assert marker.exists()
    mtime = marker.stat().st_mtime_ns
    # Re-materialize without force -> no overwrite (idempotent).
    fixtures.materialize(tmp_path, force=False)
    assert marker.stat().st_mtime_ns == mtime


def test_demo_load_offline_skips_and_exits_zero(tmp_path, capsys):
    """T011: demo load with no DSN reports the skip reason and exits 0."""
    _seed_repo(tmp_path)

    class _Args:
        repo = str(tmp_path)
        dsn = None

    from seshat.demo.load import run_load

    assert run_load(_Args()) == 0
    assert "offline" in capsys.readouterr().out.lower()


def test_demo_run_offline_ceiling(tmp_path, capsys):
    """T012: offline run -> source/mapping/silver pass, gold+ never pass."""
    _seed_repo(tmp_path)

    class _Args:
        repo = str(tmp_path)
        dsn = None

    from seshat.demo.run import run_run

    assert run_run(_Args()) == 0
    snap = json.loads(
        (tmp_path / ".demo-work" / "computed-status.json").read_text(encoding="utf-8")
    )
    stages = snap["stages"]
    assert stages["source_ready"]["status"] == "pass"
    assert stages["mapping_ready"]["status"] == "pass"
    assert stages["silver_ready"]["status"] == "pass"
    # Gold Ready onward is NEVER pass offline (the honest ceiling).
    for later in (
        "gold_ready",
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    ):
        assert stages[later]["status"] != "pass"


def test_demo_report_no_score_and_names_next_action(tmp_path, capsys):
    """T013: report never emits a numeric score and names a next_action (text+json)."""
    _seed_repo(tmp_path)

    class _Args:
        repo = str(tmp_path)
        dsn = None
        format = "text"

    from seshat.demo.report import run_report
    from seshat.demo.run import run_run

    run_run(_Args())  # produce a snapshot first
    assert run_report(_Args()) == 0
    text_out = capsys.readouterr().out
    assert "next_action" in text_out
    # no numeric percentage / "N of M" score anywhere
    assert "%" not in text_out
    assert " of " not in text_out or "out of scope" in text_out.lower()

    _Args.format = "json"
    assert run_report(_Args()) == 0
    json_out = capsys.readouterr().out
    doc = json.loads(json_out)
    assert doc.get("next_action")
    assert "score" not in json_out.lower()


def test_demo_report_labels_illustrative_approval(tmp_path, capsys):
    """T028 (US3): report labels the illustrative approval, not run-produced."""
    _seed_repo(tmp_path)

    class _Args:
        repo = str(tmp_path)
        dsn = None
        format = "text"

    from seshat.demo.report import run_report
    from seshat.demo.run import run_run

    run_run(_Args())
    run_report(_Args())
    out = capsys.readouterr().out
    assert "ILLUSTRATIVE" in out.upper()


def test_demo_never_writes_tracked_readiness_fixture(tmp_path):
    """T029: no demo verb mutates the committed readiness-status fixture."""
    _seed_repo(tmp_path)
    committed = tmp_path / "mappings" / "demo_sample_orders" / "readiness-status.yaml"
    before = committed.read_bytes()

    class _Args:
        repo = str(tmp_path)
        dsn = None
        format = "text"
        force = False

    from seshat.demo.init import run_init
    from seshat.demo.report import run_report
    from seshat.demo.run import run_run

    run_init(_Args())
    run_run(_Args())
    run_report(_Args())
    assert committed.read_bytes() == before


def _seed_repo(tmp_path: Path) -> None:
    """Copy the committed demo fixtures into a tmp repo root for isolated testing."""
    import shutil

    (tmp_path / "mappings" / "demo_sample_orders").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "fixtures" / "demo").mkdir(parents=True, exist_ok=True)
    src_map = _REPO / "mappings" / "demo_sample_orders"
    for name in (
        "source-profile.md",
        "source-map.yaml",
        "assumptions.md",
        "unresolved-questions.md",
        "readiness-status.yaml",
    ):
        shutil.copyfile(
            src_map / name, tmp_path / "mappings" / "demo_sample_orders" / name
        )
    shutil.copyfile(
        _REPO / "tests" / "fixtures" / "demo" / "demo_sample_orders.csv",
        tmp_path / "tests" / "fixtures" / "demo" / "demo_sample_orders.csv",
    )
