"""US2: prove each live check catches its own seeded defect (spec 082).

Each scenario seeds one defect in its own fresh container and runs all four checks,
asserting exactly the expected ERROR and no cross-contamination from the others.
Requires the ``livetest`` extra + a running Docker daemon; otherwise import-skips /
fixture-skips honestly.
"""

import pytest

pytest.importorskip("testcontainers")  # collection-skip when livetest extra absent

from seshat import validate  # noqa: E402
from seshat.core import Severity  # noqa: E402
from tests.live_db.test_live_validate_clean import _targets  # noqa: E402

pytestmark = pytest.mark.live_db


def _errors(findings):
    return [f for f in findings if f.severity is Severity.ERROR]


@pytest.mark.seed("seed_defect_pk_duplicate.sql")
def test_pk_duplicate_yields_v_rc2(live_db_container):
    """T020: a duplicate grain -> exactly one V-RC2 ERROR, nothing else."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    errs = _errors(validate.run_live_checks(runner, _targets()))
    assert len(errs) == 1, f"expected exactly one ERROR, got: {errs}"
    assert errs[0].rule_id == "V-RC2"


@pytest.mark.seed("seed_defect_date_gap.sql")
def test_date_gap_yields_v_rc15(live_db_container):
    """T021: a fact date outside dim_date -> exactly one V-RC15 ERROR."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    errs = _errors(validate.run_live_checks(runner, _targets()))
    assert len(errs) == 1, f"expected exactly one ERROR, got: {errs}"
    assert errs[0].rule_id == "V-RC15"


@pytest.mark.seed("seed_defect_orphan_fk.sql")
def test_orphan_fk_yields_v_rc16(live_db_container):
    """T022: an orphan product_key -> exactly one V-RC16 (orphan) ERROR."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    errs = _errors(validate.run_live_checks(runner, _targets()))
    assert len(errs) == 1, f"expected exactly one ERROR, got: {errs}"
    assert errs[0].rule_id == "V-RC16"
    assert "orphan" in errs[0].message.lower()


@pytest.mark.seed("seed_defect_reconciliation_mismatch.sql")
def test_reconciliation_mismatch_yields_v_rc16(live_db_container):
    """T023: a one-cent silver/gold gap -> exactly one V-RC16 (reconcile) ERROR."""
    runner = validate.make_psycopg2_runner(live_db_container.dsn)
    errs = _errors(validate.run_live_checks(runner, _targets()))
    assert len(errs) == 1, f"expected exactly one ERROR, got: {errs}"
    assert errs[0].rule_id == "V-RC16"
    assert (
        "orphan" not in errs[0].message.lower()
    )  # the reconcile V-RC16, not the orphan one
