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


def _validate_ok_result(
    dax: str | None, tmdl_block: str | None, reason: str | None
) -> None:
    """Enforce the ok=True invariants: dax + tmdl_block present, no reason."""
    if dax is None or tmdl_block is None:
        raise ValueError("ok GenResult must populate dax and tmdl_block")
    if reason is not None:
        raise ValueError("ok GenResult must not carry a reason")


def _validate_refusal_result(
    dax: str | None, tmdl_block: str | None, reason: str | None
) -> None:
    """Enforce the ok=False invariants: no dax/tmdl_block, reason present."""
    if dax is not None or tmdl_block is not None:
        raise ValueError("refusal GenResult must not carry dax/tmdl_block")
    if not reason:
        raise ValueError("refusal GenResult must carry a reason")


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
        validate = _validate_ok_result if self.ok else _validate_refusal_result
        validate(self.dax, self.tmdl_block, self.reason)

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


def _validate_base_source(
    defn: dict,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Validate agg + source shape -> (agg, table, column, reason).

    On refusal, agg/table/column are None and reason carries the message; on
    success reason is None. Check order: aggregation, gold.* table, then the
    count_rows-vs-column rules.
    """
    agg = defn.get("aggregation")
    if agg not in _AGG_TO_DAX:
        return None, None, None, f"unsupported aggregation {agg!r}"
    source = defn.get("source") or {}
    table = source.get("table")
    column = source.get("column")
    if not isinstance(table, str) or not table.startswith("gold."):
        return None, None, None, f"source.table must be a gold.* table, got {table!r}"
    if agg == "count_rows":
        if column:
            return (
                None,
                None,
                None,
                "count_rows must not specify source.column (table only)",
            )
    elif not column:
        return None, None, None, f"aggregation {agg!r} requires source.column"
    return agg, table, column, None


def _emit_filters(filters: object, table: str) -> tuple[list[str] | None, str | None]:
    """Filter list -> (predicates, reason). Empty/absent filters -> ([], None).

    Fail-closed: a malformed `filter` is a refusal, never a raise. Validate the
    SHAPE before iterating (a scalar or single dict would otherwise blow up).
    """
    filters = filters or []
    if not isinstance(filters, list):
        return None, "filter must be a list of {column, op} objects"

    preds: list[str] = []
    tbl = "'" + table.replace(".", " ") + "'"
    for f in filters:
        if not isinstance(f, dict):
            return None, f"filter entry is not an object: {f!r}"
        col = f.get("column")
        op = f.get("op")
        tmpl = _OP_TO_DAX.get(op) if op else None
        if not col or tmpl is None:
            return None, f"unrecognized filter op {op!r} on column {col!r}"
        preds.append(tmpl.format(col=f"{tbl}[{col}]"))
    return preds, None


def _emit_base(defn: dict) -> tuple[str | None, str | None]:
    agg, table, column, reason = _validate_base_source(defn)
    if reason is not None:
        return None, reason

    func = _AGG_TO_DAX[agg]
    inner = f"{func}({_qualify(table, column)})"

    preds, filter_reason = _emit_filters(defn.get("filter"), table)
    if filter_reason is not None:
        return None, filter_reason
    if not preds:
        return inner, None
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


_DEFAULT_FORMATS: dict[str, str] = {
    "sum": "#,0",
    "count": "#,0",
    "distinct_count": "#,0",
    "average": "#,0.00",
    "count_rows": "#,0",
    "ratio": "0.0%",
}


def _default_format(definition: dict) -> str:
    """Return the presentation default format string for this definition."""
    if definition.get("kind") == "ratio":
        return _DEFAULT_FORMATS["ratio"]
    return _DEFAULT_FORMATS.get(definition.get("aggregation", ""), "#,0")


def _build_tmdl_block(
    name: str, dax: str, format_string: str, display_folder: str, doc_intent: str
) -> str:
    """A TMDL measure block. /// doc is documentation only (from doc_intent)."""
    doc = (doc_intent or name).replace("\n", " ").strip()
    return (
        f"\t/// {doc}\n"
        f"\tmeasure {name} = {dax}\n"
        f"\t\tformatString: {format_string}\n"
        f"\t\tdisplayFolder: {display_folder}\n"
    )


def _is_d_rule(rule_id: str) -> bool:
    """The D-rule family is D1-D11 (TMDL/DAX hygiene): a 'D' followed by a digit.

    A bare startswith("D") also catches unrelated rules like DF1 (parked-on),
    which then run against this synthetic single-TMDL context and fail loud on
    their absent manifest -- so match the 'D' + digit shape precisely.
    """
    return len(rule_id) >= 2 and rule_id[0] == "D" and rule_id[1].isdigit()


def _run_d_rules(tmdl_block: str, name: str) -> tuple[list[str], list[str]]:
    """Stage the block under a temp SemanticModel path and run D1-D11."""
    import tempfile
    from pathlib import Path

    from . import rules as _rules_pkg  # noqa: F401  fire @register
    from .core import RuleContext, Severity
    from .registry import all_rules
    from .runner import _format  # "[sev] id msg (loc)"

    # A minimal TMDL table wrapper: `table T` header at indent 0, measure at indent 1.
    # No stub measure -- the generated block IS the only measure in the table.
    table_text = f"table T\n{tmdl_block}"
    errors: list[str] = []
    warnings: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rel = "Model.SemanticModel/definition/tables/T.tmdl"
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(table_text, encoding="utf-8")
        ctx = RuleContext(repo_root=root, tracked_files=(rel,))
        for reg in all_rules():
            if not _is_d_rule(reg.id):
                continue
            for f in reg.rule(ctx):
                line = _format(f)
                (errors if f.severity is Severity.ERROR else warnings).append(line)
    return errors, warnings


def _emit_for_kind(definition: dict) -> tuple[str | None, str | None]:
    """Dispatch on `kind` and emit DAX -> (dax, reason). An unknown kind is a
    refusal reason, so callers reproduce it via the shared reason path."""
    kind = definition.get("kind") if isinstance(definition, dict) else None
    if kind == "base":
        return _emit_base(definition)
    if kind == "ratio":
        return _emit_ratio(definition)
    return None, f"unsupported kind {kind!r} (expected base|ratio)"


def _verify_form(
    name: str,
    dax: str,
    definition: dict,
    format_string: str | None,
    display_folder: str | None,
    doc_intent: str | None,
) -> "GenResult":
    """STEP 4: build the TMDL block, run D1-D11 form verification, and return
    a success/refusal GenResult. Applies the presentation defaults."""
    fmt = format_string or _default_format(definition)
    folder = display_folder or "Measures"
    block = _build_tmdl_block(name, dax, fmt, folder, doc_intent or "")
    errors, warnings = _run_d_rules(block, name)
    if errors:
        return GenResult.refuse("D-rule ERROR(s): " + "; ".join(errors))
    return GenResult.success(dax=dax, tmdl_block=block, warnings=tuple(warnings))


def generate_measure(
    definition: dict,
    *,
    name: str,
    format_string: str | None = None,
    display_folder: str | None = None,
    doc_intent: str | None = None,
) -> "GenResult":
    """Contract definition -> verified DAX measure. Fail-closed at every step."""
    if not name:
        raise ValueError("generate_measure requires a measure name")

    # STEP 1+2: validate shape + emit DAX
    dax, reason = _emit_for_kind(definition)
    if reason is not None:
        return GenResult.refuse(reason)

    # STEP 3: semantic verify (L3) -- BEFORE form. pass is the only acceptable result.
    from .metric_drift import check_measure_drift

    v = check_measure_drift(dax, definition)
    if v.status != "pass":
        return GenResult.refuse(f"L3 {v.status}: {v.detail}")

    # STEP 4: build TMDL block + form verify (D1-D11)
    return _verify_form(
        name, dax, definition, format_string, display_folder, doc_intent
    )


def load_contract(path: str) -> dict:
    """Read a metric contract YAML and return the whole parsed mapping.

    Lazy `import yaml` (dev/optional dep) -- the ONLY yaml touch in this module,
    kept out of the `retail check` core chain (the stdlib-only invariant).
    """
    from pathlib import Path

    import yaml  # lazy

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"contract {path} is not a YAML mapping")
    return data
