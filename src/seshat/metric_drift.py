"""L3 contract<->DAX drift check: does a DIVIDE measure's DENOMINATOR apply the
filter the approved metric contract declares?

This is the layer that catches the 50.37-vs-33.55 class -- a measure that is valid,
best-practice-clean DAX yet divides by the WRONG row-set (e.g. all transactions when
the contract rules known-status only). `retail check` (D1-D8) proves DAX *form*;
`retail validate` reconciles *column sums*; neither sees a wrong denominator. L3 does.

SEPARATE MODULE ON PURPOSE (mirrors `validate_targets.py`): it parses YAML contracts
(pyyaml, a dev/optional dep) and MUST NOT be imported by the `retail check` core chain
(`seshat.cli -> seshat.rules`), whose stdlib-only invariant keeps `dependencies = []`.
The `retail-semantic-check` skill imports this lazily; the static gate never does.

DESIGN (from the F038-era design workflow + its adversary red-team):
  * The CONTRACT's structured `definition` is the SOLE arbiter of the correct
    denominator -- never the DAX shape, never prose. (The workflow's own scouts
    inverted 33.55/50.37 reading prose; a deterministic filter-set comparison cannot
    be inference-inverted.)
  * ESCALATE is the DEFAULT branch. A recognized predicate spelling is compared;
    ANYTHING else (unknown predicate, non-ratio measure, unbalanced parens) escalates
    to a human. Never pass-on-uncertain (false negative) and never drift-on-uncertain
    (the S8-over-broad false positive).
  * No bare-vs-wrapped verdict. Two approved measures can both have a wrapped CALCULATE
    denominator differing only in the filter COLUMN; the discriminator is the
    column-specific filter-set, read from the contract.
  * The base measure-ref (e.g. [TransactionCount]) is treated as OPAQUE -- L3 does not
    re-derive its aggregation (that is the base measure's own contract's job). It only
    compares the denominator's FILTER-SET to the contract.

This module is stdlib-only at import time. `yaml` is imported lazily ONLY in the
contract-file loader (`load_definition`), never at module scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = ["Verdict", "check_measure_drift", "load_definition", "Filter"]


@dataclass(frozen=True)
class Verdict:
    """One measure's drift verdict.

    status:
      pass     -- the DAX denominator filter-set matches the contract definition.
      drift    -- a recognized mismatch (wrong/missing/extra filter, wrong column/op).
      escalate -- the DEFAULT for anything not confidently recognized (raise to a
                  human).
      skip     -- the contract has no `definition` block to check against.
    """

    status: str  # "pass" | "drift" | "escalate" | "skip"
    detail: str


@dataclass(frozen=True)
class Filter:
    """A normalized filter predicate (denominator/numerator): column + recognized op."""

    column: str
    op: str  # "is_not_null" | "is_true" (the recognized-op whitelist)


# --- recognized predicate spellings (TIGHT whitelist; anything else escalates) ---
# `NOT ( ISBLANK ( <colref> ) )`  -> is_not_null
_RE_IS_NOT_NULL = re.compile(
    r"^NOT\s*\(\s*ISBLANK\s*\(\s*(?P<col>.+?)\s*\)\s*\)$", re.IGNORECASE | re.DOTALL
)
# `<colref> = TRUE ( )`  -> is_true
_RE_IS_TRUE = re.compile(
    r"^(?P<col>.+?)\s*=\s*TRUE\s*\(\s*\)$", re.IGNORECASE | re.DOTALL
)
# --- WIDENED whitelist: 4 more recognized-equivalent spellings ---
# `<colref> <> BLANK ( )`  -> is_not_null  (recognized-equivalent of NOT(ISBLANK))
_RE_NE_BLANK = re.compile(
    r"^(?P<col>.+?)\s*<>\s*BLANK\s*\(\s*\)$", re.IGNORECASE | re.DOTALL
)
# `ISBLANK ( <colref> ) = FALSE ( )`  -> is_not_null
_RE_ISBLANK_EQ_FALSE = re.compile(
    r"^ISBLANK\s*\(\s*(?P<col>.+?)\s*\)\s*=\s*FALSE\s*\(\s*\)$",
    re.IGNORECASE | re.DOTALL,
)
# `TRUE ( ) = <colref>`  -> is_true  (order-flipped form of col = TRUE())
_RE_TRUE_EQ = re.compile(
    r"^TRUE\s*\(\s*\)\s*=\s*(?P<col>.+?)$", re.IGNORECASE | re.DOTALL
)
# `<colref> <> FALSE ( )`  -> is_true
_RE_NE_FALSE = re.compile(
    r"^(?P<col>.+?)\s*<>\s*FALSE\s*\(\s*\)$", re.IGNORECASE | re.DOTALL
)

# Recognized spellings grouped by the op they normalize to. Order matters: the
# first regex that both matches AND yields a non-empty column wins.
_IS_NOT_NULL_RES = (_RE_IS_NOT_NULL, _RE_NE_BLANK, _RE_ISBLANK_EQ_FALSE)
_IS_TRUE_RES = (_RE_IS_TRUE, _RE_TRUE_EQ, _RE_NE_FALSE)


def _strip_column_qualification(colref: str) -> str:
    """`'gold fct_sales_rss'[discount_applied]` -> `discount_applied`; `[col]` -> `col`.

    The contract names a bare column; the DAX qualifies it by table. Normalize the DAX
    form to the bare column so the comparison is apples-to-apples. A reference that is
    NOT a simple (optionally-qualified) column produces None -> the caller escalates.
    """
    s = colref.strip()
    # optional 'table'/table prefix, then [column]
    m = re.fullmatch(r"(?:'[^']*'|[A-Za-z_][\w ]*)?\s*\[\s*([^\]]+?)\s*\]", s)
    return m.group(1).strip() if m else ""


def _paren_delta(ch: str) -> int:
    """Nesting change for one char: +1 for `(`, -1 for `)`, 0 otherwise."""
    if ch == "(":
        return 1
    if ch == ")":
        return -1
    return 0


def _split_balanced(args: str) -> list[str] | None:
    """Split a comma-separated DAX arg list at top-level commas only (paren-aware).

    Returns None on unbalanced parentheses (the caller escalates rather than guesses).
    """
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in args:
        depth += _paren_delta(ch)
        if depth < 0:
            return None  # a `)` with no matching `(` -- unbalanced
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if depth != 0:
        return None
    parts.append("".join(cur).strip())
    return parts


def _outer_call(expr: str, func: str) -> str | None:
    """If `expr` is exactly `FUNC( ... )` at the top level, return the inner arg text.

    Returns None if `expr` is not a single top-level call to `func` (so a bare measure
    ref, a different function, or trailing junk all yield None). Paren-balanced.
    """
    # Strip a trailing `;` and surrounding whitespace -- a non-standard but harmless
    # statement terminator must not make the wrapper unrecognized, which would
    # silently bypass the drift check (audit 2026-06-26 #33).
    expr = expr.strip().rstrip(";").rstrip()
    # re.escape: `func` is interpolated into a regex. Callers pass literals today
    # ("CALCULATE"/"DIVIDE"), but escaping prevents a future dynamic func with
    # regex metacharacters from being treated as a pattern (audit #25).
    m = re.match(rf"^{re.escape(func)}\s*\(", expr, re.IGNORECASE)
    if not m:
        return None
    inner_start = m.end()
    close = _matching_close_paren(expr, inner_start)
    if close is None:
        return None  # unbalanced
    # the close of the opening `(` must be the LAST char (a single top-level call,
    # no trailing tokens); otherwise this is not a single top-level call to `func`.
    return expr[inner_start:close] if close == len(expr) - 1 else None


def _matching_close_paren(expr: str, inner_start: int) -> int | None:
    """Index of the `)` closing the `(` before `inner_start`, or None if unbalanced.

    Scans from `inner_start` with the opening paren already counted (depth starts at 1).
    """
    depth = 1
    for i in range(inner_start, len(expr)):
        depth += _paren_delta(expr[i])
        if depth == 0:
            return i
    return None


def _normalize_denominator(expr: str) -> tuple[str, list[str]] | None:
    """Reduce a denominator expression to (base_measure_ref, [predicate_texts]).

    Handles (right-hand side is the returned tuple):
      [Measure]                    -> ("[Measure]", [])           # bare = no filter
      CALCULATE([Measure])         -> ("[Measure]", [])           # empty wrapper = bare
      CALCULATE([Measure], p1, p2) -> ("[Measure]", ["p1","p2"]) # wrapped + filters

    Returns None if the shape is not one of these (caller escalates). Only a SYNTACTIC
    empty CALCULATE is collapsed; a semantic no-op like CALCULATE([M], TRUE()) keeps its
    predicate `TRUE()` and will escalate (unrecognized op), per the adversary note.
    """
    expr = expr.strip()
    inner = _outer_call(expr, "CALCULATE")
    if inner is None:
        # not a CALCULATE -- accept only a bare measure ref `[Name]`, else None
        if re.fullmatch(r"\[[^\]]+\]", expr):
            return (expr, [])
        return None
    parts = _split_balanced(inner)
    if parts is None:
        return None
    base = parts[0].strip()
    preds = [p for p in parts[1:] if p.strip()]
    return (base, preds)


def _recognize_filter(pred: str) -> Filter | None:
    """Map a predicate text to a recognized Filter, or None (-> escalate).

    The whitelist is deliberately TIGHT. Recognized canonical spellings:
      is_not_null:  NOT(ISBLANK(col)) | col <> BLANK() | ISBLANK(col) = FALSE()
      is_true:      col = TRUE()      | TRUE() = col   | col <> FALSE()
    DAX has further equivalent spellings (LEN(col)<>0, COALESCE(...), col = 1, ...)
    that need type knowledge or are low-frequency; those are NOT guessed -- they
    escalate. Every captured column is routed through _strip_column_qualification
    (bracket-notation only), so a non-column capture falls through to escalate.
    """
    pred = pred.strip()
    for regexes, op in ((_IS_NOT_NULL_RES, "is_not_null"), (_IS_TRUE_RES, "is_true")):
        for rx in regexes:
            m = rx.match(pred)
            if m and (col := _strip_column_qualification(m.group("col"))):
                return Filter(column=col, op=op)
    return None


def _contract_filters(side: dict[str, Any]) -> frozenset[Filter] | None:
    """Build the contract's declared filter-set for one side, or None if malformed."""
    raw = side.get("filter", [])
    if raw is None:
        raw = []
    # Fail-closed: a malformed `filter` escalates (None), never raises. A non-list
    # or a non-dict element is unrecognized shape -> escalate to a human.
    if not isinstance(raw, list):
        return None
    out: set[Filter] = set()
    for f in raw:
        if not isinstance(f, dict):
            return None
        col = f.get("column")
        op = f.get("op")
        if not col or op not in ("is_not_null", "is_true"):
            return None
        out.add(Filter(column=str(col), op=str(op)))
    return frozenset(out)


# AGG name -> the single DAX function the generator emits for it (mirror of dax_gen)
_BASE_AGG_FUNC: dict[str, str] = {
    "sum": "SUM",
    "count": "COUNT",
    "distinct_count": "DISTINCTCOUNT",
    "average": "AVERAGE",
    "count_rows": "COUNTROWS",
}


def _recognized_agg_func(expr: str) -> str | None:
    """Return the recognized AGG function name if `expr` is a top-level AGG(...) call.

    Returns None if `expr` is not a call to any known aggregation function.
    Uses _outer_call (paren-anchored) so COUNT does not prefix-match COUNTROWS.
    """
    for func in _BASE_AGG_FUNC.values():
        if _outer_call(expr, func) is not None:
            return func
    return None


def _check_agg(
    expr: str, want_func: str, *, unrecognized_detail: str
) -> tuple[str, Verdict | None]:
    """Resolve the top-level AGG function of `expr` and compare it to `want_func`.

    Returns `(func, None)` when a recognized aggregation matches the contract, else
    `("", verdict)` where verdict is the escalate/drift to short-circuit on. The
    `unrecognized_detail` message is caller-supplied so the bare and CALCULATE arms
    keep their distinct escalate wording.
    """
    actual_func = _recognized_agg_func(expr)
    if actual_func is None:
        return "", Verdict("escalate", unrecognized_detail)
    if actual_func != want_func:
        return "", Verdict(
            "drift", f"aggregation {actual_func!r} != contract {want_func!r}"
        )
    return actual_func, None


def _recognize_filters(
    parts: list[str], *, detail_noun: str
) -> frozenset[Filter] | Verdict:
    """Map predicate texts to a recognized filter-set, or a Verdict to escalate on.

    Ignores empty parts. Any unrecognized predicate escalates with a message using the
    caller-supplied `detail_noun` (e.g. "predicate" vs "denominator predicate") so the
    base and ratio paths keep their distinct wording.
    """
    recognized: set[Filter] = set()
    for p in (x for x in parts if x.strip()):
        f = _recognize_filter(p)
        if f is None:
            return Verdict("escalate", f"unrecognized {detail_noun}: {p!r}")
        recognized.add(f)
    return frozenset(recognized)


def _base_dax_filters(expr: str, want_func: str) -> frozenset[Filter] | Verdict:
    """Resolve a base measure's DAX filter-set, checking its aggregation en route.

    Recognizes exactly two shapes (mirroring the generator's emit templates):
      AGG( <col-or-table> )                          -> no filter
      CALCULATE( AGG( <col-or-table> ), p1, p2, ... ) -> wrapped + filters
    Returns the recognized filter-set, or a Verdict (escalate/drift) to short-circuit
    on. ESCALATE for anything else; never guesses. The base measure is its OWN
    contract, so its aggregation IS checked (unlike a referenced measure).
    """
    inner = _outer_call(expr, "CALCULATE")
    if inner is None:
        # bare aggregation, no filter
        _func, verdict = _check_agg(
            expr,
            want_func,
            unrecognized_detail="measure is not a recognized AGG(col) shape",
        )
        return verdict if verdict is not None else frozenset()

    parts = _split_balanced(inner)
    if parts is None or not parts:
        return Verdict("escalate", "CALCULATE arguments unbalanced")
    _func, verdict = _check_agg(
        parts[0].strip(),
        want_func,
        unrecognized_detail="CALCULATE inner is not a recognized AGG(col)",
    )
    if verdict is not None:
        return verdict
    return _recognize_filters(parts[1:], detail_noun="predicate")


def _check_base_drift(dax_expr: str, definition: dict[str, Any]) -> Verdict:
    """Verify a kind:base measure's aggregation + filter-set vs its contract.

    Resolves the contract's declared aggregation + filter-set, then compares them to
    the DAX filter-set (recognized by `_base_dax_filters`). ESCALATE is the default for
    anything not confidently recognized.
    """
    agg = definition.get("aggregation")
    want_func = _BASE_AGG_FUNC.get(agg) if agg else None
    if want_func is None:
        return Verdict("escalate", f"contract aggregation {agg!r} not recognized")

    # _contract_filters reads side["filter"]; wrap the base filter list in that shape.
    contract_filters = _contract_filters({"filter": definition.get("filter", [])})
    if contract_filters is None:
        return Verdict("escalate", "contract filter is malformed or uses an unknown op")

    dax_filters = _base_dax_filters(dax_expr.strip(), want_func)
    if isinstance(dax_filters, Verdict):
        return dax_filters

    if dax_filters == contract_filters:
        return Verdict("pass", "base aggregation + filter-set matches the contract")
    return Verdict(
        "drift",
        f"filter-set {sorted((f.column, f.op) for f in dax_filters)} "
        f"!= contract {sorted((f.column, f.op) for f in contract_filters)}",
    )


def _is_ratio_needing_additive_default(d: dict[str, Any] | None) -> bool:
    """True when `d` is a kind:ratio contract with `additive` unset.

    kind:ratio implies non-additive; the caller need not restate additive:false. An
    explicit `additive:true` is respected (returns False), so only a truly-absent key
    triggers the default injection.
    """
    return bool(d) and d.get("kind") == "ratio" and "additive" not in d


def _is_measure_ref(base: str) -> bool:
    """True when `base` is a bare `[Name]` measure reference (the OPAQUE base form)."""
    return bool(re.fullmatch(r"\[[^\]]+\]", base))


def _expected_inline_operand(contract_side: dict[str, Any]) -> str | None:
    """The DAX operand text a contract's inline aggregation source must emit.

    Mirrors the generator's `_qualify`: ``{table: "gold.x", column: "c"}`` ->
    ``'gold x'[c]``; a table-only source (e.g. count_rows) -> ``'gold x'``.
    Returns None when the source shape is absent/mis-typed (caller escalates --
    it cannot verify what it cannot resolve).
    """
    source = contract_side.get("source")
    if not isinstance(source, dict):
        return None
    table = source.get("table")
    if not isinstance(table, str) or not table:
        return None
    quoted = "'" + table.replace(".", " ") + "'"
    column = source.get("column")
    if isinstance(column, str) and column:
        return f"{quoted}[{column}]"
    return quoted


def _inline_operand_matches(dax_agg_expr: str, contract_side: dict[str, Any]) -> bool:
    """True when the DAX ``AGG(<operand>)`` operand equals the contract source.

    Compares the argument inside the recognized aggregation call to
    `_expected_inline_operand`, ignoring surrounding whitespace. False when the
    operand cannot be extracted or does not match -- so a denominator that
    aggregates a DIFFERENT column than the contract declares (e.g. a
    `DISTINCTCOUNT(order_id)` contract with `DISTINCTCOUNT(customer_id)` DAX) is
    NOT silently accepted (#432 / Codex #449).
    """
    func = _recognized_agg_func(dax_agg_expr)
    if func is None:
        return False
    inner = _outer_call(dax_agg_expr, func)
    expected = _expected_inline_operand(contract_side)
    if inner is None or expected is None:
        return False
    return inner.strip() == expected


def _ratio_denominator_filters(
    dax_denominator: str, contract_side: dict[str, Any]
) -> frozenset[Filter] | Verdict:
    """Resolve a DIVIDE denominator's filter-set, dispatching on its base shape.

    Two recognized families (audit #432 widened the second):
      * measure-ref base ([Measure] / CALCULATE([Measure], ...)) -- OPAQUE: the
        base measure is its own contract, so only its filter-set is compared; its
        aggregation is never read here (unchanged pre-#432 behavior).
      * inline aggregation-call base (AGG(col) / CALCULATE(AGG(col), ...)) --
        reuses `_base_dax_filters` (the same shape logic the kind:base path
        already trusts), which checks the aggregation FUNCTION against
        `contract_side['aggregation']`, AND -- because the inline call is not
        opaque and has no separate contract to defer to -- verifies the aggregated
        OPERAND matches `contract_side['source']` (Codex #449: otherwise a
        different-column denominator computing a different KPI would pass).
    Anything genuinely unrecognized (VAR/RETURN, nested CALCULATE, a non-AGG
    call), or an operand that does not match the contract source, escalates.
    """
    den = _normalize_denominator(dax_denominator)
    if den is not None and _is_measure_ref(den[0]):
        _base_ref, pred_texts = den
        return _recognize_filters(pred_texts, detail_noun="denominator predicate")

    # Not a measure-ref shape (either _normalize_denominator returned None -- a
    # bare AGG(col) -- or it returned a CALCULATE(...) whose base is an inline
    # AGG(col) call, not `[Measure]`). Reuse the base-measure shape logic, which
    # recognizes AGG(col) and CALCULATE(AGG(col), p1, ...) and checks the
    # aggregation function en route.
    agg = contract_side.get("aggregation")
    want_func = _BASE_AGG_FUNC.get(agg) if agg else None
    if want_func is None:
        return Verdict(
            "escalate", f"contract denominator aggregation {agg!r} not recognized"
        )
    # Verify the aggregated operand matches the contract source before trusting the
    # inline call: the CALCULATE arm's base is parts[0], the bare arm is the whole
    # expr. Escalate (never silently pass) when the operand cannot be confirmed.
    inner_agg = dax_denominator.strip()
    calc = _outer_call(inner_agg, "CALCULATE")
    if calc is not None:
        parts = _split_balanced(calc)
        inner_agg = parts[0].strip() if parts else inner_agg
    if not _inline_operand_matches(inner_agg, contract_side):
        return Verdict(
            "escalate",
            "denominator aggregates an operand that does not match the contract "
            "source (or the operand could not be verified)",
        )
    return _base_dax_filters(dax_denominator.strip(), want_func)


def _check_ratio_drift(dax_expr: str, definition: dict[str, Any]) -> Verdict:
    """Verify a ratio (DIVIDE) measure's denominator filter-set vs its contract.

    Mirrors `_check_base_drift`: build the contract filter-set, recognize the DIVIDE
    denominator shape, map its predicates to Filters, and compare. ESCALATE is the
    default for anything not confidently recognized.
    """
    contract_filters = _contract_filters(definition["denominator"])
    if contract_filters is None:
        return Verdict(
            "escalate", "contract denominator filter is malformed or uses an unknown op"
        )

    # The measure must be a single top-level DIVIDE. DAX DIVIDE takes 2 or 3 args:
    # DIVIDE(num, den) or DIVIDE(num, den, alternate_result). The denominator is
    # always args[1]; the optional 3rd arg is the alternate result and does not
    # affect the denominator filter-set (audit 2026-06-26: 3-arg form was wrongly
    # escalated, skipping the drift check on a common divide-by-zero pattern).
    inner = _outer_call(dax_expr.strip(), "DIVIDE")
    if inner is None:
        return Verdict("escalate", "measure is not a single top-level DIVIDE ratio")
    args = _split_balanced(inner)
    if args is None or len(args) not in (2, 3):
        return Verdict("escalate", "DIVIDE does not have 2 or 3 balanced arguments")

    # denominator shape: bare/CALCULATE-wrapped measure ref (opaque) OR an inline
    # aggregation call (#432 widening) -- see _ratio_denominator_filters.
    filters = _ratio_denominator_filters(args[1], definition["denominator"])
    if isinstance(filters, Verdict):
        return filters

    if filters == contract_filters:
        return Verdict("pass", "denominator filter-set matches the contract")
    return Verdict(
        "drift",
        f"denominator filter-set {sorted((f.column, f.op) for f in filters)} "
        f"!= contract {sorted((f.column, f.op) for f in contract_filters)}",
    )


def check_measure_drift(dax_expr: str, definition: dict[str, Any] | None) -> Verdict:
    """Compare a DIVIDE measure's denominator filter-set to its contract definition.

    Returns a Verdict (pass | drift | escalate | skip). ESCALATE is the default for any
    expression not confidently recognized. Never raises on bad DAX -- escalates instead.
    If definition.kind == "base", verify the base measure's aggregation + filter-set
    against its own contract.
    """
    if definition and definition.get("kind") == "base":
        return _check_base_drift(dax_expr, definition)
    # kind:ratio implies non-additive; shallow-copy only when the key is truly absent.
    if _is_ratio_needing_additive_default(definition):
        definition = {**definition, "additive": False}

    # Backward compat: no structured definition -> nothing to check.
    if not definition or "denominator" not in definition:
        return Verdict("skip", "contract has no structured `definition.denominator`")

    # Additive measures are not ratios; denominator filter-set logic does not apply.
    # Require an explicit `additive: false` to proceed; True or absent -> escalate.
    if definition.get("additive") is not False:
        return Verdict(
            "escalate",
            "additive measure (or `additive` unset); "
            "denominator filter-set logic does not apply",
        )

    return _check_ratio_drift(dax_expr, definition)


def load_definition(contract_path: str) -> dict[str, Any] | None:
    """Read a metric contract YAML and return its optional `definition` block (or None).

    Lazy `import yaml` (dev/optional dep) -- this is the ONLY place yaml is touched, and
    this module is never in the `retail check` core import chain (the stdlib invariant).
    """
    from pathlib import Path

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    data = yaml.safe_load(Path(contract_path).read_text(encoding="utf-8")) or {}
    return data.get("definition")
