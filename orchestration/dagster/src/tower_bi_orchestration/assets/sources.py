"""Concrete Bronze source adapters (issues #404 / #405).

Two adapters satisfy the pluggable :class:`SourceAdapter` contract; the mode
(:mod:`seshat.dagster_adapter.source_mode`) chooses which one drives the ingest
head. Both delegate their DB work to the lazily-imported ``db`` boundary, so
the module imports without a driver.

* :class:`CsvLandingAdapter` -- the DEFAULT. A raw ``<table>.csv`` OWNS and
  (re)creates ``bronze.<table>`` (``db.load_csv``: drop-and-reload). This is
  the one destructive-by-design mode; it is UNCHANGED from the pre-feature
  path (same measured ``{"rows_loaded": ...}``).

* :class:`ExistingBronzeAdapter` -- NON-DESTRUCTIVE DB-first. A pre-loaded
  ``bronze.<table>`` is verified READ-ONLY (``db.inspect_bronze``: only
  ``information_schema`` + ``SELECT count(*)``). It issues ZERO Bronze DDL/DML,
  returns ``mutated_bronze=False``, and halts fail-closed with a named blocker
  when the relation is absent, empty, or missing a column the approved
  source-map references.

An adapter that cannot proceed HALTS through the caller-supplied ``halt``
seam (records a blocking outcome, raises ``dagster.Failure``) -- it never
returns a fabricated success. Every DSN-touching path honors the deferred
boundary exactly as the pre-feature ``bronze_table`` did.
"""

from __future__ import annotations

import os
from pathlib import Path

from seshat.dagster_adapter.source_adapter import SourcePrepared
from seshat.dagster_adapter.source_contract import referenced_source_columns
from seshat.dagster_adapter.source_mode import (
    CSV,
    EXISTING_BRONZE,
    normalize_source_mode,
)

from .. import db


def resolve_source_mode() -> str:
    """The active source mode for this run, from the closed discovery seam.

    Reads ``SESHAT_DAGSTER_SOURCE_MODE`` (set by the runner only when
    non-default) and normalizes it fail-closed. An unset / empty value resolves
    to the default CSV path, so an existing run is byte-identical.
    """
    from seshat.dagster_adapter.source_mode import SOURCE_MODE_ENV

    return normalize_source_mode(os.environ.get(SOURCE_MODE_ENV))


class CsvLandingAdapter:
    """CSV landing file OWNS ``bronze.<table>`` (drop-and-reload). Unchanged."""

    source_mode = CSV

    def __init__(self, root: Path, landing_path: Path, halt_blocked) -> None:
        self._root = Path(root)
        self._landing_path = Path(landing_path)
        # A callable the asset supplies to record + raise a `blocked` halt with
        # the DSN deferred boundary; keeps this adapter dagster-free.
        self._halt_blocked = halt_blocked

    def prepare_bronze(self, table: str) -> SourcePrepared:
        dsn = db.resolve_dsn()
        if dsn is None:
            self._halt_blocked(db.DEFERRED_BOUNDARY)
        rows = db.load_csv(dsn, table, self._landing_path)
        # Byte-identity: the CSV path's measured dict is EXACTLY the pre-feature
        # `{"rows_loaded": rows}` -- no source_mode key is added here (#404/#405).
        return SourcePrepared(
            source_mode=CSV,
            outcome="materialized",
            measured={"rows_loaded": rows},
            mutated_bronze=True,
        )


class ExistingBronzeAdapter:
    """A pre-loaded ``bronze.<table>`` verified READ-ONLY (non-destructive)."""

    source_mode = EXISTING_BRONZE

    def __init__(self, root: Path, halt_blocked, halt_failed) -> None:
        self._root = Path(root)
        # `blocked` = a deferred/environment boundary (no creds); `failed` =
        # the existing relation violates the approved contract. Both named.
        self._halt_blocked = halt_blocked
        self._halt_failed = halt_failed

    def prepare_bronze(self, table: str) -> SourcePrepared:
        dsn = db.resolve_dsn()
        if dsn is None:
            self._halt_blocked(db.DEFERRED_BOUNDARY)
        relation = db.inspect_bronze(dsn, table)
        if not relation.exists:
            self._halt_failed(
                f"existing-bronze mode: bronze.{table} not found "
                "(no relation to start from -- load Bronze first, or use "
                "--source-mode csv)"
            )
        if relation.rows == 0:
            self._halt_failed(
                f"existing-bronze mode: bronze.{table} exists but is EMPTY "
                "(0 rows) -- refusing to start a governed run on empty Bronze; "
                "re-load Bronze, or use --source-mode csv"
            )
        required = referenced_source_columns(self._root, table)
        missing = sorted(required - set(relation.columns))
        if missing:
            self._halt_failed(
                f"existing-bronze mode: bronze.{table} does not match the "
                "approved source-map -- missing source column(s): "
                f"{', '.join(missing)}; re-load Bronze with these columns, or "
                "correct mappings/<table>/source-map.yaml"
            )
        # READ-ONLY: nothing was dropped, created, truncated, or loaded.
        mutated = False  # the single source of truth for the non-destruction
        return SourcePrepared(
            source_mode=EXISTING_BRONZE,
            outcome="materialized",
            measured={
                "source_mode": EXISTING_BRONZE,
                "rows_present": relation.rows,
                "columns_present": len(relation.columns),
                # Same value the SourcePrepared contract carries -- the evidence
                # flag is derived, never a decorative duplicate literal.
                "bronze_mutated": mutated,
            },
            mutated_bronze=mutated,
        )
