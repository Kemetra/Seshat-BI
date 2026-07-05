"""HR11 -- summed measure inputs share a unit.

What HR11 does (STATIC, fail-closed):
  Scans every committed metric contract (``mappings/<table>/metrics/*.yaml``)
  whose ``binds_to.columns[]`` names two or more gold-facing column names.
  For each such contract, it resolves every bound column against the SAME
  table's committed ``mappings/<table>/source-map.yaml`` ``columns[]`` list --
  matching on ``columns[].rename_to`` (spec 103 Clarification Q4: the only
  literal join key already present in both committed artifacts; a
  ``binds_to.columns[]`` entry that names a ``derived_columns`` entry, which
  carries no ``unit``/``currency`` field at all, is therefore never
  resolvable and falls under the "cannot be resolved" path below rather than
  being silently treated as unit/currency-agnostic).

  For every bound column that DOES resolve, HR11 reads that source-map
  entry's declared ``unit`` and ``currency`` (verbatim, exact-string,
  case-sensitive -- no normalization, aliasing, or fuzzy-matching, e.g.
  ``"kg"`` vs ``"Kg"`` vs ``"kilogram"`` are distinct values). It then
  compares, independently on each axis, every NON-NULL declared value across
  the metric's resolved bound columns:

  - Two or more resolved bound columns declare a DIFFERENT, non-null
    ``unit``      -> one ``Severity.ERROR`` finding (FR-005).
  - Two or more resolved bound columns declare a DIFFERENT, non-null
    ``currency``  -> one ``Severity.ERROR`` finding (FR-006), independent of
    the unit check -- a metric may clash on unit, on currency, on both, or
    on neither.
  - A bound column cannot be resolved against the table's source-map
    ``columns[].rename_to`` list                    -> ``Severity.ERROR``
    (FR-010; mirrors HR6's "unresolvable column" treatment).
  - The table's ``source-map.yaml`` itself is missing or unreadable
    (OSError / UnicodeDecodeError / YAML parse error) -> ``Severity.ERROR``
    naming the missing/unreadable path (FR-010).

  A metric contract whose ``binds_to.columns[]`` lists fewer than two
  entries has nothing to compare and MUST NOT fire (FR-011) -- HR11 skips it
  entirely, silently.

  A null (absent/never-declared) unit or currency value is EXCLUDED from the
  comparison set on its own axis, never treated as "matches anything" and
  never treated as a mismatch against a declared value on the other side.
  This is the literal FR-005/FR-006 condition ("two or more ... different,
  non-null ... value") and is DELIBERATE, not an oversight: whether an
  undeclared unit/currency on one side of a multi-column bind should itself
  be a blocking finding, a warning, or a silent no-op is spec 103's FR-014,
  an explicit OPEN Principle-V/VI governance-policy question (retroactive
  enforcement strictness against mappings that predate this feature) that
  this module MUST NOT and does NOT resolve on its own authority. Do not
  "fix" the null-handling here to make it stricter or looser -- that is an
  owner ruling, not an implementation detail.

  HR11 also does NOT decide spec 103's other open question, FR-013: how to
  detect that a metric contract represents a "sum of its bound columns" when
  the optional ``definition.aggregation`` block is absent (the common case;
  the template documents that "a contract WITHOUT it behaves exactly as
  today"). HR11 deliberately SIDESTEPS this detection-scope question rather
  than picking a side: it never reads or branches on ``definition``,
  ``definition.aggregation``, or ``additive`` at all. Instead it treats "two
  or more bound columns whose declared units/currencies can be compared" as
  a claim worth checking regardless of what aggregation (sum, ratio,
  count_rows, ...) the contract ultimately computes -- a same-unit/currency
  mismatch across a metric's own bound inputs is suspicious information for
  a human reviewer even on a metric that turns out not to be a plain sum.
  This is intentionally the more permissive reading; it does not adopt
  either FR-013 candidate extreme (neither "only definition.aggregation ==
  sum is in scope" nor "any 2+-column bind IS a sum") because this module
  never asks "is this contract a sum" in the first place.

What HR11 NEVER does:
  - It MUST NOT convert, normalize, rescale, or re-express any unit or
    currency value, MUST NOT compute or embed a conversion rate or
    conversion factor, and MUST NOT emit a converted value or a suggested
    rate in any finding message (Scope Guard; spec 103 FR-008). Currency
    conversion rates and unit-conversion factors are an owner ruling
    (Principle V) entirely out of scope here.
  - It never opens a database connection, executes DAX/SQL, or reads a live
    Power BI/PBIP surface (Principle VIII, static-first) -- it reads only
    already-committed ``source-map.yaml`` and metric-contract YAML text.
  - It never decides a Principle-V judgment call: it does not rule on
    FR-013 (sum-detection scope) or FR-014 (undeclared-value enforcement
    posture), and it does not invent, guess, or default an answer to
    either -- a missing declaration surfaces as an explicit "not compared"
    state (FR-014) or an explicit "cannot resolve" ERROR (FR-010), never a
    silently assumed match.
  - It never cross-checks a metric contract's own top-level ``unit`` field
    against its bound columns' declared units (spec 103 Clarification Q3:
    that field is documentary only) -- HR11's comparison is strictly
    column-to-column agreement among ``binds_to.columns[]``.
  - It emits no numeric score, confidence value, or completeness count
    (hard rule #9) -- only a pass/fail ``Finding`` per violation.

Mirrors docs/readiness/semantic-model-ready.md's HR11 listing and the
templates/source-map.yaml / templates/metric-contract.yaml declaration shape
(spec 103-currency-unit-contract data-model.md). See AL1
(src/retail/rules/assumptions.py) for the sibling per-contract YAML-scan
pattern this module follows (lazy ``import yaml``, ``mappings/*/metrics/*``
glob, ``utf-8-sig`` read, fail-loud on parse error).
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "HR11"

_METRICS_RE = re.compile(r"^mappings/([^/]+)/metrics/[^/]+\.ya?ml$")
_METRIC_TEMPLATE_PATH = "templates/metric-contract.yaml"


def _iter_metric_contract_files(ctx: RuleContext) -> list[tuple[str, str]]:
    """Return ``(rel_path, table)`` for every committed, non-template,
    non-test-fixture metric contract."""
    found: list[tuple[str, str]] = []
    for rel in ctx.tracked_files:
        if rel == _METRIC_TEMPLATE_PATH or is_test_path(rel):
            continue
        m = _METRICS_RE.match(rel)
        if not m:
            continue
        found.append((rel, m.group(1)))
    return found


class _Unreadable:
    """Sentinel: the table's source-map.yaml is missing or unreadable."""


_UNREADABLE = _Unreadable()


def _read_source_map_columns(
    ctx: RuleContext, table: str
) -> dict[str, dict[str, object]] | _Unreadable:
    """Read ``mappings/<table>/source-map.yaml`` and return a mapping of
    ``rename_to -> {"unit": ..., "currency": ...}`` for every ``columns[]``
    entry. Returns the ``_UNREADABLE`` sentinel (never raises) when the file
    is absent, unreadable, or not valid YAML -- the caller turns that into
    an FR-010 finding instead of crashing the whole gate.
    """
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope

    rel = f"mappings/{table}/source-map.yaml"
    try:
        raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        doc = yaml.safe_load(raw)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return _UNREADABLE

    if not isinstance(doc, dict):
        return _UNREADABLE

    columns = doc.get("columns")
    if not isinstance(columns, list):
        return _UNREADABLE

    by_rename_to: dict[str, dict[str, object]] = {}
    for entry in columns:
        if not isinstance(entry, dict):
            continue
        rename_to = entry.get("rename_to")
        if not isinstance(rename_to, str) or not rename_to:
            continue
        by_rename_to[rename_to] = {
            "unit": entry.get("unit"),
            "currency": entry.get("currency"),
        }
    return by_rename_to


def _clashes(values: dict[str, object]) -> list[tuple[str, object]] | None:
    """Given ``{column_name: declared_value}``, return the
    ``[(column, value), ...]`` pairs (stable input order) when two or more
    DISTINCT, non-null values are present -- else ``None``. Null values are
    excluded from comparison entirely (FR-014 stays open; a null is never
    treated as matching or mismatching anything)."""
    declared = [(col, val) for col, val in values.items() if val is not None]
    distinct = {val for _, val in declared}
    if len(distinct) >= 2:
        return declared
    return None


def _fmt_pairs(pairs: list[tuple[str, object]]) -> str:
    return ", ".join(f"{col}={val!r}" for col, val in pairs)


@register(RULE_ID, "summed measure inputs share a unit")
def check_unit_currency_agreement(ctx: RuleContext) -> Iterable[Finding]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope

    findings: list[Finding] = []
    # Cache one read per table across multiple contracts naming the same table.
    source_map_cache: dict[str, dict[str, dict[str, object]] | _Unreadable] = {}

    for rel, table in sorted(_iter_metric_contract_files(ctx)):
        try:
            raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
            contract = yaml.safe_load(raw)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=f"could not read/parse metric contract: {exc}",
                    locator=rel,
                )
            )
            continue

        if not isinstance(contract, dict):
            continue

        binds_to = contract.get("binds_to") or {}
        if not isinstance(binds_to, dict):
            continue
        bound_columns = binds_to.get("columns")
        if not isinstance(bound_columns, list):
            continue
        # only real, non-empty string column names
        bound_columns = [c for c in bound_columns if isinstance(c, str) and c]
        if len(bound_columns) < 2:
            continue  # FR-011: nothing to compare, HR11 must not fire

        metric_name = contract.get("name") or rel

        if table not in source_map_cache:
            source_map_cache[table] = _read_source_map_columns(ctx, table)
        source_map = source_map_cache[table]

        if isinstance(source_map, _Unreadable):
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"metric {metric_name!r} binds {len(bound_columns)} columns "
                        f"but its table's source-map "
                        f"(mappings/{table}/source-map.yaml) is missing or "
                        f"unreadable -- cannot verify declared unit/currency "
                        f"agreement across the bound columns"
                    ),
                    locator=rel,
                )
            )
            continue

        units: dict[str, object] = {}
        currencies: dict[str, object] = {}
        unresolved: list[str] = []
        for col in bound_columns:
            entry = source_map.get(col)
            if entry is None:
                unresolved.append(col)
                continue
            units[col] = entry.get("unit")
            currencies[col] = entry.get("currency")

        if unresolved:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"metric {metric_name!r} binds_to.columns names "
                        f"{unresolved!r} which could not be resolved against "
                        f"mappings/{table}/source-map.yaml columns[].rename_to "
                        f"-- cannot verify declared unit/currency agreement"
                    ),
                    locator=rel,
                )
            )
            # still compare whatever DID resolve, below

        unit_clash = _clashes(units)
        if unit_clash is not None:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"metric {metric_name!r} binds columns with "
                        f"clashing declared units: {_fmt_pairs(unit_clash)} "
                        f"(mappings/{table}/source-map.yaml columns[].unit)"
                    ),
                    locator=rel,
                )
            )

        currency_clash = _clashes(currencies)
        if currency_clash is not None:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"metric {metric_name!r} binds columns with "
                        f"clashing declared currencies: "
                        f"{_fmt_pairs(currency_clash)} "
                        f"(mappings/{table}/source-map.yaml columns[].currency)"
                    ),
                    locator=rel,
                )
            )

    return findings
