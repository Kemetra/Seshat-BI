"""DAX Generator (Phase 1): contract `definition` -> verified DAX measure.

The INVERSE of metric_drift.check_measure_drift: that answers "does this DAX
match this contract?"; this answers "what DAX matches this contract?", then
feeds its own output back through the checker. Fail-closed: `pass` is the only
acceptable round-trip; anything else is a refusal (no DAX/TMDL emitted).

Stdlib-only at import time (mirrors metric_drift.py). `yaml` is imported lazily
ONLY in load_contract(); this module is never in the `retail check` core chain.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GenResult", "generate_measure", "load_contract"]


@dataclass(frozen=True)
class GenResult:
    """A sum type: EITHER (ok=True, dax, tmdl_block) OR (ok=False, reason).

    On refusal, dax and tmdl_block are None -- a caller cannot fish an
    unverified partial out of a refusal.
    """

    ok: bool
    dax: str | None = None
    tmdl_block: str | None = None
    reason: str | None = None
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.ok:
            if self.dax is None or self.tmdl_block is None:
                raise ValueError("ok GenResult must populate dax and tmdl_block")
            if self.reason is not None:
                raise ValueError("ok GenResult must not carry a reason")
        else:
            if self.dax is not None or self.tmdl_block is not None:
                raise ValueError("refusal GenResult must not carry dax/tmdl_block")
            if not self.reason:
                raise ValueError("refusal GenResult must carry a reason")

    @classmethod
    def success(
        cls, dax: str, tmdl_block: str, warnings: tuple[str, ...] = ()
    ) -> "GenResult":
        return cls(ok=True, dax=dax, tmdl_block=tmdl_block, warnings=warnings)

    @classmethod
    def refuse(cls, reason: str) -> "GenResult":
        return cls(ok=False, reason=reason)


_AGG_TO_DAX: dict[str, str] = {
    "sum": "SUM",
    "count": "COUNT",
    "distinct_count": "DISTINCTCOUNT",
    "average": "AVERAGE",
    "count_rows": "COUNTROWS",
}
_NEEDS_COLUMN = {"sum", "count", "distinct_count", "average"}
# canonical predicate spellings -- MUST match the spellings metric_drift recognizes
_OP_TO_DAX = {
    "is_true": "{col} = TRUE()",
    "is_not_null": "NOT(ISBLANK({col}))",
}


def _qualify(table: str, column: str | None) -> str:
    """`gold.fct_sales_rss`,`col` -> `'gold fct_sales_rss'[col]`; table-only if no col.

    The committed TMDL uses a space-joined single-quoted table name
    (`'gold fct_sales_rss'`), matching what metric_drift parses. A dotted
    `schema.table` is rendered with the dot replaced by a space.
    """
    tbl = "'" + table.replace(".", " ") + "'"
    return f"{tbl}[{column}]" if column else tbl


def _emit_base(defn: dict) -> tuple[str | None, str | None]:
    agg = defn.get("aggregation")
    if agg not in _AGG_TO_DAX:
        return None, f"unsupported aggregation {agg!r}"
    source = defn.get("source") or {}
    table = source.get("table")
    column = source.get("column")
    if not isinstance(table, str) or not table.startswith("gold."):
        return None, f"source.table must be a gold.* table, got {table!r}"
    if agg == "count_rows":
        if column:
            return None, "count_rows must not specify source.column (table only)"
    elif not column:
        return None, f"aggregation {agg!r} requires source.column"

    func = _AGG_TO_DAX[agg]
    inner = f"{func}({_qualify(table, column)})"

    filters = defn.get("filter") or []
    if not filters:
        return inner, None

    preds: list[str] = []
    tbl = "'" + table.replace(".", " ") + "'"
    for f in filters:
        col = f.get("column")
        op = f.get("op")
        tmpl = _OP_TO_DAX.get(op) if op else None
        if not col or tmpl is None:
            return None, f"unrecognized filter op {op!r} on column {col!r}"
        preds.append(tmpl.format(col=f"{tbl}[{col}]"))
    return f"CALCULATE({inner}, {', '.join(preds)})", None


def _emit_side(side: dict) -> tuple[str | None, str | None]:
    """A ratio side is an inline aggregation -- identical rules to a base body."""
    return _emit_base(side)  # same shape/validation; returns (dax, reason)


def _emit_ratio(defn: dict) -> tuple[str | None, str | None]:
    """Emit a ratio measure as DIVIDE(numerator, denominator)."""
    num = defn.get("numerator")
    den = defn.get("denominator")
    if not isinstance(num, dict) or not isinstance(den, dict):
        return None, "ratio requires numerator and denominator objects"
    num_dax, num_reason = _emit_side(num)
    if num_reason is not None:
        return None, f"numerator: {num_reason}"
    den_dax, den_reason = _emit_side(den)
    if den_reason is not None:
        return None, f"denominator: {den_reason}"
    return f"DIVIDE({num_dax}, {den_dax})", None
