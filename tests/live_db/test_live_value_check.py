"""US3: prove the L4 value-check path live, both matching and mismatching (spec 082).

Requires the ``livetest`` extra + a running Docker daemon; otherwise import-skips /
fixture-skips honestly.
"""

from decimal import Decimal

import pytest

pytest.importorskip("testcontainers")  # collection-skip when livetest extra absent

from seshat import validate, value_proxy  # noqa: E402
from seshat.core import Severity  # noqa: E402

pytestmark = pytest.mark.live_db

# Seeded gold.fct_order_line net_amount total: 20.00 + 15.50 + 30.00 = 65.50.
_SEEDED_TOTAL = Decimal("65.50")


def _expected(value: Decimal) -> value_proxy.ExpectedValue:
    return value_proxy.ExpectedValue(
        value=value,
        tolerance_abs=Decimal("0"),  # penny-exact
        aggregation="sum",
        column="net_amount",
        gold_table="gold.fct_order_line",
    )


@pytest.mark.seed("seed_value_check.sql")
def test_matching_expected_value_no_finding(live_db_container):
    """T025: an ExpectedValue matching the seeded sum -> no finding (live pass)."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    findings = list(
        value_proxy.check_expected_value(runner, "net_sales", _expected(_SEEDED_TOTAL))
    )
    assert findings == [], f"expected no finding on an exact match, got: {findings}"


@pytest.mark.seed("seed_value_check.sql")
def test_mismatched_expected_value_yields_v_l4(live_db_container):
    """T026: an ExpectedValue perturbed beyond tolerance -> exactly one V-L4 ERROR."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    perturbed = _SEEDED_TOTAL + Decimal("100.00")
    findings = list(
        value_proxy.check_expected_value(runner, "net_sales", _expected(perturbed))
    )
    assert len(findings) == 1, f"expected exactly one V-L4 finding, got: {findings}"
    assert findings[0].rule_id == "V-L4"
    assert findings[0].severity is Severity.ERROR
