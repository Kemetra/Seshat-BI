"""Offline PBIR binding-resolution validator (#454).

Walks every JSON document under a report's ``definition/`` tree for bound field
references -- ``Column``/``Measure`` wrappers carrying an ``Expression ->
SourceRef`` and a ``Property`` (queryState projections, filters, sorts alike;
one recursive walker, no bucket enumeration) -- and resolves each
``Entity``+``Property`` pair against a symbol table built from the semantic
model's TMDL. Every unresolved binding is exactly one Power BI Desktop
"Something's wrong with one or more fields" error card caught BEFORE a human
opens Desktop.

WHY THIS IS A READ-ONLY CLI VERB (same precedent as ``pbir-validate-blueprint``)
--------------------------------------------------------------------------------
The delivery default for new capabilities is a SKILL, not a CLI verb (ratified
Option-B, ``docs/roadmap/decisions/cli-verbs-vs-skill-driven.md``). This module
is a CHECK SURFACE that POLICES what writers already produced -- the US7
compiler, pbi-cli scaffolding, or a human Desktop build -- exactly the narrow
exception R1/R2 and ``pbir-validate-blueprint`` established. Unlike that
validator it needs NO blueprint or binding map: the reported real-world case
(a Desktop-owned report over a Get-Data model) has neither, only the report
and model trees themselves.

READ-ONLY, GRANTS NO APPROVAL
--------------------------------------------------------------------------------
Opens nothing for write, never mutates the Decision Store, never sets a
readiness stage. ``BindingValidationResult.grants_approval`` is always False
and the shape carries no member that could ever flip it. Status vocabulary is
the shipped four-status subset (``pass`` / ``warning`` / ``blocked``), never a
numeric score.

RESOLUTION SEMANTICS
--------------------------------------------------------------------------------
- Case-insensitive: Power BI object names are case-insensitive; exact-case
  comparison would fabricate error cards Desktop never shows.
- ``SourceRef`` resolves directly (``{"Entity": e}``) or through the
  document-wide alias table collected from ``"From": [{"Name": n, "Entity": e}]``
  lists; an alias no ``From`` declaration defines is a NAMED blocker (#475) --
  Desktop shows an error card for it, so omitting the reference was a fail-open.
- Wrappers other than ``Column``/``Measure`` (``HierarchyLevel``, variations,
  conditional-formatting expressions) are out of scope for this increment.
- A wrapper is a DECLARED binding once it carries an ``Expression`` or a
  ``Property``. Such a wrapper must be classified or blocked; a visual carrying
  no wrapper at all is intentionally unbound (card, shape, text box) and stays
  silent. That distinction is what keeps "0 findings" honest without inventing
  findings for static visuals.
- A model column bound under a ``Measure`` wrapper (or vice versa) resolves --
  Desktop renders it "by luck" -- but is reported as a ``projection_kind``
  WARNING: the detection side of #456; the authoring fix lives in the
  generator, so the validator warns without blocking.

FAIL-CLOSED (the #453 lesson: never a silent "0 findings" pass over nothing)
--------------------------------------------------------------------------------
Zero visuals under the report, zero TMDL tables under the model, or ANY
unreadable/unparseable definition file is a ``blocked`` finding naming the
path -- not a skip. A validator that silently validates nothing gives false
comfort, which is the exact failure mode it exists to remove.

TMDL NOTE: a single ``model.tmdl`` may carry SEVERAL table blocks (Desktop
sometimes writes this). ``tmdl.parse_tmdl`` attributes every block in a file to
the FIRST table header, so this module splits column-0 ``table`` headers into
segments first and delegates each segment to ``parse_tmdl`` -- the shipped
parser is reused, never reimplemented.

No pbi-cli, no live Power BI, no network -- stdlib ``json``/``pathlib``/``re``/
``difflib`` plus the shipped TMDL parser.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator, NamedTuple

from .tmdl import parse_tmdl


class BindingFinding(NamedTuple):
    """One binding defect: evidence only, grants nothing."""

    dimension: str  # "unknown_entity" | "unresolved_field" | "projection_kind"
    #                 | "unparseable_json" | "unreadable_source"
    #                 | "unresolved_alias" | "malformed_binding"
    #                 | "unparseable_model_file"
    locator: str  # where (report-relative-ish path, or the offending dir)
    message: str  # human-readable statement naming entity/property/cause


class BindingValidationResult(NamedTuple):
    """The validator's verdict. Read-only evidence, never an approval grant --
    ``grants_approval`` is ALWAYS False; no member on this shape can flip it."""

    status: str  # "pass" | "warning" | "blocked"; worst finding rolls up
    unresolved: tuple[BindingFinding, ...]  # blocked-class findings
    kind_mismatches: tuple[BindingFinding, ...]  # warning-class (#456 shape)
    evidence: tuple[str, ...]
    grants_approval: bool = False


# --------------------------------------------------------------------------- #
# Model side: TMDL -> symbol table
# --------------------------------------------------------------------------- #


class _ModelTable(NamedTuple):
    name: str  # exact-case, for messages
    columns: dict[str, str]  # casefold -> exact-case
    measures: dict[str, str]


_TABLE_HEADER = re.compile(r"table\s+\S")


def _split_table_segments(text: str) -> list[str]:
    """Split one TMDL file into per-table texts at column-0 ``table`` headers.

    ``parse_tmdl`` reads a SINGLE-table file: on a multi-table ``model.tmdl``
    it would attribute every measure/column block to the first header. Files
    with no table header (``relationships.tmdl``, ``expressions.tmdl``) yield
    no segments.
    """
    lines = text.lstrip("﻿").splitlines()
    starts = [
        i
        for i, line in enumerate(lines)
        if line[:1] not in (" ", "\t") and _TABLE_HEADER.match(line.strip())
    ]
    return [
        "\n".join(lines[start : starts[idx + 1] if idx + 1 < len(starts) else None])
        for idx, start in enumerate(starts)
    ]


def _model_files(model_dir: Path) -> list[Path]:
    definition = model_dir / "definition"
    if not definition.is_dir():
        return []
    return sorted(definition.rglob("*.tmdl"))


def _unreadable_model_finding(tmdl_path: Path) -> BindingFinding:
    return BindingFinding(
        dimension="unreadable_source",
        locator=str(tmdl_path),
        message=(
            f"model definition file {tmdl_path.name} is unreadable -- "
            f"validation blocked (fail closed): an unread table file "
            f"would misreport its bindings as unknown entities"
        ),
    )


def _tables_in_text(text: str) -> Iterator[_ModelTable]:
    """Every parsed table in one TMDL file's text (multi-table tolerant)."""
    parsed_tables = (parse_tmdl(s) for s in _split_table_segments(text))
    for parsed in parsed_tables:
        if parsed is None:
            continue
        yield _ModelTable(
            name=parsed.name,
            columns={c.name.casefold(): c.name for c in parsed.columns},
            measures={m.name.casefold(): m.name for m in parsed.measures},
        )


def _in_tables_tree(model_dir: Path, tmdl_path: Path) -> bool:
    """True when ``tmdl_path`` lives under ``definition/tables/``.

    Only that tree is REQUIRED to yield a table symbol: ``model.tmdl``,
    ``relationships.tmdl``, ``expressions.tmdl`` and ``cultures/*.tmdl``
    legitimately declare no table, and blocking on those would fabricate
    findings for a well-formed model.
    """
    try:
        relative = tmdl_path.relative_to(model_dir / "definition")
    except ValueError:
        return False
    return relative.parts[:1] == ("tables",)


def _unparseable_model_finding(tmdl_path: Path) -> BindingFinding:
    return BindingFinding(
        dimension="unparseable_model_file",
        locator=str(tmdl_path),
        message=(
            f"table definition file {tmdl_path.name} produced no table symbol "
            f"-- an unparseable file under definition/tables/ silently shrinks "
            f"the model symbol table and turns real bindings into false unknown "
            f"entities; validation blocked (fail closed)"
        ),
    )


def _model_symbol_table(
    model_dir: Path,
) -> tuple[dict[str, _ModelTable], list[BindingFinding]]:
    """``{casefold(table): _ModelTable}`` from every ``definition/**/*.tmdl``.

    An UNREADABLE tmdl file is a blocker, not a skip: silently shrinking the
    symbol table would turn every binding into that file's tables into a false
    ``unknown_entity`` -- a validator must fail closed, never guess smaller.

    Same reasoning for a file under ``definition/tables/`` that parses to NO
    table symbol (#475): it is the table-definition tree, so a file there that
    yields nothing is a parse defect, not an absence.
    """
    tables: dict[str, _ModelTable] = {}
    blockers: list[BindingFinding] = []
    for tmdl_path in _model_files(model_dir):
        try:
            text = tmdl_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            blockers.append(_unreadable_model_finding(tmdl_path))
            continue
        parsed = list(_tables_in_text(text))
        if not parsed and _in_tables_tree(model_dir, tmdl_path):
            blockers.append(_unparseable_model_finding(tmdl_path))
            continue
        tables.update({table.name.casefold(): table for table in parsed})
    return tables, blockers


# --------------------------------------------------------------------------- #
# Report side: definition JSON -> bound field references
# --------------------------------------------------------------------------- #


class _FieldRef(NamedTuple):
    path: Path
    kind: str  # "Column" | "Measure" (the wrapper key)
    entity: str  # resolved entity name (direct or via From-alias)
    prop: str


def _children(node: Any) -> Iterable[Any]:
    if isinstance(node, dict):
        return node.values()
    return node if isinstance(node, list) else ()


def _iter_dicts(node: Any) -> Iterator[dict[str, Any]]:
    """Every dict anywhere in a parsed JSON document, depth-first."""
    if isinstance(node, dict):
        yield node
    for child in _children(node):
        yield from _iter_dicts(child)


def _from_entries(doc: Any) -> Iterator[Any]:
    """Every entry of every ``"From"`` declaration list, document-wide."""
    for node in _iter_dicts(doc):
        entries = node.get("From")
        if isinstance(entries, list):
            yield from entries


def _alias_pair(entry: Any) -> tuple[str, str] | None:
    """One ``(alias, entity)`` from a ``From`` entry, or ``None`` if malformed."""
    if not isinstance(entry, dict):
        return None
    name, entity = entry.get("Name"), entry.get("Entity")
    if isinstance(name, str) and isinstance(entity, str):
        return name, entity
    return None


def _collect_aliases(doc: Any) -> dict[str, str]:
    """Document-wide ``{alias: entity}`` from every ``"From"`` declaration list."""
    pairs = (_alias_pair(entry) for entry in _from_entries(doc))
    return dict(pair for pair in pairs if pair is not None)


def _declares_binding(inner: Any) -> bool:
    """True when a ``Column``/``Measure`` wrapper CLAIMS to be a field reference.

    The distinction #475 turns on: a visual carrying no such wrapper is
    intentionally unbound (card, shape, text box) and must stay silent, while a
    wrapper that carries an ``Expression`` or a ``Property`` is a DECLARED
    binding -- so failing to classify it is a defect, not an absent reference.
    """
    return isinstance(inner, dict) and ("Expression" in inner or "Property" in inner)


def _malformed_binding_finding(kind: str, detail: str, locator: str) -> BindingFinding:
    return BindingFinding(
        dimension="malformed_binding",
        locator=locator,
        message=(
            f"a {kind} projection is declared but cannot be classified: {detail} "
            f"-- a declared binding that cannot be resolved is a defect, not an "
            f"absent reference; validation blocked (fail closed)"
        ),
    )


def _unresolved_alias_finding(
    kind: str, alias: str, prop: str, locator: str
) -> BindingFinding:
    return BindingFinding(
        dimension="unresolved_alias",
        locator=locator,
        message=(
            f"{kind} projection {prop!r} sources its entity through alias "
            f"{alias!r}, which no From declaration in this document defines -- "
            f"Desktop shows an error card for it; validation blocked"
        ),
    )


class _WrapperContext(NamedTuple):
    """Where a wrapper was found: the wrapper key, its file, and its locator.

    Threaded as ONE value so the classifier and its helpers stay inside the
    argument budget while every finding can still name its exact origin.
    """

    kind: str
    path: Path
    locator: str


def _grounded_ref(
    context: _WrapperContext,
    prop: str,
    source_ref: dict[str, Any],
    aliases: dict[str, str],
) -> tuple[_FieldRef | None, BindingFinding | None]:
    """Ground a well-formed ``SourceRef`` on its entity, direct or by alias."""
    entity = source_ref.get("Entity")
    if isinstance(entity, str):
        return _field_ref(context, entity, prop), None
    alias = source_ref.get("Source")
    if not isinstance(alias, str):
        return None, _malformed_binding_finding(
            context.kind,
            f"{prop!r} names neither SourceRef.Entity nor SourceRef.Source",
            context.locator,
        )
    resolved = aliases.get(alias)
    if resolved is None:
        return None, _unresolved_alias_finding(
            context.kind, alias, prop, context.locator
        )
    return _field_ref(context, resolved, prop), None


def _field_ref(context: _WrapperContext, entity: str, prop: str) -> _FieldRef:
    return _FieldRef(path=context.path, kind=context.kind, entity=entity, prop=prop)


def _classified_ref(
    node: dict[str, Any],
    context: _WrapperContext,
    aliases: dict[str, str],
) -> tuple[_FieldRef | None, BindingFinding | None]:
    """``(reference, defect)`` for one node's wrapper of ``context.kind``.

    Both ``None`` only when the node declares no binding of that kind at all;
    a declared binding always yields one or the other -- never silence.
    """
    inner = node.get(context.kind)
    if not _declares_binding(inner):
        return None, None
    assert isinstance(inner, dict)
    prop = inner.get("Property")
    if not isinstance(prop, str):
        return None, _malformed_binding_finding(
            context.kind, "it carries no string Property", context.locator
        )
    expression = inner.get("Expression")
    if not isinstance(expression, dict):
        return None, _malformed_binding_finding(
            context.kind, f"{prop!r} carries no Expression object", context.locator
        )
    source_ref = expression.get("SourceRef")
    if not isinstance(source_ref, dict):
        return None, _malformed_binding_finding(
            context.kind, f"{prop!r} has no Expression.SourceRef", context.locator
        )
    return _grounded_ref(context, prop, source_ref, aliases)


def _refs_in_doc(
    doc: Any, path: Path, locator: str
) -> tuple[list[_FieldRef], list[BindingFinding]]:
    """Every ``Column``/``Measure`` reference in one doc, plus every declared
    binding that could not be classified (each a blocked-class finding)."""
    aliases = _collect_aliases(doc)
    refs: list[_FieldRef] = []
    defects: list[BindingFinding] = []
    for node in _iter_dicts(doc):
        for kind in ("Column", "Measure"):
            context = _WrapperContext(kind=kind, path=path, locator=locator)
            ref, defect = _classified_ref(node, context, aliases)
            if ref is not None:
                refs.append(ref)
            elif defect is not None:
                defects.append(defect)
    return refs, defects


def _rel_locator(base_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base_dir.parent))
    except ValueError:
        return str(path)


def _walk_report(
    report_dir: Path,
) -> tuple[list[_FieldRef], list[BindingFinding]]:
    """All field references + fail-closed blockers across ``definition/**/*.json``.

    A corrupt or unreadable definition JSON is a blocker, not a skip: a broken
    ``visual.json`` is itself an error-card source, and silently skipping it
    would be the #453 fail-open pattern all over again. A declared binding that
    cannot be classified joins those blockers for the same reason (#475).
    """
    refs: list[_FieldRef] = []
    blockers: list[BindingFinding] = []
    definition = report_dir / "definition"
    if not definition.is_dir():
        return refs, blockers
    for json_path in sorted(definition.rglob("*.json")):
        locator = _rel_locator(report_dir, json_path)
        doc, blocker = _load_definition_doc(json_path, locator)
        if blocker is not None:
            blockers.append(blocker)
            continue
        found, defects = _refs_in_doc(doc, json_path, locator)
        refs.extend(found)
        blockers.extend(defects)
    return refs, blockers


def _load_definition_doc(
    json_path: Path, locator: str
) -> tuple[Any, BindingFinding | None]:
    """One definition JSON parsed, or the fail-closed blocker naming it."""
    try:
        text = json_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None, BindingFinding(
            dimension="unreadable_source",
            locator=locator,
            message=(
                "report definition file is unreadable -- "
                "validation blocked (fail closed)"
            ),
        )
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, BindingFinding(
            dimension="unparseable_json",
            locator=locator,
            message=(
                f"report definition file is not valid JSON ({exc.msg}, "
                f"line {exc.lineno}) -- a corrupt definition is itself "
                f"an error-card source; validation blocked (fail closed)"
            ),
        )


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #


def _dedupe(refs: list[_FieldRef]) -> list[_FieldRef]:
    seen: set[tuple[Path, str, str, str]] = set()
    out: list[_FieldRef] = []
    for ref in refs:
        key = (ref.path, ref.kind, ref.entity.casefold(), ref.prop.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append(ref)
    return out


def _unresolved_field_finding(
    ref: _FieldRef, table: _ModelTable, locator: str
) -> BindingFinding:
    """The blocked finding for a property missing from its entity, naming the
    nearest model field: a governed rename / PII mask (the ex-2 defect --
    ``person_name`` vs the gold model's ``staff_name_masked``) is the common
    cause, and the near-match makes it visible without opening Desktop."""
    candidates = [*table.columns.values(), *table.measures.values()]
    near = difflib.get_close_matches(ref.prop, candidates, n=1)
    hint = f"; nearest model field: {near[0]!r}" if near else ""
    return BindingFinding(
        dimension="unresolved_field",
        locator=locator,
        message=(
            f"{ref.entity}[{ref.prop}] is bound in the report but {ref.prop!r} "
            f"is not a column or measure on model table {table.name!r}{hint} "
            f"-- a governed rename or PII mask is the common cause"
        ),
    )


def _kind_mismatch_finding(
    ref: _FieldRef, table: _ModelTable, locator: str
) -> BindingFinding:
    actual = "COLUMN" if ref.kind == "Measure" else "MEASURE"
    wanted = "Column" if ref.kind == "Measure" else "Measure"
    return BindingFinding(
        dimension="projection_kind",
        locator=locator,
        message=(
            f"{ref.entity}[{ref.prop}] is bound as a {ref.kind} projection but "
            f"is a model {actual} on {table.name!r} -- emit a {wanted} "
            f"projection instead (renders by luck; semantically wrong, #456)"
        ),
    )


def _unknown_entity_finding(ref: _FieldRef, locator: str) -> BindingFinding:
    return BindingFinding(
        dimension="unknown_entity",
        locator=locator,
        message=(
            f"field reference {ref.entity}[{ref.prop}] names entity "
            f"{ref.entity!r}, which is not a table in the model"
        ),
    )


def _kind_conflicts(kind: str, is_column: bool, is_measure: bool) -> bool:
    """True when the wrapper kind contradicts what the property actually is --
    a column wrapped as ``Measure`` or a measure wrapped as ``Column``."""
    if kind == "Measure":
        return is_column and not is_measure
    return is_measure and not is_column


def _resolve_ref(
    ref: _FieldRef,
    tables: dict[str, _ModelTable],
    report_dir: Path,
) -> tuple[BindingFinding | None, BindingFinding | None]:
    """``(blocked_finding, warning_finding)`` for one reference; both ``None``
    when the binding resolves cleanly with the right projection kind."""
    locator = _rel_locator(report_dir, ref.path)
    table = tables.get(ref.entity.casefold())
    if table is None:
        return _unknown_entity_finding(ref, locator), None
    prop_key = ref.prop.casefold()
    is_column = prop_key in table.columns
    is_measure = prop_key in table.measures
    if not is_column and not is_measure:
        return _unresolved_field_finding(ref, table, locator), None
    if _kind_conflicts(ref.kind, is_column, is_measure):
        return None, _kind_mismatch_finding(ref, table, locator)
    return None, None


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #


def _fail_closed_blockers(
    report_dir: Path,
    model_dir: Path,
    tables: dict[str, _ModelTable],
) -> list[BindingFinding]:
    """The "nothing to validate" blockers: zero visuals or zero model tables is
    an ERROR naming the path, never a vacuous pass (the #453 lesson)."""
    blockers: list[BindingFinding] = []
    visuals = sorted(
        (report_dir / "definition" / "pages").glob("*/visuals/*/visual.json")
    )
    if not visuals:
        blockers.append(
            BindingFinding(
                dimension="unreadable_source",
                locator=str(report_dir),
                message=(
                    f"no visuals found under {report_dir}/definition/pages -- "
                    f"nothing to validate (fail closed); check the --report path"
                ),
            )
        )
    if not tables:
        blockers.append(
            BindingFinding(
                dimension="unreadable_source",
                locator=str(model_dir),
                message=(
                    f"no TMDL table definitions found under {model_dir}/definition "
                    f"-- nothing to resolve against (fail closed); check the "
                    f"--model path"
                ),
            )
        )
    return blockers


def validate_bindings(*, report_dir: Path, model_dir: Path) -> BindingValidationResult:
    """Resolve every bound field reference in the report against the model.

    READ-ONLY: opens nothing for write, never mutates the Decision Store,
    never sets a readiness stage. Returns evidence + findings only --
    ``grants_approval`` is always False.
    """
    report_dir = Path(report_dir)
    model_dir = Path(model_dir)

    tables, model_blockers = _model_symbol_table(model_dir)
    refs, report_blockers = _walk_report(report_dir)
    blockers = [
        *_fail_closed_blockers(report_dir, model_dir, tables),
        *model_blockers,
        *report_blockers,
    ]

    deduped = _dedupe(refs)
    # An empty model already blocked; don't cascade per-ref unknown_entity noise.
    resolved, kind_mismatches = (
        _resolve_all(deduped, tables, report_dir) if tables else ([], [])
    )
    unresolved = [*blockers, *resolved]

    evidence = (
        f"PBIR report dir: {report_dir}",
        f"semantic model dir: {model_dir}",
        f"{len(deduped)} field reference(s) checked against "
        f"{len(tables)} model table(s)",
    )
    return BindingValidationResult(
        status=_rollup_status(unresolved, kind_mismatches),
        unresolved=tuple(unresolved),
        kind_mismatches=tuple(kind_mismatches),
        evidence=evidence,
        grants_approval=False,
    )


def _resolve_all(
    refs: list[_FieldRef],
    tables: dict[str, _ModelTable],
    report_dir: Path,
) -> tuple[list[BindingFinding], list[BindingFinding]]:
    """``(blocked, warnings)`` across all references."""
    blocked: list[BindingFinding] = []
    warnings: list[BindingFinding] = []
    for ref in refs:
        block, warn = _resolve_ref(ref, tables, report_dir)
        blocked.extend([block] if block is not None else [])
        warnings.extend([warn] if warn is not None else [])
    return blocked, warnings


def _rollup_status(
    unresolved: list[BindingFinding], kind_mismatches: list[BindingFinding]
) -> str:
    """Worst-first roll-up: any blocked-class finding blocks; kind mismatches
    alone warn; a clean resolution is ``pass``."""
    if unresolved:
        return "blocked"
    return "warning" if kind_mismatches else "pass"


def pbir_validate_bindings_main(args: object) -> int:
    """CLI entry: ``seshat pbir-validate-bindings``. Read-only: prints the
    resolution report to stdout and exits non-zero on any blocked finding --
    it never writes a file and never grants any readiness stage."""
    result = validate_bindings(
        report_dir=Path(args.report),  # type: ignore[attr-defined]
        model_dir=Path(args.model),  # type: ignore[attr-defined]
    )
    print(f"status: {result.status}")
    for finding in result.unresolved:
        print(
            f"[unresolved] {finding.dimension}: {finding.message} ({finding.locator})"
        )
    for finding in result.kind_mismatches:
        print(f"[kind] {finding.dimension}: {finding.message} ({finding.locator})")
    for line in result.evidence:
        print(f"evidence: {line}")
    print(
        "note: this is a read-only validation report; it grants no approval "
        "and never sets a readiness stage."
    )
    # Name the boundary rather than letting a clean report imply more than it
    # checked: bindings resolving says nothing about whether the TMDL parses or
    # whether Desktop can load the model (issue #494).
    print(
        "scope: checks BINDINGS only -- that each bound field resolves to a "
        "declared measure/column. It does NOT verify TMDL syntax or that "
        "Desktop can load the model; a syntax defect can pass this check."
    )
    # Point at the one TMDL mistake that IS checkable headlessly, without
    # implying the pair closes the gap -- neither is a TMDL syntax validator.
    print(
        "see also: `seshat tmdl-doc-comment-lint` checks ONE TMDL rule (a /// "
        "block must attach to a declaration). It is not a syntax validator "
        "either; TMDL loadability stays unverified."
    )
    return 1 if result.status == "blocked" else 0
