# tests/unit/test_cli_drift.py
import pytest

from retail.cli import main

pytestmark = pytest.mark.unit


def test_drift_without_dsn_is_deferred(capsys):
    rc = main(["drift", "--baseline", "mappings/retail_store_sales/source-profile.md"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "PENDING LIVE RE-PROFILE" in err or "deferred" in err.lower()


def test_drift_nonconformant_baseline_reports_uncomparable(capsys):
    rc = main(["drift", "--baseline", "mappings/demo_sample_orders/source-profile.md"])
    out = capsys.readouterr()
    assert rc == 1
    assert (
        "uncomparable" in (out.out + out.err).lower()
        or "non-conformant" in (out.out + out.err).lower()
    )


_CONFORMANT = "mappings/retail_store_sales/source-profile.md"


def test_drift_live_missing_driver_is_actionable(capsys, monkeypatch):
    # --dsn given but the optional DB driver is absent: gate like validate does
    # -- an actionable "pip install 'retail[db]'" message + rc 1, never a raw
    # ModuleNotFoundError traceback.
    from retail import cli

    monkeypatch.setattr(cli, "_ensure_driver", lambda: False)
    rc = main(["drift", "--baseline", _CONFORMANT, "--dsn", "postgresql://x@h/db"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "retail[db]" in err


def test_drift_live_db_error_is_scrubbed_not_leaked(capsys, monkeypatch):
    # A DB-boundary failure must NOT leak the DSN (user/host/password) verbatim.
    # Mirror validate.py: the exception is caught and run through the dialect
    # redactor before printing. The DSN embeds a password that must not appear.
    from retail import cli

    secret = "postgresql://admin:s3cr3t_pw@db.internal:5432/prod"

    monkeypatch.setattr(cli, "_ensure_driver", lambda: True)

    def _boom(config):
        raise RuntimeError(f"connection failed for {config}")

    monkeypatch.setattr(cli, "_make_runner", _boom)
    rc = main(["drift", "--baseline", _CONFORMANT, "--dsn", secret])
    out = capsys.readouterr()
    combined = out.out + out.err
    assert rc == 1
    assert "s3cr3t_pw" not in combined
    assert "connection failed" not in combined or "s3cr3t_pw" not in combined


def test_drift_live_loads_sibling_source_map(monkeypatch):
    # The live leg auto-discovers the sibling source-map.yaml and threads its
    # semantics into the comparison. Patched so no real DB is touched.
    import retail.cli.commands.drift as drift_cmd
    from retail import cli
    from retail.drift import DriftSemantics
    from retail.profile import PkProof, ProfileResult

    calls = {}

    monkeypatch.setattr(cli, "_ensure_driver", lambda: True)
    monkeypatch.setattr(cli, "_make_runner", lambda config: "RUNNER")

    def fake_loader(path):
        calls["path"] = str(path)
        return DriftSemantics()

    monkeypatch.setattr(drift_cmd, "load_drift_semantics", fake_loader, raising=False)

    def fake_profile(runner, table, pk):
        return ProfileResult(
            table=table,
            row_count=1,
            column_count=0,
            columns=(),
            pk=PkProof(total=1, distinct_pk=1, null_pk=0, is_unique=True),
        )

    monkeypatch.setattr("retail.profile.profile", fake_profile)

    main(["drift", "--baseline", _CONFORMANT, "--dsn", "postgresql://u@h/db"])
    # the sibling source-map.yaml next to the baseline was the loaded path
    assert (
        calls["path"]
        .replace("\\", "/")
        .endswith("mappings/retail_store_sales/source-map.yaml")
    )


def test_drift_source_map_flag_missing_file_is_clean_error(capsys, monkeypatch):
    from retail import cli

    monkeypatch.setattr(cli, "_ensure_driver", lambda: True)
    rc = main(
        [
            "drift",
            "--baseline",
            _CONFORMANT,
            "--dsn",
            "postgresql://u@h/db",
            "--source-map",
            "does/not/exist.yaml",
        ]
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "source-map" in err.lower()
