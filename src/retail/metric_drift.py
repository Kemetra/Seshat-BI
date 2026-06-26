"""L3 contract<->DAX drift check: does a DIVIDE measure's DENOMINATOR apply the
filter the approved metric contract declares?

This is the layer that catches the 50.37-vs-33.55 class -- a measure that is valid,
best-practice-clean DAX yet divides by the WRONG row-set (e.g. all transactions when
the contract rules known-status only). `retail check` (D1-D8) proves DAX *form*;
`retail validate` reconciles *column sums*; neither sees a wrong denominator. L3 does.

SEPARATE MODULE ON PURPOSE (mirrors `validate_targets.py`): it parses YAML contracts
(pyyaml, a dev/optional dep) and MUST NOT be imported by the `retail check` core chain
(`retail.cli -> retail.rules`), whose stdlib-only invariant keeps `dependencies = []`.
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


def _split_balanced(args: str) -> list[str] | None:
    """Split a comma-separated DAX arg list at top-level commas only (paren-aware).

    Returns None on unbalanced parentheses (the caller escalates rather than guesses).
    """
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in args:
        if ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return None
            cur.append(ch)
        elif ch == "," and depth == 0:
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
    expr = expr.strip()
    m = re.match(rf"^{func}\s*\(", expr, re.IGNORECASE)
    if not m:
        return None
    inner_start = m.end()
    depth = 1
    i = inner_start
    while i < len(expr):
        c = expr[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                # must be the LAST char (a single top-level call, no trailing tokens)
                return expr[inner_start:i] if i == len(expr) - 1 else None
        i += 1
    return None  # unbalanced


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
    # is_not_null spellings
    for rx in (_RE_IS_NOT_NULL, _RE_NE_BLANK, _RE_ISBLANK_EQ_FALSE):
        m = rx.match(pred)
        if m:
            col = _strip_column_qualification(m.group("col"))
            if col:
                return Filter(column=col, op="is_not_null")
    # is_true spellings
    for rx in (_RE_IS_TRUE, _RE_TRUE_EQ, _RE_NE_FALSE):
        m = rx.match(pred)
        if m:
            col = _strip_column_qualification(m.group("col"))
            if col:
                return Filter(column=col, op="is_true")
    return None


def _contract_filters(side: dict[str, Any]) -> frozenset[Filter] | None:
    """Build the contract's declared filter-set for one side, or None if malformed."""
    raw = side.get("filter", [])
    if raw is None:
        raw = []
    out: set[Filter] = set()
    for f in raw:
        col = f.get("column")
        op = f.get("op")
        if not col or op not in ("is_not_null", "is_true"):
            return None
        out.add(Filter(column=str(col), op=str(op)))
    return frozenset(out)


def check_measure_drift(dax_expr: str, definition: dict[str, Any] | None) -> Verdict:
    """Compare a DIVIDE measure's denominator filter-set to its contract definition.

    Returns a Verdict (pass | drift | escalate | skip). ESCALATE is the default for any
    expression not confidently recognized. Never raises on bad DAX -- escalates instead.
    """
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

    contract_filters = _contract_filters(definition["denominator"])
    if contract_filters is None:
        return Verdict(
            "escalate", "contract denominator filter is malformed or uses an unknown op"
        )

    # The measure must be a single top-level DIVIDE(num, den).
    inner = _outer_call(dax_expr.strip(), "DIVIDE")
    if inner is None:
        return Verdict("escalate", "measure is not a single top-level DIVIDE ratio")
    args = _split_balanced(inner)
    if args is None or len(args) != 2:
        return Verdict(
            "escalate", "DIVIDE does not have exactly two balanced arguments"
        )

    den = _normalize_denominator(args[1])
    if den is None:
        return Verdict(
            "escalate",
            "denominator shape not recognized (not a bare measure or CALCULATE)",
        )
    _base_ref, pred_texts = den

    # Map each denominator predicate to a recognized Filter; any unknown -> escalate.
    dax_filters: set[Filter] = set()
    for p in pred_texts:
        f = _recognize_filter(p)
        if f is None:
            return Verdict("escalate", f"unrecognized denominator predicate: {p!r}")
        dax_filters.add(f)

    if frozenset(dax_filters) == contract_filters:
        return Verdict("pass", "denominator filter-set matches the contract")
    return Verdict(
        "drift",
        f"denominator filter-set {sorted((f.column, f.op) for f in dax_filters)} "
        f"!= contract {sorted((f.column, f.op) for f in contract_filters)}",
    )


def load_definition(contract_path: str) -> dict[str, Any] | None:
    """Read a metric contract YAML and return its optional `definition` block (or None).

    Lazy `import yaml` (dev/optional dep) -- this is the ONLY place yaml is touched, and
    this module is never in the `retail check` core import chain (the stdlib invariant).
    """
    from pathlib import Path

    import yaml  # lazy: dev/optional dep, kept out of the retail check core chain

    data = yaml.safe_load(Path(contract_path).read_text(encoding="utf-8")) or {}
    return data.get("definition")
