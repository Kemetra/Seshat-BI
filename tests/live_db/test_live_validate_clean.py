"""US1: prove the four live checks pass against a clean seeded container (spec 082).

Requires the ``livetest`` extra (testcontainers) AND a running Docker daemon. When
either is absent the module import-skips (testcontainers) or the fixture skips
honestly (Docker) -- it never fakes a pass.
"""

import pytest

pytest.importorskip("testcontainers")  # collection-skip when livetest extra absent

from seshat import readiness_evidence, validate  # noqa: E402

pytestmark = pytest.mark.live_db


def _targets() -> validate.ValidationTargets:
    """The four live-check targets pointed at the seeded generic tables."""
    return validate.ValidationTargets(
        pk=validate.PkTarget(
            table="gold.fct_order_line", pk_columns=("order_line_id",)
        ),
        date_coverage=validate.DateCoverageTarget(
            fact="gold.fct_order_line",
            fact_date="date_key",
            date_dim="gold.dim_date",
            dim_date="date_key",
        ),
        orphans=validate.OrphanTarget(
            fact="gold.fct_order_line",
            fks=(("product_key", "gold.dim_product", "product_key"),),
        ),
        reconcile=validate.ReconcileTarget(
            silver="silver.stg_order_line",
            gold="gold.fct_order_line",
            measures=("net_amount",),
        ),
    )


@pytest.mark.seed("seed_clean.sql")
def test_clean_run_all_checks_pass(live_db_container):
    """T013: a clean seed -> all four live checks run, zero ERROR findings."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    findings = validate.run_live_checks(runner, _targets())
    assert findings == [], f"expected zero findings on clean seed, got: {findings}"


@pytest.mark.seed("seed_clean.sql")
def test_clean_run_feeds_evidence_recorder(live_db_container):
    """T014: the clean live findings feed 057's recorder -> warning, never pass."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    findings = validate.run_live_checks(runner, _targets())
    # FR-014: a human-readable line stating run mode + table identity.
    print("run_mode=live table=gold.fct_order_line (generic seed)")
    block = readiness_evidence.build_gold_ready_block(
        findings,
        table_identity="gold.fct_order_line",
        run_mode="live",
    )
    assert (
        block["status"] == "warning"
    )  # clean live run is warning, never pass (FR-012)
    assert block.get("evidence")  # non-empty evidence
    # no numeric score anywhere in the block (hard rule #9)
    for value in block.values():
        assert not isinstance(value, (int, float)) or isinstance(value, bool)
