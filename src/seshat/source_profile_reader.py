"""Parse a template-conformant committed source-profile.md into a ProfileResult.

The baseline a drift run compares against is the committed source-profile.md that
earned Source Ready pass. This reader parses the template's structured sections
(Header 'Table id', Shape 'Row count', the 'Per-column profile' pipe table with
its measured missingness / distinct cardinality, and the 'Candidate grain &
candidate PK' uniqueness proof) back into a seshat.profile.ProfileResult.

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
    # The candidate PK column set the baseline STATES ("**Candidate PK:**
    # `( transaction_id )`"). The live re-profile MUST run against this exact
    # set -- profiling observed on a guessed column compares baseline.pk and
    # observed.pk on DIFFERENT columns, an invalid comparison that fabricates a
    # false blocked grain_pk_drift. None when the baseline states no PK line.
    pk_columns: tuple[str, ...] | None = None
    # The schema-qualified LANDED table ("Landed location: `bronze.<table>`") the
    # live re-profile must CONNECT to. Distinct from profile.table (the display
    # "Table id", which the emitted findings doc reports): a bare display id makes
    # profile() default to schema `public` and mistarget. None when unstated.
    landed_table: str | None = None


def _find_table_id(text: str) -> str | None:
    m = re.search(r"\|\s*Table id\s*\|\s*`?([^`|]+?)`?\s*\|", text)
    return m.group(1).strip() if m else None


def _find_landed_table(text: str) -> str | None:
    """Parse the schema-qualified landed object from the "Landed location" row,
    e.g. ``| Landed location | `bronze.retail_store_sales` (...) |`` -> the
    ``schema.table`` before any trailing parenthetical. Skips the unfilled
    template placeholder ``<bronze.schema.table>`` and returns None when the row
    is absent, so a live re-profile never runs against a guessed/`public` target."""
    m = re.search(r"\|\s*Landed location\s*\|\s*`([^`|]+?)`", text)
    if not m:
        return None
    name = m.group(1).strip()
    # angle-bracket = an unfilled template placeholder, not a real table
    if name.startswith("<") or "." not in name:
        return None
    return name


def _find_pk_columns(text: str) -> tuple[str, ...] | None:
    """Parse the stated candidate PK, e.g. ``**Candidate PK:** `( transaction_id )```
    or a composite ``( col_a, col_b )``. Returns the column tuple, or None when
    no such line is present (a non-conformant baseline)."""
    m = re.search(r"\*\*Candidate PK:\*\*\s*`\(([^`)]+)\)`", text)
    if not m:
        return None
    cols = tuple(c.strip() for c in m.group(1).split(",") if c.strip())
    return cols or None


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
        landed_type = m.group(2).strip() or None  # "Type as landed" cell
        cols.append(
            ColumnProfile(
                name=m.group(1).strip(),
                missing_count=int(m.group(3).replace(",", "")),
                missing_pct=float(m.group(4)),
                distinct_cardinality=int(m.group(5).replace(",", "")),
                landed_type=landed_type,
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


def _missing_template_sections(
    table: str | None, row_count: int | None, columns: list[ColumnProfile]
) -> list[str]:
    """Names of the template sections a comparable baseline needs but lacks."""
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
    return missing


def read_source_profile(path: str | Path) -> ParsedBaseline:
    text = Path(path).read_text(encoding="utf-8")
    table = _find_table_id(text)
    row_count = _find_row_count(text)
    columns = _parse_columns(text)

    missing = _missing_template_sections(table, row_count, columns)
    if missing:
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
        pk_columns=_find_pk_columns(text),
        landed_table=_find_landed_table(text),
    )
