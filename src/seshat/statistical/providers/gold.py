"""Count-first, read-only Gold rectangular data provider."""

from __future__ import annotations

import hashlib
import json

from seshat.dialect import Dialect
from seshat.validate import QueryRunner

from ..contracts import Blocker
from ..query import QueryRefused, compile_count, compile_select
from .base import (
    DataRequest,
    ProviderProvenance,
    ProviderUnavailable,
    RectangularData,
    ResourceLimits,
)

_FORBIDDEN_SQL = (";", "--", "/*", "*/")


def _unavailable(code: str, message: str, recovery: str) -> ProviderUnavailable:
    return ProviderUnavailable(Blocker(code, message, recovery))


def _is_single_count(rows: list[tuple]) -> bool:
    """A count result is one row, one column, holding a non-negative integer."""

    if len(rows) != 1 or len(rows[0]) != 1:
        return False
    value = rows[0][0]
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value >= 0


class GoldProvider:
    """Execute only compiler-produced SELECT statements through a runner."""

    def __init__(
        self,
        runner: QueryRunner,
        dialect: Dialect,
        limits: ResourceLimits | None = None,
    ) -> None:
        self._runner = runner
        self._dialect = dialect
        self._limits = limits or ResourceLimits()

    def _run(self, sql: str, params: tuple[object, ...]) -> list[tuple]:
        if not sql.lstrip().upper().startswith("SELECT") or any(
            token in sql for token in _FORBIDDEN_SQL
        ):
            raise _unavailable(
                "STAT_QUERY_REFUSED",
                "Gold provider refused a non-SELECT statement.",
                "Use only the closed statistical query compiler.",
            )
        try:
            return self._runner.run(sql, params)
        except Exception as exc:
            raise _unavailable(
                "STAT_PROVIDER_UNAVAILABLE",
                "Gold data acquisition failed.",
                "Verify the read-only DB connection and retry.",
            ) from exc

    @staticmethod
    def _count(rows: list[tuple]) -> int:
        if not _is_single_count(rows):
            raise _unavailable(
                "STAT_PROVIDER_INVALID_DATA",
                "Gold count query returned an invalid result.",
                "Repair the read-only runner or Gold query boundary.",
            )
        return rows[0][0]

    def _assert_row_shape(self, rows: list[tuple], selected, total_count: int) -> None:
        """The measured count and compiled width both have to hold exactly."""

        if len(rows) != total_count:
            raise _unavailable(
                "STAT_PROVIDER_INVALID_DATA",
                (f"Gold count mismatch: expected {total_count}, received {len(rows)}."),
                "Retry against a stable read-only snapshot.",
            )
        width = len(selected.output_columns)
        if any(len(row) != width for row in rows):
            raise _unavailable(
                "STAT_PROVIDER_INVALID_DATA",
                "Gold result width does not match the compiled output contract.",
                "Repair the runner or approved query definition.",
            )

    def _assert_within_limits(self, total_count: int) -> None:
        if total_count > self._limits.max_rows:
            raise _unavailable(
                "STAT_PROVIDER_RESOURCE_LIMIT",
                (
                    f"Measured Gold count {total_count} exceeds the row ceiling "
                    f"{self._limits.max_rows}."
                ),
                "Narrow the governed request or raise an approved resource limit.",
            )

    def _assert_within_byte_ceiling(self, rows: list[tuple]) -> None:
        returned = json.dumps(
            rows, default=str, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
        if len(returned) > self._limits.max_bytes:
            raise _unavailable(
                "STAT_PROVIDER_RESOURCE_LIMIT",
                (
                    f"Gold result byte ceiling exceeded: {len(returned)} > "
                    f"{self._limits.max_bytes}."
                ),
                "Narrow the governed request or raise an approved resource limit.",
            )

    def _compiled(self, request: DataRequest):
        try:
            return (
                compile_count(request, self._dialect),
                compile_select(request, self._dialect),
            )
        except QueryRefused as exc:
            raise ProviderUnavailable(exc.blocker) from exc

    def fetch(self, request: DataRequest) -> RectangularData:
        """Count first, then fetch the whole approved result or refuse it."""

        counted, selected = self._compiled(request)
        total_count = self._count(self._run(counted.sql, counted.params))
        self._assert_within_limits(total_count)
        rows = self._run(selected.sql, selected.params)
        self._assert_row_shape(rows, selected, total_count)
        self._assert_within_byte_ceiling(rows)
        shape = json.dumps(
            [selected.digest, total_count, len(selected.output_columns)],
            separators=(",", ":"),
        ).encode("utf-8")
        provenance = ProviderProvenance(
            kind="gold",
            safe_label=f"gold:{request.table}",
            data_digest=hashlib.sha256(shape).hexdigest(),
            query_digest=selected.digest,
            snapshot_id=None,
        )
        return RectangularData(
            columns=selected.output_columns,
            rows=tuple(rows),
            total_count=total_count,
            excluded_count=0,
            exclusion_reasons=(),
            provenance=provenance,
        )
