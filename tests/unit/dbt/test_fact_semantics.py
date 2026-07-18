from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


_VALID_MAP = """\
table_id: retail_store_sales
gold_star:
  fact:
    name: "gold.fct_sales_rss"
    grain: "one row = one retail transaction"
    business_key: "transaction_id"
    measures:
      - "quantity"
      - "total_spent"
    additive_money_measures:
      - "total_spent"
"""


def _write_map(tmp_path: Path, text: str) -> Path:
    source_map = tmp_path / "source-map.yaml"
    source_map.write_text(text, encoding="utf-8")
    return source_map


def test_load_fact_semantics_reads_declared_tags(tmp_path: Path) -> None:
    from seshat.dbt.fact_semantics import load_fact_semantics

    fact = load_fact_semantics(_write_map(tmp_path, _VALID_MAP))

    # The schema-qualified declared name normalizes to the bare MODEL name --
    # evidence compares it against the built fact model.
    assert fact.name == "fct_sales_rss"
    assert fact.business_key == ("transaction_id",)
    assert fact.additive_money_measures == ("total_spent",)


def test_composite_business_key_keeps_declared_order(tmp_path: Path) -> None:
    """A composite grain (e.g. invoice_no + line_no) declares its key as an
    ordered column list; the order is the grain declaration, so it is
    preserved verbatim, never sorted."""
    from seshat.dbt.fact_semantics import load_fact_semantics

    text = _VALID_MAP.replace(
        'business_key: "transaction_id"',
        'business_key: ["invoice_no", "line_no"]',
    )

    fact = load_fact_semantics(_write_map(tmp_path, text))

    assert fact.business_key == ("invoice_no", "line_no")


def test_factless_fact_declares_an_empty_money_set(tmp_path: Path) -> None:
    """templates/factless-fact.yaml requires measures: [] by design -- an
    explicitly declared empty additive_money_measures is a decision, not an
    omission, and parity then requires ZERO additive_money_total rows."""
    from seshat.dbt.fact_semantics import load_fact_semantics

    text = _VALID_MAP.replace(
        '    measures:\n      - "quantity"\n      - "total_spent"\n'
        '    additive_money_measures:\n      - "total_spent"\n',
        "    measures: []\n    additive_money_measures: []\n",
    )

    fact = load_fact_semantics(_write_map(tmp_path, text))

    assert fact.additive_money_measures == ()


def test_load_fact_semantics_sorts_money_measures_for_determinism(
    tmp_path: Path,
) -> None:
    from seshat.dbt.fact_semantics import load_fact_semantics

    text = _VALID_MAP.replace(
        '    measures:\n      - "quantity"\n      - "total_spent"\n'
        '    additive_money_measures:\n      - "total_spent"\n',
        '    measures:\n      - "quantity"\n      - "total_spent"\n'
        '      - "net_amount"\n'
        '    additive_money_measures:\n      - "total_spent"\n'
        '      - "net_amount"\n',
    )

    fact = load_fact_semantics(_write_map(tmp_path, text))

    assert fact.additive_money_measures == ("net_amount", "total_spent")


def test_missing_source_map_is_invalid(tmp_path: Path) -> None:
    from seshat.dbt.contracts import GovernanceError
    from seshat.dbt.fact_semantics import load_fact_semantics

    with pytest.raises(GovernanceError) as excinfo:
        load_fact_semantics(tmp_path / "absent.yaml")

    assert excinfo.value.code == "DBT_FACT_SEMANTICS_INVALID"


@pytest.mark.parametrize(
    ("text", "code", "match"),
    (
        pytest.param(
            "table_id: retail_store_sales\n",
            "DBT_FACT_SEMANTICS_MISSING",
            "gold_star.fact",
            id="no-gold-star",
        ),
        pytest.param(
            "gold_star:\n  fact: fct_sales\n",
            "DBT_FACT_SEMANTICS_MISSING",
            "gold_star.fact",
            id="fact-not-a-mapping",
        ),
        pytest.param(
            _VALID_MAP.replace('    business_key: "transaction_id"\n', ""),
            "DBT_FACT_SEMANTICS_MISSING",
            "business_key",
            id="no-business-key",
        ),
        pytest.param(
            _VALID_MAP.replace(
                '    additive_money_measures:\n      - "total_spent"\n', ""
            ),
            "DBT_FACT_SEMANTICS_MISSING",
            "additive_money_measures",
            id="no-money-measures",
        ),
        pytest.param(
            "not yaml: [unclosed\n",
            "DBT_FACT_SEMANTICS_INVALID",
            "source map",
            id="invalid-yaml",
        ),
        pytest.param(
            _VALID_MAP.replace('    name: "gold.fct_sales_rss"\n', ""),
            "DBT_FACT_SEMANTICS_MISSING",
            "name",
            id="no-fact-name",
        ),
        pytest.param(
            _VALID_MAP.replace('name: "gold.fct_sales_rss"', 'name: "gold.Fct-Sales"'),
            "DBT_FACT_SEMANTICS_INVALID",
            "name",
            id="fact-name-not-identifier",
        ),
        pytest.param(
            _VALID_MAP.replace(
                'business_key: "transaction_id"', 'business_key: "Bad-Name"'
            ),
            "DBT_FACT_SEMANTICS_INVALID",
            "business_key",
            id="business-key-not-identifier",
        ),
        pytest.param(
            _VALID_MAP.replace('business_key: "transaction_id"', "business_key: []"),
            "DBT_FACT_SEMANTICS_INVALID",
            "business_key",
            id="empty-business-key-list",
        ),
        pytest.param(
            _VALID_MAP.replace(
                'business_key: "transaction_id"',
                'business_key: ["invoice_no", "invoice_no"]',
            ),
            "DBT_FACT_SEMANTICS_INVALID",
            "business_key",
            id="duplicate-business-key-columns",
        ),
        pytest.param(
            _VALID_MAP.replace(
                'additive_money_measures:\n      - "total_spent"\n',
                'additive_money_measures:\n      - "total_spent"\n'
                '      - "total_spent"\n',
            ),
            "DBT_FACT_SEMANTICS_INVALID",
            "duplicate",
            id="duplicate-money-measures",
        ),
        pytest.param(
            _VALID_MAP.replace(
                'additive_money_measures:\n      - "total_spent"\n',
                'additive_money_measures:\n      - "price_per_unit"\n',
            ),
            "DBT_FACT_SEMANTICS_INVALID",
            "measures",
            id="money-not-a-declared-measure",
        ),
        pytest.param(
            _VALID_MAP.replace(
                '    measures:\n      - "quantity"\n      - "total_spent"\n'
                '    additive_money_measures:\n      - "total_spent"\n',
                '    measures:\n      - "quantity"\n      - "transaction_id"\n'
                '    additive_money_measures:\n      - "transaction_id"\n',
            ),
            "DBT_FACT_SEMANTICS_INVALID",
            "business_key",
            id="business-key-tagged-as-money",
        ),
    ),
)
def test_invalid_fact_semantics_fail_closed(
    tmp_path: Path, text: str, code: str, match: str
) -> None:
    from seshat.dbt.contracts import GovernanceError
    from seshat.dbt.fact_semantics import load_fact_semantics

    with pytest.raises(GovernanceError, match=match) as excinfo:
        load_fact_semantics(_write_map(tmp_path, text))

    assert excinfo.value.code == code


def test_measures_list_is_optional_for_the_dbt_path(tmp_path: Path) -> None:
    """The live-validate path requires `measures`; the dbt path must not break a
    map that declares only the parity tags (subset rule applies only when the
    measures list is present)."""
    from seshat.dbt.fact_semantics import load_fact_semantics

    text = _VALID_MAP.replace(
        '    measures:\n      - "quantity"\n      - "total_spent"\n', ""
    )

    fact = load_fact_semantics(_write_map(tmp_path, text))

    assert fact.additive_money_measures == ("total_spent",)
