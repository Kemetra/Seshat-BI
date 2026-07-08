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
