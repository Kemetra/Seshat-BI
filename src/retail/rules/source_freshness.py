"""HR4 -- source freshness declaration presence/well-formedness gate.

What HR4 does (STATIC, fail-closed, presence-GATED):
  Scans every filled per-table mapping-gate artifact
  (``mappings/<table>/source-map.yaml``) for the optional
  ``meta.freshness`` block -- the human-declared SLA a data owner records for
  a source: ``expected_cadence`` (how often new data is expected to land) and
  ``max_staleness`` (the longest tolerable gap before the source counts as
  stale). See ``specs/090-source-freshness-gate/spec.md`` and
  ``data-model.md`` for the full rationale.

  Presence is OPTIONAL; well-formedness is NOT (the load-bearing distinction
  this rule encodes):

  - ``meta.freshness`` entirely ABSENT on a filled map -> NO Finding. Whether
    the block becomes mandatory (retroactively or going forward) is the OPEN
    Q-FR014-SCOPE governance ruling (FR-014, Principle V) -- this rule MUST
    NOT settle that ruling by treating absence as an error. [PENDING OWNER
    RULING: Q-FR014-SCOPE, FR-014 -- see spec.md Clarifications.]
  - ``meta.freshness`` PRESENT but not a YAML mapping -> one ERROR Finding
    with the whole-block locator.
  - ``meta.freshness`` PRESENT as a mapping but ``expected_cadence`` and/or
    ``max_staleness`` is missing, blank/whitespace-only, or does not match
    the recognized grammar below -> one ERROR Finding per offending field,
    naming the table, the field, and the offending raw value when present.
  - ``meta.freshness`` PRESENT with both sub-keys well-formed -> NO Finding.

  Recognized grammar (Clarification C1/C2, small + generic, no domain value
  inlined -- Principle VII):
  - ``expected_cadence``: closed enum, case-insensitive, trimmed --
    ``daily | weekly | monthly | quarterly | annual`` (``annually``/``yearly``
    accepted as synonyms of ``annual``) or ``one_time`` (``static`` accepted
    as a synonym), reserved for a genuinely one-time/static reference source.
  - ``max_staleness``: a magnitude-plus-unit duration matching
    ``^\\s*\\d+\\s*(hour|day|week|month|quarter|year)s?\\s*$``
    (case-insensitive), OR the literal sentinel ``n/a`` (case-insensitive),
    reserved for pairing with ``one_time``/``static``. The two fields are NOT
    cross-validated against each other -- each sub-key's well-formedness is
    checked independently (data-model.md "Why this shape").

  A table with no ``mappings/<table>/source-map.yaml`` at all (Stage 1,
  pre-mapping) is entirely OUT OF SCOPE -- HR4 never fires ahead of Stage 2
  (FR-005). ``templates/source-map.yaml`` itself is excluded by path
  (Clarification C3): its ``freshness`` sub-keys are placeholder schema
  documentation, not a real per-table declaration. Any path under ``tests/``
  is excluded via ``is_test_path`` (fixture exemption).

What HR4 NEVER does:
  - It NEVER computes, queries, or asserts an ACTUAL arrival time, an actual
    elapsed staleness duration, or a live pass/fail verdict against the
    declared SLA (Principle VIII -- static only). That live comparison is
    explicitly DEFERRED to a future live surface (most likely `retail
    validate`, spec 082); this module opens no database connection, makes no
    network call, and computes no latest-arrival-timestamp aggregate. Any
    future surface that reports the live comparison must mark it
    ``[PENDING LIVE FRESHNESS CHECK]`` with a non-pass status rather than a
    fabricated verdict (FR-006) -- this module itself never emits that
    marker because it never reports on live state at all (Clarification C4).
  - It NEVER emits a numeric confidence/health/maturity/freshness score or an
    "N of M" / completeness tally (hard rule #9, FR-007). Its output is a
    categorical Finding (present-and-well-formed vs. missing/malformed) only.
  - It NEVER re-decides, auto-fills, defaults, or fabricates a table's
    ``expected_cadence``/``max_staleness`` value on a human's behalf
    (Principle V, FR-002, FR-008); it reads and reports only.
  - It NEVER writes to ``source-map.yaml``, ``readiness-status.yaml``, or
    ``approvals[]`` (FR-008). Read-only, side-effect-free.
  - It NEVER decides Q-FR014-SCOPE (whether the block is mandatory,
    retroactive, or exempt for one-time sources) -- that is an OPEN,
    named-human governance ruling this rule does not settle by its
    presence-gated design (Principle V).
  - It NEVER touches missing-segment / date-spine completeness detection
    (the other half of PB-SQL-09, explicitly out of scope, FR-010) or the
    shape/semantic drift taxonomy owned by ``docs/readiness/source-drift.md``
    (FR-009) -- arrival-cadence staleness is a distinct signal from both.

Reads ``mappings/<table>/source-map.yaml`` only (lazy ``import yaml`` inside
the check function, keeping the retail-check core stdlib-only at module
scope, mirroring the AL1/rule_sf1 convention).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "HR4"

_MAP_PATH_RE = re.compile(r"^mappings/[^/]+/source-map\.yaml$")
_TEMPLATE_PATH = "templates/source-map.yaml"

_CADENCE_SYNONYMS = {
    "daily": "daily",
    "weekly": "weekly",
    "monthly": "monthly",
    "quarterly": "quarterly",
    "annual": "annual",
    "annually": "annual",
    "yearly": "annual",
    "one_time": "one_time",
    "static": "one_time",
}

_STALENESS_RE = re.compile(
    r"^\s*\d+\s*(hour|day|week|month|quarter|year)s?\s*$", re.IGNORECASE
)
_NA_SENTINEL = "n/a"


def _table_id_from_path(rel: str) -> str:
    # mappings/<table>/source-map.yaml -> <table>
    return rel.split("/", 2)[1]


def _iter_filled_maps(ctx: RuleContext) -> list[tuple[str, str]]:
    """Return [(table_id, rel_path), ...] for in-scope filled source-maps."""
    return [
        (_table_id_from_path(rel), rel)
        for rel in ctx.tracked_files
        if _MAP_PATH_RE.match(rel) and rel != _TEMPLATE_PATH and not is_test_path(rel)
    ]


def _cadence_ok(value: object) -> bool:
    if not isinstance(value, str):
        return False
    trimmed = value.strip()
    if not trimmed:
        return False
    return trimmed.lower() in _CADENCE_SYNONYMS


def _staleness_ok(value: object) -> bool:
    if not isinstance(value, str):
        return False
    trimmed = value.strip()
    if not trimmed:
        return False
    if trimmed.lower() == _NA_SENTINEL:
        return True
    return _STALENESS_RE.match(trimmed) is not None


def _blank_or_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _field_finding(table: str, rel: str, field: str, value: object) -> Finding:
    if _blank_or_missing(value):
        detail = "is missing or blank"
    else:
        detail = f"has an unrecognized value: {value!r}"
    return Finding(
        rule_id=RULE_ID,
        severity=Severity.ERROR,
        message=(
            f"table '{table}': meta.freshness.{field} {detail}; "
            "declare a well-formed value (human SLA judgment, Principle V -- "
            "this rule never fabricates one)"
        ),
        locator=f"{rel}:meta.freshness.{field}",
    )


def _check_one_table(table: str, rel: str, freshness: object) -> list[Finding]:
    if freshness is None:
        # Presence-gated: outright absence of the whole block is NOT an error.
        # [PENDING OWNER RULING: Q-FR014-SCOPE, FR-014] whether this becomes
        # mandatory (retroactively or going forward) is a named-human
        # governance decision this rule does not settle.
        return []

    if not isinstance(freshness, dict):
        return [
            Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"table '{table}': meta.freshness is present but is not a "
                    "mapping (expected expected_cadence/max_staleness sub-keys)"
                ),
                locator=f"{rel}:meta.freshness",
            )
        ]

    findings: list[Finding] = []
    cadence = freshness.get("expected_cadence")
    if not _cadence_ok(cadence):
        findings.append(_field_finding(table, rel, "expected_cadence", cadence))

    staleness = freshness.get("max_staleness")
    if not _staleness_ok(staleness):
        findings.append(_field_finding(table, rel, "max_staleness", staleness))

    return findings


@register(RULE_ID, "source freshness declaration")
def check_hr4(ctx: RuleContext) -> Iterable[Finding]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope

    findings: list[Finding] = []
    for table, rel in sorted(_iter_filled_maps(ctx), key=lambda t: t[1]):
        try:
            raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
            parsed = yaml.safe_load(raw)
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            # Unparseable/unreadable source-map.yaml is out of HR4's scope
            # entirely -- a different rule's concern (FR-005 spirit: HR4 only
            # evaluates maps it can confidently read as a filled instance).
            continue

        if not isinstance(parsed, dict):
            continue
        meta = parsed.get("meta")
        if not isinstance(meta, dict):
            continue

        freshness = meta.get("freshness")
        findings.extend(_check_one_table(table, rel, freshness))

    return findings
