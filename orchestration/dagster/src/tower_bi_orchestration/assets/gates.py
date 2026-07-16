"""Gate assets: source_map [HUMAN SEAM] -> silver_tables -> gold_tables -> live_validate.

The human seam READS the committed approval as its only GO signal and halts if
absent (Principle IV/V); the mechanical STOP nodes run the SAME commands CI
runs and gate on a literal exit 0. Nothing here writes a ``Gate status``, a
readiness ``status``, or an ``approvals[]`` entry -- ever.
"""

from __future__ import annotations

from pathlib import Path

from dagster import AssetKey, asset

from seshat.dagster_adapter.gate import read_gate_state

from .. import commands, db
from . import halt, writer_for


def _migrations(root: Path, layer: str, table: str) -> list[Path]:
    migrations_dir = root / "warehouse" / "migrations"
    if not migrations_dir.is_dir():
        return []
    return sorted(migrations_dir.glob(f"*{layer}*{table}*.sql"))


def _build_layer(context, *, table: str, root: Path, layer: str, asset_name: str) -> None:
    """Shared silver/gold body: apply the committed migrations, then run the
    static gate; exit 0 is the ONLY green (Principle I)."""
    writer = writer_for(context, root)
    gate_command = " ".join(commands.checker_argv()[-3:])
    dsn = db.resolve_dsn()
    if dsn is None:
        halt(
            writer,
            asset=asset_name,
            table=table,
            gate_command=gate_command,
            exit_code=None,
            measured={},
            outcome="blocked",
            reason=db.DEFERRED_BOUNDARY,
            owner="platform owner",
        )
    migrations = _migrations(root, layer, table)
    if not migrations:
        halt(
            writer,
            asset=asset_name,
            table=table,
            gate_command=gate_command,
            exit_code=None,
            measured={},
            outcome="blocked",
            reason=f"no committed {layer} migration found for {table} under warehouse/migrations/",
            owner="warehouse owner",
        )
    for migration in migrations:
        db.apply_sql_file(dsn, migration)
    exit_code, output = commands.run_gate_command(commands.checker_argv(), cwd=root)
    if exit_code != 0:
        halt(
            writer,
            asset=asset_name,
            table=table,
            gate_command=gate_command,
            exit_code=exit_code,
            measured={"output_tail": output},
            outcome="failed",
            reason=f"static governance gate failed: seshat check exit {exit_code}",
            owner="warehouse owner",
        )
    writer.record(
        asset=asset_name,
        table=table,
        gate_command=gate_command,
        exit_code=0,
        measured={"migrations_applied": [m.name for m in migrations]},
        outcome="materialized",
    )


def build_gate_assets(table: str, root: Path) -> list:
    prefix = [table]

    @asset(
        name="source_map",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "source_profile"])],
    )
    def source_map(context) -> None:
        """HUMAN SEAM (Principle IV): reads Gate status; HALTS if not CLEARED."""
        writer = writer_for(context, root)
        state = read_gate_state(root, table)
        gate_command = f"reads Gate status from mappings/{table}/unresolved-questions.md"
        if not state.silver_permitted:
            halt(
                writer,
                asset="source_map",
                table=table,
                gate_command=gate_command,
                exit_code=None,
                measured={"gate_status": state.gate_status, "open_rows": state.open_rows},
                outcome="blocked",
                reason=(
                    f"source_map gate not CLEARED: Gate status {state.gate_status}, "
                    f"open rows {state.open_rows} "
                    f"(read from mappings/{table}/unresolved-questions.md)"
                ),
                owner="the mapping reviewer",
            )
        writer.record(
            asset="source_map",
            table=table,
            gate_command=gate_command,
            exit_code=None,
            measured={"gate_status": state.gate_status, "open_rows": state.open_rows},
            outcome="materialized",
        )

    @asset(
        name="silver_tables",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "source_map"])],
    )
    def silver_tables(context) -> None:
        _build_layer(context, table=table, root=root, layer="silver", asset_name="silver_tables")

    @asset(
        name="gold_tables",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "silver_tables"])],
    )
    def gold_tables(context) -> None:
        _build_layer(context, table=table, root=root, layer="gold", asset_name="gold_tables")

    @asset(
        name="live_validate",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "gold_tables"])],
    )
    def live_validate(context) -> None:
        """The live acceptance step: records ``deferred`` without creds (never a
        fabricated pass; Principle VIII); a real non-zero exit FAILS CLOSED."""
        writer = writer_for(context, root)
        argv = commands.validate_argv(table)
        gate_command = " ".join(argv[-4:])
        if db.resolve_dsn() is None:
            writer.record(
                asset="live_validate",
                table=table,
                gate_command=gate_command,
                exit_code=None,
                measured={},
                outcome="deferred",
                blocking_reason=db.DEFERRED_BOUNDARY,
                owner="platform owner",
            )
            return
        exit_code, output = commands.run_gate_command(argv, cwd=root)
        if exit_code != 0:
            halt(
                writer,
                asset="live_validate",
                table=table,
                gate_command=gate_command,
                exit_code=exit_code,
                measured={"output_tail": output},
                outcome="failed",
                reason=f"live validation failed: seshat validate exit {exit_code}",
                owner="warehouse owner",
            )
        writer.record(
            asset="live_validate",
            table=table,
            gate_command=gate_command,
            exit_code=0,
            measured={"validate": "exit 0"},
            outcome="materialized",
        )

    return [source_map, silver_tables, gold_tables, live_validate]
