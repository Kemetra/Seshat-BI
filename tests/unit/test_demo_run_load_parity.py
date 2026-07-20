"""demo run / demo load parity + live-leg redaction (issues #375, #376, #379).

`demo run` and `demo load` are sibling verbs that drifted apart. These tests pin
the three audit findings:

* #375 -- `demo run` reported "live mode" on `bool(dsn)` alone, never connecting.
  Liveness must follow an actual reachability probe, not the presence of a string.
* #376 -- `demo run` ignored a DSN configured in `.env` (which `demo load` honors),
  silently falling back to offline.
* #379 -- the live leg's psycopg2 connect had no handler and no redaction, so an
  unreachable DSN could surface credentials in a raw traceback.

The real socket cannot be exercised in CI, so every test monkeypatches the
connect/probe seam; the real psycopg2 connect path is documented as not run here.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_FIXTURE_ROOT = Path(__file__).resolve().parents[2]


def _seed_repo(tmp_path: Path) -> None:
    """Copy the committed demo fixtures into a tmp repo root for isolated testing."""
    for rel in ("mappings/demo_sample_orders", "tests/fixtures/demo"):
        src = _FIXTURE_ROOT / rel
        if src.exists():
            shutil.copytree(src, tmp_path / rel, dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# #375 -- "live mode" follows a real reachability probe, not bool(dsn)
# ---------------------------------------------------------------------------


def test_run_reports_offline_when_dsn_unreachable(tmp_path, monkeypatch, capsys):
    # A --dsn is passed but the probe says unreachable: run must NOT claim "live".
    _seed_repo(tmp_path)
    from seshat.demo import run as run_mod

    monkeypatch.setattr(run_mod, "probe_reachable", lambda dsn: False)

    class _Args:
        repo = str(tmp_path)
        dsn = "postgresql://baduser:badpass@127.0.0.1:5999/nodb"

    assert run_mod.run_run(_Args()) == 0
    out = capsys.readouterr().out.lower()
    assert "offline mode" in out
    assert "live mode" not in out


def test_run_reports_live_only_when_probe_succeeds(tmp_path, monkeypatch, capsys):
    # The probe (not the flag) decides liveness.
    _seed_repo(tmp_path)
    from seshat.demo import run as run_mod

    monkeypatch.setattr(run_mod, "probe_reachable", lambda dsn: True)

    class _Args:
        repo = str(tmp_path)
        dsn = "postgresql://u:p@localhost:5432/demo"

    assert run_mod.run_run(_Args()) == 0
    out = capsys.readouterr().out.lower()
    assert "live mode" in out


def test_run_never_probes_without_a_dsn(tmp_path, monkeypatch, capsys):
    # Pure-offline path stays driver-free: no DSN => no probe call at all.
    _seed_repo(tmp_path)
    from seshat.demo import run as run_mod

    def _boom(dsn):  # pragma: no cover - fires only on a regression
        raise AssertionError("probe_reachable must not be called without a DSN")

    monkeypatch.setattr(run_mod, "probe_reachable", _boom)

    class _Args:
        repo = str(tmp_path)
        dsn = None

    assert run_mod.run_run(_Args()) == 0
    assert "offline mode" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# #376 -- demo run resolves a DSN from .env, exactly as demo load does
# ---------------------------------------------------------------------------


def test_run_resolves_dsn_from_workspace_dotenv(tmp_path, monkeypatch):
    # Mirror test_demo_load_resolves_dsn_from_workspace_dotenv: a DSN configured in
    # the workspace .env must reach demo run's resolution, not be ignored.
    for key in ("DATABASE_URL", "ANALYTICS_DB_HOST", "ANALYTICS_DB_NAME"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql://u:p@127.0.0.1:5432/somedb\n", encoding="utf-8"
    )

    from seshat.demo.run import resolve_dsn

    class _Args:
        repo = str(tmp_path)
        dsn = None

    assert resolve_dsn(_Args()) == "postgresql://u:p@127.0.0.1:5432/somedb"


def test_run_and_load_share_one_resolver(tmp_path):
    # #376 root cause: the two verbs must resolve DSNs via ONE helper, not two.
    from seshat.demo.load import _resolve_dsn as load_resolver
    from seshat.demo.run import resolve_dsn as run_resolver

    assert load_resolver is run_resolver


# ---------------------------------------------------------------------------
# #379 -- live-leg connect failure is redacted + non-zero, never a raw trace
# ---------------------------------------------------------------------------


def test_load_live_leg_redacts_dsn_on_connect_failure(tmp_path, monkeypatch, capsys):
    _seed_repo(tmp_path)

    # A resolvable DSN carrying credentials; psycopg2 present but connect raises a
    # reformatted error that echoes host/user/password (the psycopg2 shape).
    creds_dsn = "postgresql://secretuser:secretpass@unreachable.example:5432/db"

    class _FakeOperationalError(Exception):
        pass

    class _FakePsycopg2:
        OperationalError = _FakeOperationalError

        @staticmethod
        def connect(_dsn):
            raise _FakeOperationalError(
                'connection to server at "unreachable.example" failed: '
                "password authentication failed for user "
                '"secretuser" (password "secretpass")'
            )

    import sys

    monkeypatch.setitem(sys.modules, "psycopg2", _FakePsycopg2)

    from seshat.demo.load import run_load

    class _Args:
        repo = str(tmp_path)
        dsn = creds_dsn

    code = run_load(_Args())
    out = capsys.readouterr().out + capsys.readouterr().err
    # Non-zero: a load the user asked for failed; do not silently hide it.
    assert code != 0
    # No credential or host component leaks into any output.
    assert "secretuser" not in out
    assert "secretpass" not in out
    assert "unreachable.example" not in out
