"""The closed job vocabulary (contracts/dagster-cli.md): full sequence, or
through-gold (ingest -> gates -> live validate, stopping before the semantic /
publish tail)."""

from __future__ import annotations

from dagster import AssetKey, AssetSelection, define_asset_job

THROUGH_GOLD_ASSETS: tuple[str, ...] = (
    "raw_source_file",
    "bronze_table",
    "source_profile",
    "source_map",
    "silver_tables",
    "gold_tables",
    "live_validate",
)


def build_jobs(tables: list[str]) -> list:
    full_sequence_job = define_asset_job(
        name="full_sequence_job",
        selection=AssetSelection.all(),
        description="All eleven medallion assets (plus live validate) for every mapped table.",
    )
    through_gold_keys = [
        AssetKey([table, name]) for table in tables for name in THROUGH_GOLD_ASSETS
    ]
    through_gold_job = define_asset_job(
        name="through_gold_job",
        selection=AssetSelection.assets(*through_gold_keys)
        if through_gold_keys
        else AssetSelection.all(),
        description="Ingest -> gates -> gold -> live validate; stops before the semantic/publish tail.",
    )
    return [full_sequence_job, through_gold_job]
