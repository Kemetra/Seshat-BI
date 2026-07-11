from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]

_SYNTH = """\
meta:
  table_id: t
columns:
  - source_name: keep_clean
    decision: keep
    pii: false
  - source_name: kept_pii
    decision: keep
    pii: true
  - source_name: dropped_pii
    decision: drop
    pii: true
  - source_name: dropped_plain
    decision: drop
    pii: false
derived_columns:
  - name: is_return
    derived_from: txn_type
"""


def _write(tmp_path, text):
    p = tmp_path / "source-map.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_dropped_pii_is_pii_true_and_decision_drop_only(tmp_path):
    from seshat.drift_semantics import load_drift_semantics

    sem = load_drift_semantics(_write(tmp_path, _SYNTH))
    # only dropped_pii qualifies: kept_pii is kept, dropped_plain isn't pii
    assert sem.dropped_pii_columns == frozenset({"dropped_pii"})


def test_returns_column_is_the_derived_from_source_column(tmp_path):
    from seshat.drift_semantics import load_drift_semantics

    sem = load_drift_semantics(_write(tmp_path, _SYNTH))
    assert sem.returns_column == "txn_type"  # NOT "is_return" (the derived name)


# A minimal one-column map, plus whatever derived_columns block the test needs.
_ONE_COL = "columns:\n  - source_name: a\n    decision: keep\n    pii: false\n"


def test_empty_derived_columns_means_no_returns_column(tmp_path):
    from seshat.drift_semantics import load_drift_semantics

    sem = load_drift_semantics(_write(tmp_path, _ONE_COL + "derived_columns: []\n"))
    assert sem.returns_column is None


def test_placeholder_derived_from_means_no_returns_column(tmp_path):
    from seshat.drift_semantics import load_drift_semantics

    derived = (
        "derived_columns:\n"
        "  - name: is_return\n"
        '    derived_from: "<authoritative_type_col>"\n'
    )
    sem = load_drift_semantics(_write(tmp_path, _ONE_COL + derived))
    assert sem.returns_column is None


def test_missing_columns_key_raises(tmp_path):
    from seshat.drift_semantics import load_drift_semantics

    with pytest.raises(ValueError, match="columns"):
        load_drift_semantics(_write(tmp_path, "meta:\n  table_id: t\n"))


def test_missing_pii_or_decision_fields_are_conservative(tmp_path):
    from seshat.drift_semantics import load_drift_semantics

    # a column with no pii key and no decision key must NOT count as dropped-PII
    text = "columns:\n  - source_name: bare\n"
    sem = load_drift_semantics(_write(tmp_path, text))
    assert sem.dropped_pii_columns == frozenset()


def test_real_retail_store_sales_mapping_is_a_noop(tmp_path):
    # DOCUMENTED no-op: RC8-deviated (derived_columns: []) + the one pii:true
    # column (customer_id) is decision:keep. Guards against a future mapping
    # change silently activating a class.
    from seshat.drift_semantics import load_drift_semantics

    real = _ROOT / "mappings" / "retail_store_sales" / "source-map.yaml"
    sem = load_drift_semantics(real)
    assert sem.returns_column is None
    assert sem.dropped_pii_columns == frozenset()
