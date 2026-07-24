"""Shared workspace builders for the ``seshat reset`` planner/executor/CLI tests.

The fixtures mirror what the real verbs materialize for an onboarded table:
``mappings/<table>/`` (with its nested ``dbt-evidence/``), the numbered
silver/gold DDL migrations under ``warehouse/migrations/``, the three nested
``dbt/models/<layer>/<table>/`` model folders, the SHARED dbt files
(``dbt/selectors.yml`` + ``dbt/models/sources/_sources.yml``) exactly as
``seshat dbt scaffold``'s writer emits them, table-scoped dagster run evidence
under ``.seshat/dagster/runs/``, and the bronze landing ``data/raw/<table>.csv``
that reset must PRESERVE.

Every file is written LF-only (``newline="\\n"``), matching the scaffold
writers, so byte-fidelity assertions hold on Windows too.
"""

from __future__ import annotations

import json
from pathlib import Path

_SELECTOR_BLOCK = (
    "- name: seshat_table_{t}\n"
    "  description: Governed shadow graph for the seshat_table_{t} approved map.\n"
    "  definition:\n"
    "    method: tag\n"
    "    value: seshat_table_{t}\n"
)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def selectors_text(*tables: str) -> str:
    """The ``dbt/selectors.yml`` text carrying one selector row per table."""
    return "selectors:\n" + "".join(_SELECTOR_BLOCK.format(t=t) for t in tables)


def sources_text(bronze_rows: tuple[str, ...], gold_rows: tuple[str, ...]) -> str:
    """The shared ``_sources.yml`` text in the scaffold writer's emitted shape."""
    lines = ["version: 2", "sources:", "- name: bronze", "  schema: bronze"]
    lines.append("  tables:")
    lines += [f"  - name: {name}" for name in bronze_rows]
    lines += ["- name: migration_gold", "  schema: gold", "  tables:"]
    lines += [f"  - name: {name}" for name in gold_rows]
    return "\n".join(lines) + "\n"


def default_marts(table: str) -> tuple[str, str]:
    return (f"fct_{table}", f"dim_{table}_date")


def onboard_table(
    root: Path,
    table: str,
    *,
    marts: tuple[str, ...] | None = None,
    migration_numbers: tuple[str, str] = ("0003", "0004"),
) -> None:
    """Materialize one table's full derived file-set plus its bronze landing."""
    marts = marts or default_marts(table)
    mapping = root / "mappings" / table
    (mapping / "dbt-evidence").mkdir(parents=True)
    _write(mapping / "source-map.yaml", f'table: "bronze.{table}"\n')
    _write(mapping / "readiness-status.yaml", f'table: "{table}"\n')
    _write(mapping / "source-profile.md", "# profile\n")
    _write(mapping / "dbt-evidence" / "run-0001.md", "# dbt evidence\n")
    migrations = root / "warehouse" / "migrations"
    migrations.mkdir(parents=True, exist_ok=True)
    silver, gold = migration_numbers
    _write(
        migrations / f"{silver}_create_silver_{table}.sql",
        "CREATE TABLE IF NOT EXISTS silver.t (id int);\n",
    )
    _write(
        migrations / f"{gold}_create_gold_{table}_star.sql",
        "CREATE TABLE IF NOT EXISTS gold.t (id int);\n",
    )
    layer_files: dict[str, tuple[str, ...]] = {
        "staging": (f"stg_{table}.sql", "_models.yml"),
        "marts": tuple(f"{name}.sql" for name in marts) + ("_models.yml",),
        "audit": (f"audit_{table}_parity.sql", "_models.yml"),
    }
    for layer, files in layer_files.items():
        directory = root / "dbt" / "models" / layer / table
        directory.mkdir(parents=True)
        for filename in files:
            _write(directory / filename, "select 1\n")
    raw = root / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    _write(raw / f"{table}.csv", "id,amount\n1,10\n")


def write_shared_dbt_files(
    root: Path, marts_by_table: dict[str, tuple[str, ...]]
) -> None:
    dbt = root / "dbt"
    dbt.mkdir(exist_ok=True)
    _write(dbt / "selectors.yml", selectors_text(*marts_by_table))
    sources_dir = dbt / "models" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    gold_rows = tuple(name for marts in marts_by_table.values() for name in marts)
    _write(
        sources_dir / "_sources.yml",
        sources_text(tuple(marts_by_table), gold_rows),
    )


def add_dagster_run(root: Path, run_id: str, tables: tuple[str, ...]) -> None:
    run_dir = root / ".seshat" / "dagster" / "runs" / run_id
    run_dir.mkdir(parents=True)
    _write(
        run_dir / "summary.json",
        json.dumps({"run_id": run_id, "tables": list(tables)}),
    )
    _write(run_dir / "records.jsonl", "{}\n")


def build_workspace(root: Path, tables: tuple[str, ...] = ("orders",)) -> None:
    """One call: onboard every table and write the shared dbt files."""
    marts_by_table = {table: default_marts(table) for table in tables}
    for index, table in enumerate(tables):
        base = 3 + 2 * index
        onboard_table(
            root,
            table,
            marts=marts_by_table[table],
            migration_numbers=(f"{base:04d}", f"{base + 1:04d}"),
        )
    write_shared_dbt_files(root, marts_by_table)
