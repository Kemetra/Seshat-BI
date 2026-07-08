"""Parse a template-conformant committed source-profile.md into a ProfileResult.

The baseline a drift run compares against is the committed source-profile.md that
earned Source Ready pass. This reader parses the template's structured sections
(Header 'Table id', Shape 'Row count', the 'Per-column profile' pipe table with
its measured missingness / distinct cardinality, and the 'Candidate grain &
candidate PK' uniqueness proof) back into a retail.profile.ProfileResult.

HONESTY BOUNDARY: the two filled baselines in the tree have DIFFERENT structures
(retail_store_sales follows the template; demo_sample_orders uses a freeform
3-column layout with no measured missingness/cardinality). A non-conformant
profile is reported as uncomparable -- NEVER guessed at -- matching the taxonomy's
'profile schema-version skew' edge case (compare only what both carry).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .profile import ColumnProfile, PkProof, ProfileResult


@dataclass(frozen=True)
class ParsedBaseline:
    profile: ProfileResult | None
    uncomparable: str | None  # a human reason when profile is None


def _find_table_id(text: str) -> str | None:
    m = re.search(r"\|\s*Table id\s*\|\s*`?([^`|]+?)`?\s*\|", text)
    return m.group(1).strip() if m else None


def _find_row_count(text: str) -> int | None:
    m = re.search(r"\|\s*Row count[^|]*\|\s*([\d,]+)\s*\|", text)
    return int(m.group(1).replace(",", "")) if m else None


# A per-column row: | `name` | TYPE | 1,213 / 9.65% | 201 | ... | ... |
_COL_ROW = re.compile(
    r"\|\s*`([^`]+)`\s*\|"  # column name
    r"\s*([^|]*?)\s*\|"  # type as landed
    r"\s*([\d,]+)\s*/\s*([\d.]+)%\s*\|"  # missing count / pct
    r"\s*([\d,]+)\s*\|"  # distinct cardinality
)


def _parse_columns(text: str) -> list[ColumnProfile]:
    cols: list[ColumnProfile] = []
    for m in _COL_ROW.finditer(text):
        cols.append(
            ColumnProfile(
                name=m.group(1).strip(),
                missing_count=int(m.group(3).replace(",", "")),
                missing_pct=float(m.group(4)),
                distinct_cardinality=int(m.group(5).replace(",", "")),
            )
        )
    return cols


def _parse_pk(text: str, row_count: int) -> PkProof:
    def _num(pattern: str) -> int | None:
        m = re.search(pattern, text)
        return int(m.group(1).replace(",", "")) if m else None

    total = _num(r"COUNT\(\*\)\s*=\s*([\d,]+)") or row_count
    distinct = _num(r"COUNT\(DISTINCT pk\)\s*=\s*([\d,]+)")
    null_pk = _num(r"NULLs/empty in PK\s*=\s*([\d,]+)")
    null_pk = 0 if null_pk is None else null_pk
    is_unique = distinct is not None and distinct == total and null_pk == 0
    return PkProof(
        total=total,
        distinct_pk=distinct if distinct is not None else total,
        null_pk=null_pk,
        is_unique=is_unique,
    )


def read_source_profile(path: str | Path) -> ParsedBaseline:
    text = Path(path).read_text(encoding="utf-8")
    table = _find_table_id(text)
    row_count = _find_row_count(text)
    columns = _parse_columns(text)

    if table is None or row_count is None or not columns:
        missing = []
        if table is None:
            missing.append("Header 'Table id'")
        if row_count is None:
            missing.append("Shape 'Row count'")
        if not columns:
            missing.append(
                "a template 'Per-column profile' table with measured "
                "missingness/cardinality"
            )
        return ParsedBaseline(
            profile=None,
            uncomparable=(
                "non-conformant source-profile.md: missing "
                + ", ".join(missing)
                + " -- cannot compare; re-profile against the template shape"
            ),
        )

    return ParsedBaseline(
        profile=ProfileResult(
            table=table,
            row_count=row_count,
            column_count=len(columns),
            columns=tuple(columns),
            pk=_parse_pk(text, row_count),
        ),
        uncomparable=None,
    )
