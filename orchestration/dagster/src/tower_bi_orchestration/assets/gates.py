"""Gate assets: source_map [HUMAN SEAM] -> silver -> gold -> live_validate.

The human seam READS the committed approval as its only GO signal and halts if
absent (Principle IV/V); the mechanical STOP nodes run the SAME commands CI
runs and gate on a literal exit 0. Nothing here writes a ``Gate status``, a
readiness ``status``, or an ``approvals[]`` entry -- ever.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dagster import AssetKey, asset

from seshat.dagster_adapter.engine import resolve_build_engine
from seshat.dagster_adapter.gate import read_gate_state

from .. import commands, db, dbt_build
from ..evidence_writer import AssetOutcome
from . import halt, writer_for


def _migrations(root: Path, layer: str, table: str) -> list[Path]:
    migrations_dir = root / "warehouse" / "migrations"
    if not migrations_dir.is_dir():
        return []
    return sorted(migrations_dir.glob(f"*{layer}*{table}*.sql"))


@dataclass(frozen=True)
class _Produce:
    """One layer-build request: the writer/base evidence plumbing plus the
    (root, layer, table) coordinates every engine needs."""

    writer: object
    base: dict
    root: Path
    layer: str
    table: str


def _halt_deferred(produce: _Produce, blocking_reason: str) -> None:
    """Halt fail-closed on an absent credential contract, before anything runs.

    Each engine defers on ITS OWN contract (Codex review on PR #307):
    migrations on the ANALYTICS_DB_*/DATABASE_URL DSN, the governed dbt build
    on the SESHAT_DBT_* live profile. Neither gate weakens.
    """
    halt(
        produce.writer,
        AssetOutcome(
            **produce.base,
            exit_code=None,
            measured={},
            outcome="blocked",
            blocking_reason=blocking_reason,
            owner="platform owner",
        ),
    )


def _produce_migrations(produce: _Produce) -> dict:
    """Apply the committed migration SQL; return the measured produce fields.

    Unchanged from the pre-feature migrations path (US5): flipping back to
    ``engine: migrations`` reproduces this behavior byte-for-byte, including
    the DSN deferred boundary.
    """
    dsn = db.resolve_dsn()
    if dsn is None:
        _halt_deferred(produce, db.DEFERRED_BOUNDARY)
    migrations = _migrations(produce.root, produce.layer, produce.table)
    if not migrations:
        halt(
            produce.writer,
            AssetOutcome(
                **produce.base,
                exit_code=None,
                measured={"engine": "migrations"},
                outcome="blocked",
                blocking_reason=(
                    f"no committed {produce.layer} migration found for "
                    f"{produce.table} under warehouse/migrations/"
                ),
                owner="warehouse owner",
            ),
        )
    for migration in migrations:
        db.apply_sql_file(dsn, migration)
    return {
        "engine": "migrations",
        "migrations_applied": [m.name for m in migrations],
    }


def _produce_dbt(produce: _Produce) -> dict:
    """Run the governed table-wide dbt build (shadow-only rehearsal).

    The dbt engine does NOT rebuild the real ``silver``/``gold`` relations
    (spec 133 FR-005) -- it is a governed rehearsal into shadow schemas, so the
    measured record states ``warehouse_updated: false`` (FR-015). The
    accept-plan digest is self-accepted-by-recompute on this unattended path
    (FR-014); that is recorded too. A governed refusal / absent runtime HALTS
    fail-closed with the bridge's redacted reason (FR-006) -- never a traceback.
    """
    if not dbt_build.profile_present(produce.root):
        _halt_deferred(produce, dbt_build.DBT_DEFERRED_BOUNDARY)
    exit_code, measured, evidence_path = dbt_build.build_layer(
        context=None, table=produce.table, layer=produce.layer, root=produce.root
    )
    measured = {
        **measured,
        "engine": "dbt",
        "warehouse_updated": False,
        "self_accepted_by_recompute": True,
    }
    if exit_code != 0:
        halt(
            produce.writer,
            AssetOutcome(
                **produce.base,
                exit_code=exit_code,
                measured=measured,
                outcome=measured.get("outcome", "blocked"),
                blocking_reason=measured.get(
                    "blocking_reason", "governed dbt build did not complete"
                ),
                owner=measured.get("owner", "the dbt runtime owner"),
            ),
        )
    return measured


def _build_layer(context, table: str, root: Path, layer: str) -> None:
    """Shared silver/gold body: PRODUCE via the resolved engine, then run the
    SAME static gate; exit 0 is the ONLY green (Principle I).

    The GATE (``seshat check``), the DSN/deferred preamble, and the STOP-edge
    topology are engine-independent and unchanged; only the produce step
    branches on ``resolve_build_engine`` (default ``migrations``, fail-closed).
    """
    asset_name = f"{layer}_tables"
    writer = writer_for(context, root)
    gate_command = " ".join(commands.checker_argv()[-3:])
    base = dict(asset=asset_name, table=table, gate_command=gate_command)
    engine = resolve_build_engine(root, table, layer)
    produce = _Produce(writer=writer, base=base, root=root, layer=layer, table=table)
    if engine == "dbt":
        produced = _produce_dbt(produce)
    else:
        produced = _produce_migrations(produce)
    exit_code, output = commands.run_gate_command(commands.checker_argv(), cwd=root)
    if exit_code != 0:
        halt(
            writer,
            AssetOutcome(
                **base,
                exit_code=exit_code,
                measured={**produced, "output_tail": output},
                outcome="failed",
                blocking_reason=(
                    f"static governance gate failed: seshat check exit {exit_code}"
                ),
                owner="warehouse owner",
            ),
        )
    writer.record(
        AssetOutcome(
            **base,
            exit_code=0,
            measured=produced,
            outcome="materialized",
        )
    )


def _source_map_asset(table: str, root: Path):
    @asset(
        name="source_map",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, "source_profile"])],
    )
    def source_map(context) -> None:
        """HUMAN SEAM (Principle IV): reads Gate status; HALTS if not CLEARED."""
        writer = writer_for(context, root)
        state = read_gate_state(root, table)
        base = dict(
            asset="source_map",
            table=table,
            gate_command=(
                f"reads Gate status from mappings/{table}/unresolved-questions.md"
            ),
            exit_code=None,
            measured={"gate_status": state.gate_status, "open_rows": state.open_rows},
        )
        if not state.silver_permitted:
            halt(
                writer,
                AssetOutcome(
                    **base,
                    outcome="blocked",
                    blocking_reason=(
                        f"source_map gate not CLEARED: Gate status "
                        f"{state.gate_status}, open rows {state.open_rows} "
                        f"(read from mappings/{table}/unresolved-questions.md)"
                    ),
                    owner="the mapping reviewer",
                ),
            )
        writer.record(AssetOutcome(**base, outcome="materialized"))

    return source_map


_LAYER_UPSTREAM = {"silver": "source_map", "gold": "silver_tables"}


def _layer_asset(table: str, root: Path, layer: str):
    @asset(
        name=f"{layer}_tables",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, _LAYER_UPSTREAM[layer]])],
    )
    def layer_tables(context) -> None:
        _build_layer(context, table, root, layer)

    return layer_tables


def _live_validate_asset(table: str, root: Path):
    @asset(
        name="live_validate",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, "gold_tables"])],
    )
    def live_validate(context) -> None:
        """The live acceptance step: records ``deferred`` without creds (never a
        fabricated pass; Principle VIII); a real non-zero exit FAILS CLOSED."""
        writer = writer_for(context, root)
        argv = commands.validate_argv(table)
        base = dict(
            asset="live_validate", table=table, gate_command=" ".join(argv[-4:])
        )
        if db.resolve_dsn() is None:
            writer.record(
                AssetOutcome(
                    **base,
                    exit_code=None,
                    measured={},
                    outcome="deferred",
                    blocking_reason=db.DEFERRED_BOUNDARY,
                    owner="platform owner",
                )
            )
            return
        exit_code, output = commands.run_gate_command(argv, cwd=root)
        if exit_code != 0:
            halt(
                writer,
                AssetOutcome(
                    **base,
                    exit_code=exit_code,
                    measured={"output_tail": output},
                    outcome="failed",
                    blocking_reason=(
                        f"live validation failed: seshat validate exit {exit_code}"
                    ),
                    owner="warehouse owner",
                ),
            )
        writer.record(
            AssetOutcome(
                **base,
                exit_code=0,
                measured={"validate": "exit 0"},
                outcome="materialized",
            )
        )

    return live_validate


def build_gate_assets(table: str, root: Path) -> list:
    return [
        _source_map_asset(table, root),
        _layer_asset(table, root, "silver"),
        _layer_asset(table, root, "gold"),
        _live_validate_asset(table, root),
    ]
