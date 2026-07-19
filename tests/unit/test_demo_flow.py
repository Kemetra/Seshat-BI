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


def test_demo_load_resolves_dsn_from_workspace_dotenv(tmp_path, monkeypatch):
    """#350: `demo load` must resolve a DSN from the workspace `.env`, the same
    precedence `retail validate` uses post-#340. Before the fix, `_resolve_dsn`
    called `resolve_dsn()` with no argument (TypeError, swallowed) and never
    loaded `.env`, so it ALWAYS returned None -- offline regardless of config."""
    for key in (
        "DATABASE_URL",
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_USER",
    ):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "ANALYTICS_DB_HOST=db.example\n"
        "ANALYTICS_DB_NAME=warehouse\n"
        "ANALYTICS_DB_USER=reader\n",
        encoding="utf-8",
    )

    class _Args:
        repo = str(tmp_path)
        dsn = None

    from seshat.demo.load import _resolve_dsn

    dsn = _resolve_dsn(_Args())

    assert dsn is not None
    assert "@db.example" in dsn and "/warehouse" in dsn


def test_demo_load_explicit_dsn_still_wins(tmp_path, monkeypatch):
    """#350 regression: an explicit --dsn must still take precedence over `.env`
    (the pre-existing behavior must not regress when .env loading is added)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text(
        "ANALYTICS_DB_HOST=ignored.example\n", encoding="utf-8"
    )

    class _Args:
        repo = str(tmp_path)
        dsn = "postgresql://u:p@explicit.example:5432/db"

    from seshat.demo.load import _resolve_dsn

    assert _resolve_dsn(_Args()) == "postgresql://u:p@explicit.example:5432/db"


def test_demo_load_non_postgres_engine_degrades_to_offline(tmp_path, monkeypatch):
    """#350 Codex P2: the live leg is Postgres-only. When `.env` selects a
    non-Postgres ANALYTICS_DB_ENGINE, the generic ANALYTICS_DB_* values must NOT
    be force-built into a bogus postgresql:// DSN (which psycopg2 would then aim
    at the wrong engine). It degrades to offline instead."""
    for key in (
        "DATABASE_URL",
        "ANALYTICS_DB_ENGINE",
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_USER",
    ):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "ANALYTICS_DB_ENGINE=mysql\n"
        "ANALYTICS_DB_HOST=mysql.example\n"
        "ANALYTICS_DB_NAME=warehouse\n"
        "ANALYTICS_DB_USER=reader\n",
        encoding="utf-8",
    )

    class _Args:
        repo = str(tmp_path)
        dsn = None

    from seshat.demo.load import _resolve_dsn

    # No postgresql:// DSN fabricated for a mysql engine -> offline (None).
    assert _resolve_dsn(_Args()) is None


def test_demo_load_resolvable_dsn_without_driver_degrades_gracefully(
    tmp_path, monkeypatch, capsys
):
    """#350 Codex P2: post-#350 a workspace `.env` can resolve a DSN, making the
    live leg reachable -- but without psycopg2, load_demo_scoped would raise
    ModuleNotFoundError. The portable operating contract requires an enable-step
    message and exit 0, never a traceback."""
    for key in (
        "DATABASE_URL",
        "ANALYTICS_DB_ENGINE",
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_USER",
    ):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "ANALYTICS_DB_HOST=db.example\n"
        "ANALYTICS_DB_NAME=warehouse\n"
        "ANALYTICS_DB_USER=reader\n",
        encoding="utf-8",
    )
    # Force "psycopg2 unimportable" regardless of the test environment:
    # sys.modules[name]=None makes `import name` raise ImportError.
    import sys

    monkeypatch.setitem(sys.modules, "psycopg2", None)

    class _Args:
        repo = str(tmp_path)
        dsn = None

    from seshat.demo.load import run_load

    code = run_load(_Args())
    out = capsys.readouterr().out
    assert code == 0  # graceful, not a crash
    assert "pip install" in out and "seshat-bi[db]" in out  # the enable step


def test_demo_load_checks_psycopg2_not_the_engine_driver(tmp_path, monkeypatch, capsys):
    """#350 Codex P2 round-2: the live leg is Postgres-only, and an explicit
    --dsn resolves BEFORE the engine gate. So the driver check must pin psycopg2,
    independent of ANALYTICS_DB_ENGINE -- otherwise a `mysql` engine + a Postgres
    --dsn would check the mysql driver, misreporting offline (or passing then
    crashing in demo.live). With psycopg2 absent it must degrade gracefully."""
    monkeypatch.setenv("ANALYTICS_DB_ENGINE", "mysql")  # a wrong-engine export

    import sys

    monkeypatch.setitem(sys.modules, "psycopg2", None)  # psycopg2 import fails

    class _Args:
        repo = str(tmp_path)
        dsn = "postgresql://u:p@localhost:5432/demo"  # explicit Postgres --dsn

    from seshat.demo.load import run_load

    code = run_load(_Args())
    out = capsys.readouterr().out
    assert code == 0
    assert "psycopg2" in out and "pip install" in out  # psycopg2-specific message


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
