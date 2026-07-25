"""The advisory column-shape comparison (issue #492).

The four parity assertions are value-only, so a shadow model whose column SET
diverges from its migrations counterpart passes every one of them. These tests pin
the advisory that makes that visible -- and pin that it stays ADVISORY: no
assertion class, no blocker code, no exit-code effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from seshat.dbt.column_drift import (
    ColumnShapeAdvisory,
    column_shape_advisories,
    migration_column_sets,
)

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _Column:
    name: str


@dataclass(frozen=True)
class _Contract:
    name: str
    columns: tuple[_Column, ...]
    table_id: str = "t"


def _contract(name: str, *columns: str) -> _Contract:
    return _Contract(name=name, columns=tuple(_Column(c) for c in columns))


def _migration(root: Path, name: str, body: str) -> None:
    directory = root / "warehouse" / "migrations"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body, encoding="utf-8")


_DATE_DDL = """
CREATE TABLE gold.dim_date_c086 (
  date_sk   INT PRIMARY KEY,
  full_date DATE,
  year      SMALLINT,
  month     SMALLINT,
  day       SMALLINT
);
"""


def test_divergent_column_set_raises_an_advisory(tmp_path: Path) -> None:
    """The exact live divergence from issue #492: the shadow date dimension carries
    `quarter` + `iso_week` that migrations does not, while the member count matches
    exactly (1096 = 1096) so `dimension_member_count` passes clean."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path,
        [
            _contract(
                "dim_date_c086",
                "date_sk",
                "full_date",
                "year",
                "quarter",
                "month",
                "day",
                "iso_week",
            )
        ],
    )

    assert len(advisories) == 1
    advisory = advisories[0]
    assert advisory.model == "dim_date_c086"
    assert advisory.shadow_only == ("iso_week", "quarter")
    assert advisory.migrations_only == ()
    assert "warehouse/migrations/0004_gold.sql" in advisory.message()
    assert "quarter" in advisory.message()


def test_identical_column_set_stays_silent(tmp_path: Path) -> None:
    """The same pair, aligned: no finding. An advisory that fired on a matching
    shape would be noise on every clean project."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path,
        [_contract("dim_date_c086", "date_sk", "full_date", "year", "month", "day")],
    )

    assert advisories == ()


def test_migrations_only_column_is_reported(tmp_path: Path) -> None:
    """Drift is symmetric: a column migrations builds and the shadow drops is just
    as invisible to the four value assertions."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path, [_contract("dim_date_c086", "date_sk", "full_date", "year")]
    )

    assert advisories[0].migrations_only == ("day", "month")
    assert advisories[0].shadow_only == ()
    assert "migrations-only" in advisories[0].message()


def test_renamed_column_is_reported_on_both_sides(tmp_path: Path) -> None:
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    advisories = column_shape_advisories(
        tmp_path,
        [_contract("dim_date_c086", "date_sk", "full_date", "year", "month", "dom")],
    )

    assert advisories[0].shadow_only == ("dom",)
    assert advisories[0].migrations_only == ("day",)


def test_model_without_a_migrations_counterpart_is_silent(tmp_path: Path) -> None:
    """A shadow-only star migrations never built is a normal state, not a defect."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    assert column_shape_advisories(tmp_path, [_contract("dim_brand_new", "a")]) == ()


def test_absent_migrations_directory_is_silent(tmp_path: Path) -> None:
    assert column_shape_advisories(tmp_path, [_contract("dim_x", "a")]) == ()
    assert migration_column_sets(tmp_path) == {}


def test_skip_suppresses_the_named_model(tmp_path: Path) -> None:
    """The parity audit model is derived evidence; migrations never build it."""
    _migration(
        tmp_path, "0004_gold.sql", "CREATE TABLE gold.audit_t_parity (\n  a INT\n);"
    )

    assert (
        column_shape_advisories(
            tmp_path,
            [_contract("audit_t_parity", "a", "b")],
            skip=frozenset({"audit_t_parity"}),
        )
        == ()
    )


def test_table_constraints_and_nested_commas_are_not_columns(tmp_path: Path) -> None:
    """`NUMERIC(12,2)` must not split into two columns, and a table-level
    PRIMARY KEY / FOREIGN KEY / UNIQUE clause is not a column."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        """
CREATE TABLE gold.fct_x (
  fct_x_sk INT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  total_spent NUMERIC(12,2),
  qty NUMERIC(12,2),
  CONSTRAINT uq_x UNIQUE (fct_x_sk),
  PRIMARY KEY (fct_x_sk),
  FOREIGN KEY (fct_x_sk) REFERENCES gold.dim_y (y_sk)
);
""",
    )

    columns, _ = migration_column_sets(tmp_path)["fct_x"]
    assert columns == frozenset({"fct_x_sk", "total_spent", "qty"})
    assert (
        column_shape_advisories(
            tmp_path, [_contract("fct_x", "fct_x_sk", "total_spent", "qty")]
        )
        == ()
    )


def test_comments_are_stripped_before_parsing(tmp_path: Path) -> None:
    _migration(
        tmp_path,
        "0004_gold.sql",
        """
CREATE TABLE gold.dim_c (
  c_sk INT PRIMARY KEY,   -- surrogate, not a column named "surrogate"
  label TEXT              -- natural key
);
""",
    )

    columns, _ = migration_column_sets(tmp_path)["dim_c"]
    assert columns == frozenset({"c_sk", "label"})


def test_unparseable_definition_degrades_to_no_finding(tmp_path: Path) -> None:
    """Fail-SAFE: a body this narrow parser cannot classify yields no table entry,
    so it can never manufacture a bogus symmetric difference."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "CREATE TABLE gold.dim_weird (\n  (a + b) INT,\n  c TEXT\n);",
    )

    assert "dim_weird" not in migration_column_sets(tmp_path)
    assert column_shape_advisories(tmp_path, [_contract("dim_weird", "c")]) == ()


def test_alter_table_add_column_skips_the_table(tmp_path: Path) -> None:
    """#501 review: the CREATE body is a STALE view once a later migration ADDs a
    column, so the table is dropped from the comparison rather than compared
    against a shape known to be out of date. The shadow here is ALIGNED with the
    post-ALTER shape {a, b} -- the pre-fix behaviour would have falsely flagged
    `b` as shadow-only."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_alter.sql", "ALTER TABLE gold.dim_a ADD COLUMN b TEXT;")

    assert "dim_a" not in migration_column_sets(tmp_path)
    assert column_shape_advisories(tmp_path, [_contract("dim_a", "a", "b")]) == ()


def test_alter_table_add_column_also_silences_a_divergent_pair(tmp_path: Path) -> None:
    """The skip is symmetric and deliberate: an unknown migration shape yields NO
    finding in either direction. Guessing from a stale CREATE could just as easily
    reassure falsely as alarm falsely."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_alter.sql", "ALTER TABLE gold.dim_a ADD COLUMN b TEXT;")

    assert column_shape_advisories(tmp_path, [_contract("dim_a", "zzz")]) == ()


@pytest.mark.parametrize(
    "statement",
    [
        "ALTER TABLE gold.dim_a DROP COLUMN a;",
        "ALTER TABLE gold.dim_a RENAME COLUMN a TO b;",
        "ALTER TABLE IF EXISTS gold.dim_a ADD COLUMN b TEXT;",
        "ALTER TABLE ONLY gold.dim_a DROP COLUMN a;",
        "alter table gold.dim_a add column b text;",
        # Postgres permits omitting the COLUMN keyword for ADD/DROP...
        "ALTER TABLE gold.dim_a ADD b TEXT;",
        "ALTER TABLE gold.dim_a DROP a;",
        # ...and for RENAME (#501 review, finding A).
        "ALTER TABLE gold.dim_a RENAME a TO b;",
        "alter table gold.dim_a rename a to b;",
        "ALTER TABLE IF EXISTS gold.dim_a RENAME a TO b;",
    ],
)
def test_every_column_changing_alter_form_skips_the_table(
    tmp_path: Path, statement: str
) -> None:
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_alter.sql", statement)

    assert "dim_a" not in migration_column_sets(tmp_path), statement


@pytest.mark.parametrize(
    "statement",
    [
        "ALTER TABLE gold.dim_a ADD CONSTRAINT uq_a UNIQUE (a);",
        "ALTER TABLE gold.dim_a ADD PRIMARY KEY (a);",
        "ALTER TABLE gold.dim_a ADD FOREIGN KEY (a) REFERENCES gold.dim_b (b);",
        "ALTER TABLE gold.dim_a ADD CHECK (a > 0);",
        "ALTER TABLE gold.dim_a DROP CONSTRAINT uq_a;",
        "ALTER TABLE gold.dim_a ALTER COLUMN a TYPE BIGINT;",
        "ALTER TABLE gold.dim_a ALTER COLUMN a SET NOT NULL;",
        "ALTER TABLE gold.dim_a RENAME CONSTRAINT uq_a TO uq_b;",
    ],
)
def test_non_column_altering_statements_do_not_suppress_a_finding(
    tmp_path: Path, statement: str
) -> None:
    """A constraint-only or type-only ALTER does not change the column SET, so it
    must NOT silence a genuine divergence -- otherwise one `ADD CONSTRAINT` (which
    the real committed migration uses five times) would blind the whole check."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_alter.sql", statement)

    assert "dim_a" in migration_column_sets(tmp_path), statement
    advisories = column_shape_advisories(tmp_path, [_contract("dim_a", "a", "extra")])
    assert advisories[0].shadow_only == ("extra",), statement


def test_commented_out_alter_does_not_disable_shape_checking(tmp_path: Path) -> None:
    """#501 review, finding B: the nastiest direction, because it fails SILENTLY
    toward no-checking. A commented-out ALTER must not add the table to `altered`
    and thereby switch off its shape comparison entirely."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(
        tmp_path,
        "0005_notes.sql",
        "-- ALTER TABLE gold.dim_a ADD COLUMN b TEXT;  (planned, not applied)\n"
        "/* ALTER TABLE gold.dim_a DROP COLUMN a; */\n",
    )

    assert "dim_a" in migration_column_sets(tmp_path)
    advisories = column_shape_advisories(tmp_path, [_contract("dim_a", "a", "extra")])
    assert advisories[0].shadow_only == ("extra",)


def test_commented_out_create_does_not_override_the_real_shape(tmp_path: Path) -> None:
    """A CREATE TABLE inside a comment must not become the compared shape."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "CREATE TABLE gold.dim_a (\n  a INT,\n  b TEXT\n);",
    )
    _migration(
        tmp_path,
        "0005_notes.sql",
        "/*\nCREATE TABLE gold.dim_a (\n  only_this INT\n);\n*/\n",
    )

    columns, _ = migration_column_sets(tmp_path)["dim_a"]
    assert columns == frozenset({"a", "b"})
    assert column_shape_advisories(tmp_path, [_contract("dim_a", "a", "b")]) == ()


def test_comment_markers_inside_string_literals_are_preserved(tmp_path: Path) -> None:
    """The reviewer's own caveat: `--` inside a quoted literal is DATA, not a
    comment. Blanking it would corrupt the statement being parsed."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "CREATE TABLE gold.dim_a (\n  a INT,\n  label TEXT\n);\n"
        "INSERT INTO gold.dim_a VALUES (-1, 'UNKNOWN -- not a comment');\n"
        "INSERT INTO gold.dim_a VALUES (-2, 'slash /* star */ inside');\n",
    )

    columns, _ = migration_column_sets(tmp_path)["dim_a"]
    assert columns == frozenset({"a", "label"})


def test_an_alter_inside_a_string_literal_does_not_trip_the_guard(
    tmp_path: Path,
) -> None:
    """Symmetric to the above: ALTER text quoted as data is not a real statement."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(
        tmp_path,
        "0005_log.sql",
        "INSERT INTO audit.log VALUES ('ALTER TABLE gold.dim_a ADD COLUMN b TEXT');\n",
    )

    assert "dim_a" in migration_column_sets(tmp_path)


def test_same_name_in_another_schema_does_not_replace_the_gold_oracle(
    tmp_path: Path,
) -> None:
    """#501 review, finding C: silver/gold mirror names are natural in a medallion
    layout. The gold shape must win regardless of definition order, not lose to
    last-write-wins on the bare table name."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "CREATE TABLE gold.dim_customer (\n  customer_sk INT,\n  customer_id TEXT\n);",
    )
    # Defined LATER, so a bare-name index would have overwritten the gold shape.
    _migration(
        tmp_path,
        "0005_silver.sql",
        "CREATE TABLE silver.dim_customer (\n  raw_id TEXT,\n  loaded_at TIMESTAMP\n);",
    )

    columns, relpath = migration_column_sets(tmp_path)["dim_customer"]
    assert columns == frozenset({"customer_sk", "customer_id"})
    assert relpath.endswith("0004_gold.sql")
    assert (
        column_shape_advisories(
            tmp_path, [_contract("dim_customer", "customer_sk", "customer_id")]
        )
        == ()
    )


def test_an_alter_on_the_silver_twin_does_not_silence_the_gold_table(
    tmp_path: Path,
) -> None:
    """The ALTER guard is schema-scoped too: reshaping `silver.dim_customer` says
    nothing about the gold relation and must not suppress its comparison."""
    _migration(
        tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_customer (\n  a INT\n);"
    )
    _migration(
        tmp_path,
        "0005_silver.sql",
        "CREATE TABLE silver.dim_customer (\n  a INT\n);\n"
        "ALTER TABLE silver.dim_customer ADD COLUMN b TEXT;\n",
    )

    assert "dim_customer" in migration_column_sets(tmp_path)
    advisories = column_shape_advisories(
        tmp_path, [_contract("dim_customer", "a", "extra")]
    )
    assert advisories[0].shadow_only == ("extra",)


def test_unqualified_create_table_is_dropped_as_indeterminate(tmp_path: Path) -> None:
    """An unqualified name resolves through `search_path` at run time, which a static
    read cannot know. Its layer is indeterminate, so it is skipped rather than
    assumed to be the gold oracle -- the same honest-silence rule as ALTER."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE dim_loose (\n  a INT\n);")

    assert migration_column_sets(tmp_path) == {}
    assert column_shape_advisories(tmp_path, [_contract("dim_loose", "zzz")]) == ()


def test_non_gold_schema_alone_yields_no_comparison(tmp_path: Path) -> None:
    """dbt materializes gold and stops (ADR-0009 d.6), so a silver-only table has no
    legitimate mart counterpart to compare."""
    _migration(tmp_path, "0003_silver.sql", "CREATE TABLE silver.stg_x (\n  a INT\n);")

    assert migration_column_sets(tmp_path) == {}


_REAL_MIGRATION_SHAPES = {
    "dim_customer_rss": 2,
    "dim_date_rss": 10,
    "dim_location_rss": 2,
    "dim_payment_method_rss": 2,
    "dim_product_rss": 3,
    "fct_sales_rss": 11,
}


def test_committed_migrations_still_yield_exactly_the_six_gold_tables() -> None:
    """THE census guard (#501 review, finding B).

    The committed `0004_..._star.sql` is idempotent: all six `DROP TABLE IF EXISTS`
    statements (lines 22-27) precede ALL six `CREATE TABLE`s. Naive DROP handling
    would therefore remove the fact and every dimension from the comparison, and the
    advisory census would still read "0 advisories" -- for entirely the wrong reason.

    So this asserts the table COUNT and every per-table column count, not just the
    absence of findings. "0 advisories" alone is not evidence the check is running."""
    root = Path(__file__).resolve().parents[3]
    tables = migration_column_sets(root)

    assert set(tables) == set(_REAL_MIGRATION_SHAPES), sorted(tables)
    assert len(tables) == 6
    actual = {name: len(shape[0]) for name, shape in tables.items()}
    assert actual == _REAL_MIGRATION_SHAPES


def test_drop_then_create_in_the_same_file_ends_up_created(tmp_path: Path) -> None:
    """The idempotent preamble pattern, in miniature: DROP first, CREATE after, in
    one file. Statement order decides -- the relation exists at the end."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "DROP TABLE IF EXISTS gold.dim_a;\nCREATE TABLE gold.dim_a (\n  a INT\n);",
    )

    columns, _ = migration_column_sets(tmp_path)["dim_a"]
    assert columns == frozenset({"a"})


def test_multiple_drops_before_all_creates_still_index_every_table(
    tmp_path: Path,
) -> None:
    """The exact shape of the real 0004 migration: every DROP precedes every CREATE.
    A per-file (rather than per-statement) order would empty the index here."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "DROP TABLE IF EXISTS gold.fct_x;\n"
        "DROP TABLE IF EXISTS gold.dim_a;\n"
        "DROP TABLE IF EXISTS gold.dim_b;\n"
        "CREATE TABLE gold.dim_a (\n  a INT\n);\n"
        "CREATE TABLE gold.dim_b (\n  b INT\n);\n"
        "CREATE TABLE gold.fct_x (\n  x INT,\n  a_sk INT\n);\n",
    )

    tables = migration_column_sets(tmp_path)
    assert set(tables) == {"dim_a", "dim_b", "fct_x"}
    assert len(tables["fct_x"][0]) == 2


def test_drop_without_recreate_is_omitted(tmp_path: Path) -> None:
    """A relation that ENDS the sequence dropped no longer exists, so a lingering
    shadow model must not be compared against it."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_drop.sql", "DROP TABLE gold.dim_a;")

    assert "dim_a" not in migration_column_sets(tmp_path)
    assert column_shape_advisories(tmp_path, [_contract("dim_a", "a")]) == ()


def test_drop_in_a_later_file_after_recreate_still_drops(tmp_path: Path) -> None:
    """File order matters as much as statement order."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "DROP TABLE IF EXISTS gold.dim_a;\nCREATE TABLE gold.dim_a (\n  a INT\n);",
    )
    _migration(tmp_path, "0006_drop.sql", "DROP TABLE IF EXISTS gold.dim_a CASCADE;")

    assert "dim_a" not in migration_column_sets(tmp_path)


def test_multi_target_drop_removes_every_named_relation(tmp_path: Path) -> None:
    _migration(
        tmp_path,
        "0004_gold.sql",
        "CREATE TABLE gold.dim_a (\n  a INT\n);\n"
        "CREATE TABLE gold.dim_b (\n  b INT\n);",
    )
    _migration(tmp_path, "0005_drop.sql", "DROP TABLE gold.dim_a, gold.dim_b CASCADE;")

    assert migration_column_sets(tmp_path) == {}


def test_drop_of_a_silver_twin_leaves_the_gold_table_indexed(tmp_path: Path) -> None:
    """DROP is schema-scoped, like the ALTER guard."""
    _migration(
        tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_customer (\n  a INT\n);"
    )
    _migration(
        tmp_path,
        "0005_silver.sql",
        "CREATE TABLE silver.dim_customer (\n  a INT\n);\n"
        "DROP TABLE silver.dim_customer;",
    )

    assert "dim_customer" in migration_column_sets(tmp_path)


def test_whole_table_rename_omits_both_old_and_new_names(tmp_path: Path) -> None:
    """#501 review, finding A: `RENAME TO` is correctly NOT a column change, but the
    index is keyed by NAME -- the old name would keep a shape for a relation that no
    longer exists, and the new name would have none. Omit both."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_rename.sql", "ALTER TABLE gold.dim_a RENAME TO dim_z;")

    tables = migration_column_sets(tmp_path)
    assert "dim_a" not in tables
    assert "dim_z" not in tables
    assert column_shape_advisories(tmp_path, [_contract("dim_a", "a")]) == ()
    assert column_shape_advisories(tmp_path, [_contract("dim_z", "a")]) == ()


def test_whole_table_rename_is_still_not_a_column_change(tmp_path: Path) -> None:
    """The narrowness must hold: a renamed-away table is omitted because its NAME no
    longer resolves, not because the parser thinks its columns changed. A table that
    is renamed TO an existing indexed name is likewise not treated as reshaped."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        "CREATE TABLE gold.dim_a (\n  a INT\n);\n"
        "CREATE TABLE gold.dim_keep (\n  k INT\n);",
    )
    _migration(tmp_path, "0005_rename.sql", "ALTER TABLE gold.dim_a RENAME TO dim_z;")

    # An unrelated table is untouched by someone else's rename.
    assert "dim_keep" in migration_column_sets(tmp_path)


def test_rename_to_is_not_classified_as_a_column_change(tmp_path: Path) -> None:
    """Guards the distinction directly at the classifier, not just at the outcome:
    `RENAME TO` must be absent from the column-changing set (`_altered_tables`) and
    present in the rename set (`_renamed_tables`). Conflating them would make a bare
    `RENAME a TO b` and a whole-table `RENAME TO b` indistinguishable."""
    from seshat.dbt.column_drift import _altered_tables, _renamed_tables

    whole_table = "ALTER TABLE gold.dim_a RENAME TO dim_z;"
    bare_column = "ALTER TABLE gold.dim_a RENAME a TO b;"

    assert _altered_tables(whole_table) == set()
    assert _renamed_tables(whole_table) == {("gold", "dim_a"), ("gold", "dim_z")}
    assert _altered_tables(bare_column) == {("gold", "dim_a")}
    assert _renamed_tables(bare_column) == set()


def test_quoted_mixed_case_identifier_makes_the_table_unparseable(
    tmp_path: Path,
) -> None:
    """#501 review, finding C: Postgres folds unquoted names to lower case but keeps
    quoted ones exactly, so `"CustomerID"` and `customerid` are DIFFERENT columns.
    This comparison is case-insensitive, so folding them would hide real drift --
    skip the table rather than compare on a wrong premise."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        'CREATE TABLE gold.dim_q (\n  "CustomerID" INT,\n  plain TEXT\n);',
    )

    assert "dim_q" not in migration_column_sets(tmp_path)
    assert column_shape_advisories(tmp_path, [_contract("dim_q", "customerid")]) == ()


def test_quoted_all_lowercase_identifier_is_still_parsed(tmp_path: Path) -> None:
    """Quoting alone is not the hazard -- CASE folding is. `"plain"` folds to itself,
    so it stays comparable and must not be discarded."""
    _migration(
        tmp_path,
        "0004_gold.sql",
        'CREATE TABLE gold.dim_q (\n  "plain" TEXT,\n  other INT\n);',
    )

    columns, _ = migration_column_sets(tmp_path)["dim_q"]
    assert columns == frozenset({"plain", "other"})


def test_committed_migration_add_constraint_clauses_are_not_treated_as_alters() -> None:
    """The shipped `0004_..._star.sql` ends with five `ADD CONSTRAINT` statements on
    `fct_sales_rss`. If the ALTER guard over-matched them, the fact would silently
    drop out of the comparison and the census would pass for the wrong reason."""
    root = Path(__file__).resolve().parents[3]
    tables = migration_column_sets(root)

    assert "fct_sales_rss" in tables
    columns, _ = tables["fct_sales_rss"]
    assert "transaction_id" in columns


def test_case_insensitive_on_both_sides(tmp_path: Path) -> None:
    _migration(
        tmp_path, "0004_gold.sql", "create table GOLD.Dim_Case (\n  Date_SK int\n);"
    )

    assert column_shape_advisories(tmp_path, [_contract("dim_case", "DATE_SK")]) == ()


def test_last_definition_wins_when_a_table_is_recreated(tmp_path: Path) -> None:
    """A later migration reshaping a table is the shape the oracle ends up with."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_r (\n  a INT\n);")
    _migration(
        tmp_path, "0005_gold.sql", "CREATE TABLE gold.dim_r (\n  a INT,\n  b TEXT\n);"
    )

    columns, relpath = migration_column_sets(tmp_path)["dim_r"]
    assert columns == frozenset({"a", "b"})
    assert relpath == "warehouse/migrations/0005_gold.sql"


def test_advisory_message_states_it_compares_the_unenforced_declaration(
    tmp_path: Path,
) -> None:
    """#501 review: the shadow side is the GOVERNED DECLARATION, which dbt does not
    enforce as a contract, so a built model can drift from its own `_models.yml`
    and stay invisible. The finding must say which shape it compared rather than
    let a reader infer built-vs-built coverage it does not have."""
    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)

    message = column_shape_advisories(
        tmp_path, [_contract("dim_date_c086", "date_sk")]
    )[0].message()

    assert "DECLARED" in message
    assert "_models.yml" in message
    assert "does not enforce" in message


def test_module_docstring_states_the_declared_vs_built_boundary() -> None:
    """The scope note travels with the module, not only with one rendered line."""
    from seshat.dbt import column_drift

    doc = column_drift.__doc__ or ""

    assert "DOES *NOT* COVER" in doc
    assert "enforced: true" in doc
    assert "information_schema" in doc


def test_advisory_carries_no_assertion_or_blocker_vocabulary() -> None:
    """The ruling: drift is a DISTINCT advisory finding, not a fifth parity
    assertion. Guard the shape so a later edit cannot quietly grow one."""
    fields = ColumnShapeAdvisory.__dataclass_fields__.keys()

    assert "assertion_class" not in fields
    assert "assertion_id" not in fields
    assert "passed" not in fields
    assert "code" not in fields
    assert "tolerance" not in fields


def test_advisory_message_never_uses_the_blocker_code_namespace(tmp_path: Path) -> None:
    """`DBT_[A-Z0-9_]+` is the blocking channel's namespace in the evidence schema."""
    import re

    _migration(tmp_path, "0004_gold.sql", _DATE_DDL)
    advisories = column_shape_advisories(
        tmp_path, [_contract("dim_date_c086", "date_sk")]
    )

    assert not re.search(r"DBT_[A-Z0-9_]+", advisories[0].message())


def test_committed_worked_example_is_no_finding() -> None:
    """The census requirement: the advisory must be silent on every committed
    worked-example model pair, or it would fire on a clean repo."""
    from seshat.dbt.gate import resolve_working_set
    from seshat.dbt.project import validate_project

    root = Path(__file__).resolve().parents[3]
    working_set = resolve_working_set(root, "retail_store_sales")
    project = validate_project(root, working_set, target_schema="seshat_dbt_shadow")

    advisories = column_shape_advisories(
        root,
        project.model_contracts,
        skip=frozenset({"audit_retail_store_sales_parity"}),
    )

    assert advisories == (), [a.message() for a in advisories]
