"""HR6 -- RLS role contract binds to a real dim column.

What HR6 does (STATIC, fail-closed):
  Scans every committed ``mappings/<table>/roles/*.yaml`` file as a filled RLS
  role contract (a copy of ``templates/rls-role-contract.yaml``, mirroring the
  declare/bind/readiness shape of ``templates/metric-contract.yaml``). For each
  contract it checks that the declared ``filter: {gold_table, column}`` binding
  is internally well-formed AND that the column genuinely exists on a real,
  committed ``gold`` DIMENSION table -- i.e. the same "declared binding must
  resolve against committed structure" discipline F009's metric-contract check
  already applies to a measure's ``binds_to`` column, just for a role's filter
  instead of a metric's value.

  A role contract fails HR6 (one ``Severity.ERROR`` Finding per defect) when:
    - ``filter.column`` is missing, empty, or blank (whitespace-only).
    - ``filter.gold_table``/``filter.column`` cannot be resolved: the table is
      a ``silver.*``/``bronze.*`` object (Principle III boundary), or a
      ``gold.*`` table absent from the committed migration SQL entirely, or
      the table exists but the named column is not one of its columns.
    - ``filter.gold_table`` resolves to a committed ``gold`` table but that
      table is FACT-classified (``fct_*`` prefix) rather than DIMENSION-
      classified (``dim_*`` prefix) -- a role must filter a conformed
      dimension, not a fact, per the Kimball RLS pattern (spec Clarification
      C1: this is a hard ERROR, never a Severity.WARNING, even though a
      WARNING tier exists and was mechanically available -- a fact-bound role
      silently slipping past is exactly the leak-through direction this
      feature exists to close).
    - ``readiness.status`` is ``"pass"`` with an empty ``evidence[]`` (an
      unearned pass is a defect, mirroring the metric-contract precedent).
    - Two or more committed role contracts declare the same ``name`` (a
      case-sensitive exact duplicate; the template requires uniqueness).
  A contract that is unreadable, is not valid YAML, is not a mapping, or is
  missing its ``name``/``filter`` block entirely also fails closed with one
  ERROR Finding -- HR6 never silently skips a malformed file.

  A repo tree with ZERO committed ``mappings/*/roles/*.yaml`` files emits NO
  findings (Q-ZERO-ROLES, spec FR-010: whether every gold-backed model is
  REQUIRED to carry at least one governed role is an OPEN Principle-V
  governance ruling this rule's source deliberately does not resolve -- see
  the module-level "What HR6 NEVER does" note below). HR6 evaluates DECLARED
  contracts only; it never synthesizes a finding, a pass, or a block for the
  ABSENCE of a contract.

What HR6 NEVER does:
  - It never decides WHO should see WHAT: which roles a model needs, which
    viewers map to a role, or which column is the "correct" security boundary
    for a table. That is a named-human Principle V governance ruling recorded
    outside this rule's source (spec FR-013); this module contains no such
    answer, filled-in default, or recommendation.
  - It never rules on the OPEN Q-ZERO-ROLES question (spec FR-010): whether a
    table with zero role contracts should block, warn, or pass Semantic Model
    Ready is left for a named owner to decide; this rule's only committed
    behavior for that state is "emit nothing," which is not itself an answer
    to the policy question.
  - It never executes a filter expression, evaluates DAX/M, opens a database
    connection, or reads/previews a live PBIP "view as role" surface
    (Principle VIII, static only). A passing HR6 does NOT prove a role's
    filter actually restricts rows correctly at runtime; that live proof is
    explicitly deferred (a future live-validate surface, not this rule).
  - It never emits a numeric confidence/health/maturity score or an "N of M"
    completeness count (hard rule #9) -- readiness is the four explicit
    ``not_started | blocked | warning | pass`` statuses plus
    ``evidence[]``/``blocking_reasons[]`` only.
  - It never re-derives or second-guesses a table's grain/PK (that is the
    mapping-gate rules' concern) and it never reads or writes
    ``source-map.yaml``.
  - It never writes into ``readiness-status.yaml``'s
    ``semantic_model_ready.blocking_reasons[]`` itself -- that surfacing is
    the existing RS1/retail-semantic-check wiring's job (spec FR-011); HR6
    only emits the ``Finding`` that wiring already knows how to consume, the
    same way a D1-D11/G6 finding already blocks that stage.

Column extraction mirrors the existing static-only discipline in
``src/retail/sql.py`` (``iter_sql_files``, ``strip_sql_comments``): HR6 reads
committed ``warehouse/migrations/*.sql`` text, strips comments/strings so a
``gold.x`` mentioned inside one never leaks into the schema map, then extracts
each ``CREATE TABLE gold.<name> ( ... )`` body with a depth-aware comma split
(so a type like ``NUMERIC(10,2)`` never mis-splits) -- no live database
connection, ever.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, NamedTuple

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..sql import iter_sql_files, strip_sql_comments

if TYPE_CHECKING:
    from types import ModuleType

RULE_ID = "HR6"

_ROLE_CONTRACT_RE = re.compile(r"^mappings/[^/]+/roles/[^/]+\.ya?ml$")

_CREATE_TABLE_GOLD_RE = re.compile(
    r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?gold\.(\w+)\s*\(", re.IGNORECASE
)

# Leading tokens that mark a column-list entry as a table-level constraint
# clause, not a column definition -- its first word must not be mistaken for
# a column name.
_CONSTRAINT_LEAD_RE = re.compile(
    r"^\s*(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK|CONSTRAINT|EXCLUDE|LIKE)\b",
    re.IGNORECASE,
)

_COLUMN_NAME_RE = re.compile(r"^\s*(\w+)")


def _split_top_level_commas(body: str) -> list[str]:
    """Split a ``CREATE TABLE`` parenthesized body on depth-0 commas only.

    A type like ``NUMERIC(10,2)`` (or a nested ``CHECK (a > 0 AND b < 1)``)
    must not be split on its inner comma -- only commas outside any paren
    nesting separate column/constraint entries.
    """
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(body):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(body[start:i])
            start = i + 1
    parts.append(body[start:])
    return parts


def _find_matching_paren(text: str, open_idx: int) -> int:
    """Return the index of the ``)`` matching the ``(`` at ``open_idx``.

    Fails closed to ``len(text)`` (i.e. "consume to EOF") if unterminated --
    mirrors the fail-closed-to-EOF convention already used by
    ``sql.py``'s dollar-quote scanner.
    """
    depth = 0
    n = len(text)
    for i in range(open_idx, n):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        if depth == 0:
            return i
    return n


class _GoldTable:
    __slots__ = ("columns", "is_fact", "is_dim")

    def __init__(self, columns: frozenset[str], table_name: str) -> None:
        self.columns = columns
        self.is_fact = table_name.lower().startswith("fct_")
        self.is_dim = table_name.lower().startswith("dim_")


def _extract_columns(body: str) -> frozenset[str]:
    """Extract the lowercased column names from a ``CREATE TABLE`` body: split
    on depth-0 commas, skip empty entries and table-level constraint clauses
    (``PRIMARY KEY``, ``CONSTRAINT ...``, etc.), and take the leading word of
    each remaining entry as a column name."""
    columns: set[str] = set()
    for part in _split_top_level_commas(body):
        if not part.strip():
            continue
        if _CONSTRAINT_LEAD_RE.match(part):
            continue
        col_m = _COLUMN_NAME_RE.match(part)
        if col_m:
            columns.add(col_m.group(1).lower())
    return frozenset(columns)


def _read_gold_schema(ctx: RuleContext) -> dict[str, _GoldTable]:
    """Static structure mapping ``gold.<table>`` -> its column set + fact/dim
    classification, read from committed ``warehouse/migrations/*.sql`` text
    only (Principle VIII -- no live database connection, ever).

    Classification uses the ``dim_``/``fct_`` table-name prefix convention
    already fixed by ``docs/conventions.md`` (spec Clarification C3) -- no new
    naming convention or metadata key is introduced.
    """
    schema: dict[str, _GoldTable] = {}
    for rel in iter_sql_files(ctx):
        if is_test_path(rel):
            continue
        try:
            raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except OSError:
            continue
        clean = strip_sql_comments(raw)
        for m in _CREATE_TABLE_GOLD_RE.finditer(clean):
            table_name = m.group(1)
            open_idx = m.end() - 1  # the "(" the regex matched
            close_idx = _find_matching_paren(clean, open_idx)
            body = clean[open_idx + 1 : close_idx]
            schema[f"gold.{table_name.lower()}"] = _GoldTable(
                _extract_columns(body), table_name
            )
    return schema


def _iter_role_contract_files(ctx: RuleContext) -> list[str]:
    """Repo-relative POSIX paths of committed ``mappings/*/roles/*.yaml``
    files, excluding committed test fixtures (mirrors the ``is_test_path``
    exemption every other file-scanning rule already follows)."""
    return sorted(
        p
        for p in ctx.tracked_files
        if _ROLE_CONTRACT_RE.match(p) and not is_test_path(p)
    )


def _err(rel: str, message: str) -> Finding:
    return Finding(
        rule_id=RULE_ID, severity=Severity.ERROR, message=message, locator=rel
    )


def _extract_declared_fields(
    rel: str, data: dict[object, object]
) -> tuple[list[Finding], str | None, str | None, str | None]:
    """Validate the declared ``name`` and ``filter: {gold_table, column}``
    shape of one role contract. Returns (findings, name, gold_table, column);
    each field is None when missing/blank/wrong-type (its shape defect already
    emitted as a Finding), so the binding/readiness checks can key off it."""
    findings: list[Finding] = []

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        findings.append(_err(rel, "role contract 'name' is missing, empty, or blank"))
        name = None

    filter_block = data.get("filter")
    if not isinstance(filter_block, dict):
        findings.append(
            _err(rel, "role contract 'filter' block is missing or not a mapping")
        )
        filter_block = {}

    gold_table = filter_block.get("gold_table")
    column = filter_block.get("column")

    role_label = name if name else "<unnamed role>"

    if not isinstance(column, str) or not column.strip():
        findings.append(
            _err(
                rel,
                f"role '{role_label}' filter.column is missing, empty, or blank",
            )
        )
        column = None

    if not isinstance(gold_table, str) or not gold_table.strip():
        findings.append(
            _err(
                rel,
                f"role '{role_label}' filter.gold_table is missing, empty, or blank",
            )
        )
        gold_table = None

    return findings, name, gold_table, column


class _Binding(NamedTuple):
    """The contract-derived binding fields checked against gold structure --
    bundled so ``_check_binding`` takes one cohesive binding plus the schema
    rather than four loose scalars."""

    rel: str
    role_label: str
    gold_table: str | None
    column: str | None


def _check_binding(
    binding: _Binding,
    schema: dict[str, _GoldTable],
) -> list[Finding]:
    """Resolve the declared ``filter.gold_table``/``filter.column`` binding
    against the committed gold structure. Fails closed with one ERROR per
    defect: a non-gold (silver/bronze) table, a gold table absent from the
    committed migrations, a fact-classified table, or a column not on the
    resolved table."""
    rel, role_label = binding.rel, binding.role_label
    gold_table = binding.gold_table
    if not gold_table:
        return []

    table_key = gold_table.strip().lower()
    if not table_key.startswith("gold."):
        return [
            _err(
                rel,
                f"role '{role_label}' filter.gold_table {gold_table!r} does not "
                "reference the gold schema (a silver/bronze binding is not "
                "allowed -- Principle III)",
            )
        ]

    table = schema.get(table_key)
    if table is None:
        return [
            _err(
                rel,
                f"role '{role_label}' filter.gold_table {gold_table!r} does "
                "not exist in the committed gold migration SQL",
            )
        ]

    return _resolved_table_findings(binding, table)


def _resolved_table_findings(binding: _Binding, table: _GoldTable) -> list[Finding]:
    """Fact/dim and column checks once the gold table has resolved. Appends the
    dim-classification defect before the column-absence defect (finding order
    is contractual)."""
    rel, role_label = binding.rel, binding.role_label
    gold_table, column = binding.gold_table, binding.column
    findings: list[Finding] = []
    if not table.is_dim:
        kind = "a fact" if table.is_fact else "neither a dim nor a fact"
        findings.append(
            _err(
                rel,
                f"role '{role_label}' filter.gold_table {gold_table!r} is "
                f"{kind} table; an RLS role must bind to a gold "
                "DIMENSION (dim_*) table, not a fact table",
            )
        )
    if column and column.strip().lower() not in table.columns:
        findings.append(
            _err(
                rel,
                f"role '{role_label}' filter.column {column!r} does not "
                f"exist on {gold_table!r} per the committed gold "
                "migration SQL",
            )
        )
    return findings


def _check_readiness(
    rel: str, role_label: str, data: dict[object, object]
) -> list[Finding]:
    """A ``readiness.status`` of ``"pass"`` with an empty ``evidence[]`` is an
    unearned pass -- one ERROR Finding (mirrors the metric-contract precedent).
    Any other readiness shape/status is a lifecycle state HR6 does not judge."""
    readiness = data.get("readiness")
    if not isinstance(readiness, dict):
        return []
    status = readiness.get("status")
    evidence = readiness.get("evidence")
    if status == "pass" and not evidence:
        return [
            _err(
                rel,
                f"role '{role_label}' readiness.status is 'pass' but "
                "evidence[] is empty; a pass requires non-empty evidence",
            )
        ]
    return []


def _check_one_contract(
    rel: str, data: object, schema: dict[str, _GoldTable]
) -> tuple[list[Finding], str | None]:
    """Check one parsed role-contract mapping. Returns (findings, name) where
    ``name`` is the declared role name (or None if absent/invalid) so the
    caller can separately check for duplicate names across files."""
    if not isinstance(data, dict):
        return [_err(rel, "role contract must be a YAML mapping")], None

    findings, name, gold_table, column = _extract_declared_fields(rel, data)
    role_label = name if name else "<unnamed role>"
    binding = _Binding(rel, role_label, gold_table, column)
    findings.extend(_check_binding(binding, schema))
    findings.extend(_check_readiness(rel, role_label, data))

    return findings, name


def _load_and_check(
    ctx: RuleContext, rel: str, schema: dict[str, _GoldTable], yaml: ModuleType
) -> tuple[list[Finding], str | None]:
    """Read, parse, and check one committed role-contract file. Returns
    (findings, name); ``name`` is None whenever the file cannot be read or is
    not valid YAML (fail-closed with one ERROR Finding), so a defective file
    never participates in the cross-file duplicate-name check. ``yaml`` is
    passed in (imported once by the caller) to keep the retail check import
    path stdlib-light -- PyYAML must not be pulled in at module import time."""
    try:
        raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [_err(rel, f"could not read role contract: {exc}")], None

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return [_err(rel, f"role contract is not valid YAML: {exc}")], None

    return _check_one_contract(rel, data, schema)


def _duplicate_name_findings(names_seen: dict[str, list[str]]) -> list[Finding]:
    """One ERROR Finding per file for every role ``name`` declared by two or
    more committed contracts (the template requires case-sensitive
    uniqueness)."""
    findings: list[Finding] = []
    for name, rels in names_seen.items():
        if len(rels) > 1:
            for rel in rels:
                findings.append(
                    _err(
                        rel,
                        f"role name {name!r} is declared by more than one "
                        f"committed role contract: {', '.join(sorted(rels))}",
                    )
                )
    return findings


@register(RULE_ID, "RLS role contract binds to a real dim column")
def check_rls_role_bindings(ctx: RuleContext) -> Iterable[Finding]:
    contract_files = _iter_role_contract_files(ctx)
    if not contract_files:
        # Q-ZERO-ROLES (spec FR-010): absence of any committed role contract
        # is an OPEN Principle-V governance question this rule does not
        # settle. HR6 evaluates declared contracts only -- it never
        # synthesizes a finding, a pass, or a block for their absence.
        return []

    import yaml  # lazy: keep retail check import path stdlib-light

    schema = _read_gold_schema(ctx)

    findings: list[Finding] = []
    names_seen: dict[str, list[str]] = {}

    for rel in contract_files:
        contract_findings, name = _load_and_check(ctx, rel, schema, yaml)
        findings.extend(contract_findings)
        if name:
            names_seen.setdefault(name, []).append(rel)

    findings.extend(_duplicate_name_findings(names_seen))

    return findings
