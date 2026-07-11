"""HR9 -- rename-impact / orphaned-reference guard (spec 104, Principle III/V).

Extends the SC1/DF1 reconcile-and-fail-closed pattern to the MODEL surface.
Renaming a gold column or a TMDL measure can leave ``retail check`` green while
orphaning every reference that still points at the old name -- D1-D11 validate
DAX/TMDL shape, never cross-artifact name resolution. HR9 closes that gap.

HR9 never sees a rename EVENT (it has no diff); it detects the ORPHAN a rename
leaves -- a reference that no longer resolves to a currently-existing name.

What HR9 does (STATIC, fail-closed; per table, engages only with >=1 TMDL file):
  - Derives the TRUTH SET from the committed TMDL under
    ``powerbi/*.SemanticModel/definition/tables/*.tmdl``: every ``column <name>``
    (per table) and every ``measure <name>`` (unioned across the model's tables).
  - FR-003: resolves each ``binds_to.columns`` entry in every
    ``mappings/<table>/metrics/*.yaml`` against the cited gold table's TMDL
    columns; an unresolved column is an ORPHAN -> ``Severity.ERROR``.
  - FR-004: resolves each reference inside a TMDL measure's own DAX expression --
    a bare ``[Measure]`` (against the model-wide measure set) and a
    ``'table'[column]`` (against that named table's own columns) -- an unresolved
    token is an ORPHAN -> ``Severity.ERROR``.
  - FR-005: resolves each measure / ``dim[column]`` reference in a committed
    dashboard ``visual-contract-binding-map.md``'s field column -> ORPHAN ERROR.
  - FR-006: a table-qualified ``'table'[column]`` resolves ONLY within that named
    table's committed columns; an unqualified ``[Measure]`` resolves within the
    UNION of measures across the model's TMDL table files.
  - FR-007: a table with metric contracts but NO committed TMDL produces zero
    findings (no premature engagement; mirrors HR1's zero/one-star no-op).
  - FR-008: a contract's references are checked regardless of its own
    ``readiness.status`` -- referential integrity precedes approval state.

What HR9 NEVER does:
  - It NEVER decides which of two mismatched names is "correct", NEVER renames or
    auto-corrects, NEVER suggests a replacement (Principle V) -- it names the
    orphan + the artifact carrying it, and stops.
  - It NEVER executes DAX, connects to a DB, or opens a live PBIP surface
    (Principle VIII -- committed TMDL/YAML/Markdown text only); NEVER emits a
    numeric score (hard rule #9); NEVER writes a file (read-only).

Manifest-less by design: the truth set IS the committed TMDL (unlike SC1/DF1's
hand-curated manifests). Mirrors their reconcile CODE PATTERN, not their inputs.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from itertools import chain
from typing import NamedTuple

from ..core import Finding, RuleContext, Severity, is_test_path

try:
    from ..registry import register
except ImportError:  # pragma: no cover
    raise

RULE_ID = "HR9"

# committed TMDL table files for any semantic model
_TMDL_RE = re.compile(r"^powerbi/[^/]+\.SemanticModel/definition/tables/.+\.tmdl$")
_METRIC_RE = re.compile(r"^mappings/([^/]+)/metrics/[^/]+\.yaml$")
_BINDING_MAP_RE = re.compile(
    r"^mappings/([^/]+)/design/visual-contract-binding-map\.md$"
)

# TMDL declarations (line-leading, tab-indented)
_TABLE_DECL = re.compile(r"^table\s+(?:'([^']+)'|(\S+))", re.MULTILINE)
_COLUMN_DECL = re.compile(r"^\tcolumn\s+(?:'([^']+)'|(\S+))", re.MULTILINE)
_MEASURE_DECL = re.compile(r"^\tmeasure\s+(?:'([^']+)'|([^\s=]+))", re.MULTILINE)

# DAX reference tokens
_QUALIFIED_REF = re.compile(r"'([^']+)'\[([^\]]+)\]")  # 'table'[column]
# unquoted table[column] (binding-map idiom, e.g. dim_product_rss[category]);
# the table token is a bare identifier NOT preceded by ' or ] (so it is not the
# tail of a 'table'[a][b] chain)
_UNQUOTED_QUALIFIED_REF = re.compile(r"(?<![\w'\]])([A-Za-z_]\w*)\[([^\]]+)\]")
_BARE_MEASURE_REF = re.compile(
    r"(?<![\w'])\[([^\]]+)\]"
)  # [Measure] not preceded by ' or word


def _read(ctx: RuleContext, rel: str) -> str | None:
    try:
        return (ctx.repo_root / rel).read_text(encoding="utf-8")
    except OSError:
        return None


def _decl_name(m: re.Match) -> str:
    return (m.group(1) or m.group(2)).strip()


def _table_of(tmdl_text: str) -> str | None:
    m = _TABLE_DECL.search(tmdl_text)
    return _decl_name(m) if m else None


def _strip_table_prefix(table: str) -> str:
    """'gold fct_sales_rss' / 'gold.fct' -> bare 'fct_sales_rss' for matching a
    binds_to.gold_table like 'gold.fct_sales_rss'. Compare on the last token."""
    return table.replace("gold.", "").replace("gold ", "").strip().lower()


class _Model:
    """The truth set derived from one semantic model's committed TMDL files."""

    def __init__(self) -> None:
        # table (as declared, e.g. "gold fct_sales_rss") -> set of column names
        self.columns_by_table: dict[str, set[str]] = {}
        # bare-table-token -> set of column names (for binds_to.gold_table match)
        self.columns_by_bare: dict[str, set[str]] = {}
        self.measures: set[str] = set()

    def add_tmdl(self, text: str) -> None:
        table = _table_of(text)
        if table is None:
            return
        cols = {_decl_name(m) for m in _COLUMN_DECL.finditer(text)}
        self.columns_by_table.setdefault(table, set()).update(cols)
        self.columns_by_bare.setdefault(_strip_table_prefix(table), set()).update(cols)
        self.measures.update(_decl_name(m) for m in _MEASURE_DECL.finditer(text))


def _measure_expressions(text: str) -> str:
    """Return only the DAX from ``measure <name> = <expr>`` blocks.

    A measure block starts at a ``\\tmeasure ... =`` line and runs until the next
    top-level table-child declaration (``column`` / ``measure`` / ``partition`` /
    ``annotation`` / ``hierarchy`` / a dedent to a ``table`` line). This EXCLUDES
    the ``partition ... source = let ... in`` Power Query (M) block, whose
    ``[Field]`` / ``[Schema = ...]`` accessors are M syntax, not DAX measure refs
    (FR-004 scopes HR9 to a measure's OWN DAX expression only).
    """
    out: list[str] = []
    in_measure = False
    measure_start = re.compile(r"^\tmeasure\s+\S.*=")
    for line in text.splitlines():
        if measure_start.match(line):
            # start (or restart) a measure block: keep the declaration line itself
            in_measure = True
            out.append(line)
            continue
        if not in_measure:
            continue
        # A measure's own DAX continuation is indented DEEPER than the one-tab
        # declaration (i.e. "\t\t"+). ANY line that is NOT such a continuation --
        # a sibling one-tab decl (column/measure/partition/annotation/hierarchy),
        # a blank line, or a dedent to a top-level "table" line -- ENDS the block.
        # (A blank line inside a measure is not DAX; ending on it is safe because a
        # real multi-line DAX expression has no blank lines between its tokens.)
        if line.startswith("\t\t"):
            out.append(line)
        else:
            in_measure = False
    return "\n".join(out)


def _build_model(ctx: RuleContext) -> _Model:
    model = _Model()
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel):
            continue
        if not _TMDL_RE.match(rel):
            continue
        text = _read(ctx, rel)
        if text:
            model.add_tmdl(text)
    return model


def _metric_binds(text: str, model: _Model) -> tuple[str, list, set] | None:
    """Parse a metric YAML and return (gold_table, columns, known-column-set), or
    None when any guard fails (bad YAML, no binds_to, or no TMDL for the table)."""
    import yaml  # lazy

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    binds = data.get("binds_to")
    if not isinstance(binds, dict):
        return None
    gold_table = binds.get("gold_table")
    cols = binds.get("columns")
    if not isinstance(gold_table, str) or not isinstance(cols, list):
        return None
    known = model.columns_by_bare.get(_strip_table_prefix(gold_table))
    if known is None:
        return None  # no TMDL for this table yet -> FR-007 no-op
    return gold_table, cols, known


def _orphan_col_findings(
    rel: str, gold_table: str, cols: list, known: set
) -> list[Finding]:
    findings: list[Finding] = []
    for col in cols:
        if isinstance(col, str) and col not in known:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"metric contract binds_to column {col!r} does not "
                        f"resolve to any column of {gold_table} in the "
                        "committed TMDL (orphaned reference -- a rename left it "
                        "dangling)"
                    ),
                    locator=f"{rel}:{col}",
                )
            )
    return findings


def _check_metric_contracts(ctx: RuleContext, model: _Model) -> list[Finding]:
    """FR-003: binds_to.columns entries resolve to a column in the cited gold table."""
    findings: list[Finding] = []
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel) or not _METRIC_RE.match(rel):
            continue
        text = _read(ctx, rel)
        if text is None:
            continue
        binds = _metric_binds(text, model)
        if binds is None:
            continue
        gold_table, cols, known = binds
        findings.extend(_orphan_col_findings(rel, gold_table, cols, known))
    return findings


def _qualified_ref_findings(rel: str, text: str, model: _Model) -> list[Finding]:
    # resolve qualified 'table'[col] against that table's columns.
    findings: list[Finding] = []
    for qm in _QUALIFIED_REF.finditer(text):
        qtable, qcol = qm.group(1), qm.group(2)
        known = model.columns_by_table.get(qtable)
        if known is not None and qcol not in known:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"TMDL DAX reference {qtable!r}[{qcol}] does not resolve "
                        f"to a column of {qtable!r} (orphaned reference)"
                    ),
                    locator=f"{rel}:{qcol}",
                )
            )
    return findings


def _bare_measure_findings(rel: str, blanked: str, model: _Model) -> list[Finding]:
    # bare [X] against the model-wide measure set (skipping column names to avoid
    # flagging a bare [col] that is really a same-line measure ref target).
    findings: list[Finding] = []
    for bm in _BARE_MEASURE_REF.finditer(blanked):
        ref = bm.group(1).strip()
        if not ref:
            continue
        if ref not in model.measures and ref not in _all_columns(model):
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"TMDL DAX reference [{ref}] does not resolve to any "
                        "measure in the model (orphaned reference)"
                    ),
                    locator=f"{rel}:{ref}",
                )
            )
    return findings


def _check_tmdl_dax(ctx: RuleContext, model: _Model) -> list[Finding]:
    """FR-004/FR-006: DAX tokens inside a measure resolve to a known measure/column."""
    findings: list[Finding] = []
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel) or not _TMDL_RE.match(rel):
            continue
        full = _read(ctx, rel)
        if full is None:
            continue
        # scope to measure DAX ONLY -- never the partition/source M block, whose
        # [Field] accessors are M syntax, not DAX measure refs (FR-004).
        text = _measure_expressions(full)
        findings.extend(_qualified_ref_findings(rel, text, model))
        # bare [Measure] refs: blank out qualified refs first so 'table'[col]'s
        # [col] is not re-read as a bare measure token.
        blanked = _QUALIFIED_REF.sub("''[]", text)
        findings.extend(_bare_measure_findings(rel, blanked, model))
    return findings


def _all_columns(model: _Model) -> set[str]:
    out: set[str] = set()
    for cols in model.columns_by_table.values():
        out |= cols
    return out


class _BindingScan(NamedTuple):
    """Per-binding-map invariants threaded through the resolution helpers.

    ``rel``/``model``/``all_cols`` are fixed for one file; ``seen`` dedupes
    across all three reference forms (mutated in place through this reference).
    """

    rel: str
    model: _Model
    all_cols: set[str]
    seen: set


def _resolve_qualified(scan: _BindingScan, qtable: str, qcol: str) -> Finding | None:
    # resolve against the named table's columns; a binding map uses the
    # bare table token (dim_product_rss), so match columns_by_bare too.
    known = scan.model.columns_by_table.get(qtable)
    if known is None:
        known = scan.model.columns_by_bare.get(_strip_table_prefix(qtable))
    if known is None:
        return None
    if qcol in known:
        return None
    if (qtable, qcol) in scan.seen:
        return None
    scan.seen.add((qtable, qcol))
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=(
            f"dashboard binding references {qtable}[{qcol}], which "
            "does not resolve to a committed column (orphaned)"
        ),
        locator=f"{scan.rel}:{qcol}",
    )


def _check_bare_measure_refs(scan: _BindingScan, blanked: str) -> list[Finding]:
    findings: list[Finding] = []
    for bm in _BARE_MEASURE_REF.finditer(blanked):
        ref = bm.group(1).strip()
        if not ref or ref in scan.seen:
            continue
        if ref not in scan.model.measures and ref not in scan.all_cols:
            scan.seen.add(ref)
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dashboard binding references [{ref}], which does not "
                        "resolve to any committed measure (orphaned)"
                    ),
                    locator=f"{scan.rel}:{ref}",
                )
            )
    return findings


def _check_one_binding_map(scan: _BindingScan, text: str) -> list[Finding]:
    findings: list[Finding] = []
    # quoted 'table'[column] THEN unquoted table[column] (both binding idioms);
    # order-preserving across the two forms.
    quals = chain(_QUALIFIED_REF.finditer(text), _UNQUOTED_QUALIFIED_REF.finditer(text))
    for qm in quals:
        finding = _resolve_qualified(scan, qm.group(1), qm.group(2))
        if finding is not None:
            findings.append(finding)
    # blank BOTH qualified forms so their [col] is not re-read as a bare measure
    blanked = _UNQUOTED_QUALIFIED_REF.sub("x[]", _QUALIFIED_REF.sub("''[]", text))
    findings.extend(_check_bare_measure_refs(scan, blanked))
    return findings


def _check_binding_maps(ctx: RuleContext, model: _Model) -> list[Finding]:
    """FR-005: measure / dim[column] refs in a binding map resolve to the truth set."""
    findings: list[Finding] = []
    all_cols = _all_columns(model)
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel) or not _BINDING_MAP_RE.match(rel):
            continue
        text = _read(ctx, rel)
        if text is None:
            continue
        scan = _BindingScan(rel, model, all_cols, set())
        findings.extend(_check_one_binding_map(scan, text))
    return findings


@register(RULE_ID, "rename-impact orphaned-reference guard")
def check_hr9(ctx: RuleContext) -> Iterable[Finding]:
    model = _build_model(ctx)
    # FR-007: engage only when a committed TMDL model surface exists
    if not model.columns_by_table and not model.measures:
        return []
    findings: list[Finding] = []
    findings.extend(_check_metric_contracts(ctx, model))
    findings.extend(_check_tmdl_dax(ctx, model))
    findings.extend(_check_binding_maps(ctx, model))
    return findings
