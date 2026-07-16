"""Ingest assets: raw_source_file -> bronze_table -> source_profile."""

from __future__ import annotations

import os
from pathlib import Path

from dagster import AssetKey, asset

from .. import db
from . import halt, writer_for


def _landing_path(root: Path, table: str) -> Path:
    landing = os.environ.get("SESHAT_RAW_LANDING_DIR")
    base = Path(landing) if landing else root / "data" / "raw"
    return base / f"{table}.csv"


def build_ingest_assets(table: str, root: Path) -> list:
    prefix = [table]

    @asset(name="raw_source_file", key_prefix=prefix, group_name=table)
    def raw_source_file(context) -> None:
        writer = writer_for(context, root)
        path = _landing_path(root, table)
        if not path.is_file():
            halt(
                writer,
                asset="raw_source_file",
                table=table,
                gate_command="n/a -- landing input",
                exit_code=None,
                measured={},
                outcome="failed",
                reason=f"raw landing file not found: {path.name} (landing dir absent or empty)",
                owner="data owner",
            )
        writer.record(
            asset="raw_source_file",
            table=table,
            gate_command="n/a -- landing input",
            exit_code=None,
            measured={"bytes": path.stat().st_size},
            outcome="materialized",
        )

    @asset(
        name="bronze_table",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "raw_source_file"])],
    )
    def bronze_table(context) -> None:
        writer = writer_for(context, root)
        dsn = db.resolve_dsn()
        if dsn is None:
            halt(
                writer,
                asset="bronze_table",
                table=table,
                gate_command="load bronze (psycopg2 COPY)",
                exit_code=None,
                measured={},
                outcome="blocked",
                reason=db.DEFERRED_BOUNDARY,
                owner="platform owner",
            )
        rows = db.load_csv(dsn, table, _landing_path(root, table))
        writer.record(
            asset="bronze_table",
            table=table,
            gate_command="load bronze (psycopg2 COPY)",
            exit_code=0,
            measured={"rows_loaded": rows},
            outcome="materialized",
        )

    @asset(
        name="source_profile",
        key_prefix=prefix,
        group_name=table,
        deps=[AssetKey([*prefix, "bronze_table"])],
    )
    def source_profile(context) -> None:
        writer = writer_for(context, root)
        profile = root / "mappings" / table / "source-profile.md"
        if not profile.is_file():
            halt(
                writer,
                asset="source_profile",
                table=table,
                gate_command="n/a -- reads the committed source profile",
                exit_code=None,
                measured={},
                outcome="blocked",
                reason=f"committed source profile absent: mappings/{table}/source-profile.md "
                "(Stage-1 onboarding not done)",
                owner="table onboarder",
            )
        writer.record(
            asset="source_profile",
            table=table,
            gate_command="n/a -- reads the committed source profile",
            exit_code=None,
            measured={"profile": f"mappings/{table}/source-profile.md"},
            outcome="materialized",
        )

    return [raw_source_file, bronze_table, source_profile]
