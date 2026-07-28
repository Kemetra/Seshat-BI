"""Deterministic, fail-closed local CSV provider."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from ..contracts import Blocker
from .base import (
    DataRequest,
    ProviderProvenance,
    ProviderUnavailable,
    RectangularData,
    ResourceLimits,
)

_NON_FINITE = {
    "nan",
    "+nan",
    "-nan",
    "inf",
    "+inf",
    "-inf",
    "infinity",
    "+infinity",
    "-infinity",
}


def _unavailable(code: str, message: str, recovery: str) -> ProviderUnavailable:
    return ProviderUnavailable(Blocker(code, message, recovery))


class LocalCsvProvider:
    """Read one local CSV without sampling, transformation, or path disclosure."""

    def __init__(self, path: Path, limits: ResourceLimits | None = None) -> None:
        self._path = Path(path)
        self._limits = limits or ResourceLimits()

    def _check_size(self) -> None:
        try:
            size = self._path.stat().st_size
        except OSError as exc:
            raise _unavailable(
                "STAT_PROVIDER_UNAVAILABLE",
                "The local CSV input is unavailable.",
                "Provide a readable local CSV file.",
            ) from exc
        if size > self._limits.max_bytes:
            raise _unavailable(
                "STAT_PROVIDER_RESOURCE_LIMIT",
                (
                    f"Local CSV byte ceiling exceeded: {size} > "
                    f"{self._limits.max_bytes}."
                ),
                "Use an approved extract within the configured byte ceiling.",
            )

    @staticmethod
    def _validate_header(header: list[str] | None) -> tuple[str, ...]:
        if (
            not header
            or any(not item.strip() or item != item.strip() for item in header)
            or len(set(header)) != len(header)
        ):
            raise _unavailable(
                "STAT_PROVIDER_INVALID_DATA",
                "Local CSV header is blank, duplicated, or not normalized.",
                "Use unique, non-blank headers without surrounding whitespace.",
            )
        return tuple(header)

    @staticmethod
    def _selected_indices(
        header: tuple[str, ...], request: DataRequest
    ) -> tuple[int, ...]:
        missing = tuple(column for column in request.columns if column not in header)
        if missing:
            raise _unavailable(
                "STAT_PROVIDER_COLUMN_MISSING",
                "Local CSV is missing requested columns: " + ", ".join(missing) + ".",
                "Provide all policy-approved role columns in the extract.",
            )
        return tuple(header.index(column) for column in request.columns)

    @staticmethod
    def _validate_request(request: DataRequest) -> None:
        if request.filters or request.aggregates or request.group_by or request.joins:
            raise _unavailable(
                "STAT_PROVIDER_REQUEST_REFUSED",
                "The local CSV provider cannot silently apply query transformations.",
                "Provide a governed pre-shaped extract or use the Gold provider.",
            )

    @staticmethod
    def _validate_finite(
        row: tuple[str, ...],
        logical_types: tuple[str, ...],
        row_number: int,
    ) -> None:
        for value, logical_type in zip(row, logical_types, strict=True):
            if (
                logical_type in {"number", "integer"}
                and value.strip().casefold() in _NON_FINITE
            ):
                raise _unavailable(
                    "STAT_PROVIDER_INVALID_DATA",
                    f"Local CSV contains a non-finite token at row {row_number}.",
                    "Replace NaN or infinity tokens with an approved missing value.",
                )

    def fetch(self, request: DataRequest) -> RectangularData:
        """Return exactly the selected columns, or refuse the whole acquisition."""

        self._validate_request(request)
        self._check_size()
        selected_rows: list[tuple[str, ...]] = []
        try:
            with self._path.open(
                "r", encoding="utf-8-sig", errors="strict", newline=""
            ) as stream:
                reader = csv.reader(stream)
                header = self._validate_header(next(reader, None))
                indices = self._selected_indices(header, request)
                for row_number, row in enumerate(reader, start=2):
                    if len(row) != len(header):
                        raise _unavailable(
                            "STAT_PROVIDER_INVALID_DATA",
                            f"Local CSV has a ragged row at row {row_number}.",
                            "Make every row match the validated header width.",
                        )
                    if len(selected_rows) >= self._limits.max_rows:
                        raise _unavailable(
                            "STAT_PROVIDER_RESOURCE_LIMIT",
                            (
                                "Local CSV row ceiling exceeded: more than "
                                f"{self._limits.max_rows} rows."
                            ),
                            "Use an approved extract within the row ceiling.",
                        )
                    selected = tuple(row[index] for index in indices)
                    self._validate_finite(selected, request.logical_types, row_number)
                    selected_rows.append(selected)
        except UnicodeDecodeError as exc:
            raise _unavailable(
                "STAT_PROVIDER_INVALID_DATA",
                "Local CSV is not valid UTF-8.",
                "Encode the governed extract as UTF-8 or UTF-8 with BOM.",
            ) from exc
        except csv.Error as exc:
            raise _unavailable(
                "STAT_PROVIDER_INVALID_DATA",
                "Local CSV parsing failed.",
                "Repair CSV quoting and delimiter structure.",
            ) from exc
        except OSError as exc:
            raise _unavailable(
                "STAT_PROVIDER_UNAVAILABLE",
                "The local CSV input could not be read.",
                "Provide a readable local CSV file.",
            ) from exc
        self._check_size()

        normalized = json.dumps(
            [request.columns, selected_rows],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = hashlib.sha256(normalized).hexdigest()
        provenance = ProviderProvenance(
            kind="local_csv",
            safe_label=f"local_csv:{digest[:12]}",
            data_digest=digest,
            query_digest=None,
            snapshot_id=None,
        )
        return RectangularData(
            columns=request.columns,
            rows=tuple(selected_rows),
            total_count=len(selected_rows),
            excluded_count=0,
            exclusion_reasons=(),
            provenance=provenance,
        )
