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
    _child = re.compile(r"^\t(column|measure|partition|annotation|hierarchy)\b")
    for line in text.splitlines():
        stripped_lead = re.match(r"^\tmeasure\s+.*=", line)
        if stripped_lead:
            in_measure = True
            out.append(line)
            continue
        if in_measure:
            # a new table-child decl (or a non-indented line) ends the measure block
            if _child.match(line) or (
                line and not line.startswith("\t\t") and not line.startswith("\t\t\t")
            ):
                # a continuation of the DAX is indented deeper than the decl; a
                # sibling decl at one-tab depth ends this measure.
                if _child.match(line):
                    in_measure = False
                    continue
            out.append(line)
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


def _check_metric_contracts(ctx: RuleContext, model: _Model) -> list[Finding]:
    """FR-003: binds_to.columns entries resolve to a column in the cited gold table."""
    import yaml  # lazy

    findings: list[Finding] = []
    for rel in sorted(ctx.tracked_files):
        if is_test_path(rel) or not _METRIC_RE.match(rel):
            continue
        text = _read(ctx, rel)
        if text is None:
            continue
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        binds = data.get("binds_to")
        if not isinstance(binds, dict):
            continue
        gold_table = binds.get("gold_table")
        cols = binds.get("columns")
        if not isinstance(gold_table, str) or not isinstance(cols, list):
            continue
        bare = _strip_table_prefix(gold_table)
        known = model.columns_by_bare.get(bare)
        if known is None:
            continue  # no TMDL for this table yet -> FR-007 no-op
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
        # resolve qualified 'table'[col] against that table's columns, bare [X]
        # against the model-wide measure set (skipping column names to avoid
        # flagging a bare [col] that is really a same-line measure ref target).
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
        # bare [Measure] refs: blank out qualified refs first so 'table'[col]'s
        # [col] is not re-read as a bare measure token.
        blanked = _QUALIFIED_REF.sub("''[]", text)
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


def _all_columns(model: _Model) -> set[str]:
    out: set[str] = set()
    for cols in model.columns_by_table.values():
        out |= cols
    return out


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
        seen: set[str] = set()
        # qualified dim[column]
        for qm in _QUALIFIED_REF.finditer(text):
            qtable, qcol = qm.group(1), qm.group(2)
            known = model.columns_by_table.get(qtable)
            if known is not None and qcol not in known and (qtable, qcol) not in seen:
                seen.add((qtable, qcol))
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        severity=Severity.ERROR,
                        message=(
                            f"dashboard binding references {qtable!r}[{qcol}], which "
                            "does not resolve to a committed column (orphaned)"
                        ),
                        locator=f"{rel}:{qcol}",
                    )
                )
        blanked = _QUALIFIED_REF.sub("''[]", text)
        for bm in _BARE_MEASURE_REF.finditer(blanked):
            ref = bm.group(1).strip()
            if not ref or ref in seen:
                continue
            if ref not in model.measures and ref not in all_cols:
                seen.add(ref)
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        severity=Severity.ERROR,
                        message=(
                            f"dashboard binding references [{ref}], which does not "
                            "resolve to any committed measure (orphaned)"
                        ),
                        locator=f"{rel}:{ref}",
                    )
                )
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
