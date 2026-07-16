"""Ingest assets: raw_source_file -> bronze_table -> source_profile."""

from __future__ import annotations

import os
from pathlib import Path

from dagster import AssetKey, asset

from .. import db
from ..evidence_writer import AssetOutcome
from . import halt, writer_for


def _landing_path(root: Path, table: str) -> Path:
    landing = os.environ.get("SESHAT_RAW_LANDING_DIR")
    base = Path(landing) if landing else root / "data" / "raw"
    return base / f"{table}.csv"


def _raw_source_file_asset(table: str, root: Path):
    @asset(name="raw_source_file", key_prefix=[table], group_name=table)
    def raw_source_file(context) -> None:
        writer = writer_for(context, root)
        path = _landing_path(root, table)
        base = dict(
            asset="raw_source_file",
            table=table,
            gate_command="n/a -- landing input",
            exit_code=None,
        )
        if not path.is_file():
            halt(
                writer,
                AssetOutcome(
                    **base,
                    measured={},
                    outcome="failed",
                    blocking_reason=(
                        f"raw landing file not found: {path.name} "
                        "(landing dir absent or empty)"
                    ),
                    owner="data owner",
                ),
            )
        writer.record(
            AssetOutcome(
                **base, measured={"bytes": path.stat().st_size}, outcome="materialized"
            )
        )

    return raw_source_file


def _bronze_asset(table: str, root: Path):
    @asset(
        name="bronze_table",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, "raw_source_file"])],
    )
    def bronze_table(context) -> None:
        writer = writer_for(context, root)
        base = dict(
            asset="bronze_table",
            table=table,
            gate_command="load bronze (psycopg2 COPY)",
        )
        dsn = db.resolve_dsn()
        if dsn is None:
            halt(
                writer,
                AssetOutcome(
                    **base,
                    exit_code=None,
                    measured={},
                    outcome="blocked",
                    blocking_reason=db.DEFERRED_BOUNDARY,
                    owner="platform owner",
                ),
            )
        rows = db.load_csv(dsn, table, _landing_path(root, table))
        writer.record(
            AssetOutcome(
                **base,
                exit_code=0,
                measured={"rows_loaded": rows},
                outcome="materialized",
            )
        )

    return bronze_table


def _source_profile_asset(table: str, root: Path):
    @asset(
        name="source_profile",
        key_prefix=[table],
        group_name=table,
        deps=[AssetKey([table, "bronze_table"])],
    )
    def source_profile(context) -> None:
        writer = writer_for(context, root)
        profile = root / "mappings" / table / "source-profile.md"
        base = dict(
            asset="source_profile",
            table=table,
            gate_command="n/a -- reads the committed source profile",
            exit_code=None,
        )
        if not profile.is_file():
            halt(
                writer,
                AssetOutcome(
                    **base,
                    measured={},
                    outcome="blocked",
                    blocking_reason=(
                        "committed source profile absent: "
                        f"mappings/{table}/source-profile.md "
                        "(Stage-1 onboarding not done)"
                    ),
                    owner="table onboarder",
                ),
            )
        writer.record(
            AssetOutcome(
                **base,
                measured={"profile": f"mappings/{table}/source-profile.md"},
                outcome="materialized",
            )
        )

    return source_profile


def build_ingest_assets(table: str, root: Path) -> list:
    return [
        _raw_source_file_asset(table, root),
        _bronze_asset(table, root),
        _source_profile_asset(table, root),
    ]
