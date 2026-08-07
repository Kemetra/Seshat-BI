"""How the advisory READS committed migration DDL (issue #492, PR #501 reviews).

Separate module from ``test_column_drift.py`` (which pins the advisory's SEMANTICS)
because this is a distinct responsibility: what the narrow static SQL reader does
with ALTER, DROP, RENAME, comments, string literals, schema qualification, and
quoted identifiers.

The governing principle throughout is FAIL-SAFE, not fail-closed: every construct
the reader cannot interpret confidently resolves to NO FINDING rather than a wrong
one. Several tests here therefore assert SILENCE, and several others assert that a
guard does NOT fire -- an over-broad guard would silently stop checking, which is
the failure mode these reviews kept surfacing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.dbt.column_drift import column_shape_advisories, migration_column_sets
from tests.unit.dbt._column_drift_fixtures import (
    REAL_MIGRATION_SHAPES,
    repo_root,
)
from tests.unit.dbt._column_drift_fixtures import (
    contract as _contract,
)
from tests.unit.dbt._column_drift_fixtures import (
    migration as _migration,
)

pytestmark = pytest.mark.unit


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


def test_committed_migrations_still_yield_exactly_the_known_gold_tables() -> None:
    """THE census guard (#501 review, finding B).

    The committed `0004_..._star.sql` is idempotent: all six `DROP TABLE IF EXISTS`
    statements (lines 22-27) precede ALL six `CREATE TABLE`s. Naive DROP handling
    would therefore remove the fact and every dimension from the comparison, and the
    advisory census would still read "0 advisories" -- for entirely the wrong reason.
    `0008_create_gold_finance_gl_star.sql` (spec 137) repeats the same
    every-DROP-before-every-CREATE shape for its own two facts + five dims.

    So this asserts the table COUNT and every per-table column count, not just the
    absence of findings. "0 advisories" alone is not evidence the check is running."""
    root = repo_root()
    tables = migration_column_sets(root)

    assert set(tables) == set(REAL_MIGRATION_SHAPES), sorted(tables)
    assert len(tables) == len(REAL_MIGRATION_SHAPES)
    actual = {name: len(shape[0]) for name, shape in tables.items()}
    assert actual == REAL_MIGRATION_SHAPES


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


@pytest.mark.parametrize(
    "literal",
    [
        "$tag$ALTER TABLE gold.dim_a ADD COLUMN bogus TEXT;$tag$",
        "$$ALTER TABLE gold.dim_a DROP COLUMN a;$$",
        "$body$DROP TABLE gold.dim_a;$body$",
    ],
)
def test_dollar_quoted_ddl_is_data_not_a_statement(
    tmp_path: Path, literal: str
) -> None:
    """#501 review: Postgres dollar-quoting (`$$...$$` / `$tag$...$tag$`) delimits a
    LITERAL, so DDL inside one is data. Reading it as real DDL would silently exclude
    the table and hide genuine drift -- the same false-quiet class as the
    commented-out ALTER."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_data.sql", f"INSERT INTO gold.log VALUES ({literal});")

    assert "dim_a" in migration_column_sets(tmp_path), literal
    advisories = column_shape_advisories(tmp_path, [_contract("dim_a", "a", "extra")])
    assert advisories[0].shadow_only == ("extra",), literal


def test_a_real_alter_outside_a_dollar_quote_is_still_seen(tmp_path: Path) -> None:
    """The dollar-quote guard must not blind the scanner to genuine statements."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(
        tmp_path,
        "0005_mixed.sql",
        "INSERT INTO gold.log VALUES ($$just data$$);\n"
        "ALTER TABLE gold.dim_a ADD COLUMN b TEXT;\n",
    )

    assert "dim_a" not in migration_column_sets(tmp_path)


@pytest.mark.parametrize(
    "statement",
    [
        'DROP TABLE "gold"."dim_a";',
        'DROP TABLE IF EXISTS "gold".dim_a;',
        'DROP TABLE gold."dim_a" CASCADE;',
    ],
)
def test_quoted_relation_names_in_drop_are_recognized(
    tmp_path: Path, statement: str
) -> None:
    """#501 review: `DROP TABLE "gold"."dim_a"` is a legal, equivalent spelling. If
    the target parser missed it, the dropped relation's shape would stay indexed."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    _migration(tmp_path, "0005_drop.sql", statement)

    assert "dim_a" not in migration_column_sets(tmp_path), statement


def test_an_unreadable_migration_invalidates_the_whole_comparison(
    tmp_path: Path,
) -> None:
    """#501 review: an unreadable migration is not a neutral gap -- it may hold the
    DROP or ALTER that supersedes what an earlier file created. Keeping the earlier
    shape would let the advisory speak from an already-stale view, so the comparison
    goes quiet entirely rather than risk being confidently wrong."""
    _migration(tmp_path, "0004_gold.sql", "CREATE TABLE gold.dim_a (\n  a INT\n);")
    # Invalid UTF-8: `_read_text` cannot decode it.
    (tmp_path / "warehouse" / "migrations" / "0005_broken.sql").write_bytes(
        b"DROP TABLE gold.dim_a; \xff\xfe\x00binary"
    )

    assert migration_column_sets(tmp_path) == {}
    assert column_shape_advisories(tmp_path, [_contract("dim_a", "zzz")]) == ()


def test_committed_migration_add_constraint_clauses_are_not_treated_as_alters() -> None:
    """The shipped `0004_..._star.sql` ends with five `ADD CONSTRAINT` statements on
    `fct_sales_rss`. If the ALTER guard over-matched them, the fact would silently
    drop out of the comparison and the census would pass for the wrong reason."""
    root = repo_root()
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
