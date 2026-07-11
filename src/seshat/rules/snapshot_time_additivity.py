"""HR5 -- snapshot fact measures declare time_additivity.

What HR5 does (STATIC, fail-closed):
  Scans committed per-table metric contracts under the generic glob
  ``mappings/*/metrics/*.yaml`` (excluding ``templates/metric-contract.yaml``
  and ``tests/`` fixtures -- the AL1/AD1 exemption seam). For each contract,
  it reads the EXISTING, human-authored ``ambiguities[]`` ledger list and
  looks for an entry whose ``id`` is the exact literal ``A10`` ("Inventory
  snapshot date" -- the settled knowledge-layer id for the snapshot-additivity
  trap, ``skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md``). A
  contract carrying an A10 entry is "snapshot-flagged"; HR5 then reads the
  contract's OPTIONAL ``time_additivity`` field and ERRORs when:

  - the contract is snapshot-flagged and ``time_additivity`` is ABSENT (the
    key is missing, or present as YAML null / empty string -- both collapse
    to the same "missing declaration" outcome); or
  - the contract is snapshot-flagged and ``time_additivity`` equals ``fully``
    (a snapshot-flagged contract can never validly declare full additivity
    over the date axis); or
  - ANY contract's ``time_additivity`` value is present but is not one of the
    closed vocabulary words ``fully`` / ``semi`` / ``non`` -- an exact,
    case-sensitive, untrimmed string match; any other value (a case/whitespace
    variant, free text, or a non-scalar YAML node such as a list/mapping) is
    out-of-vocabulary and ERRORs, regardless of whether the contract is
    snapshot-flagged.

  A contract that is NOT snapshot-flagged and carries no ``time_additivity``
  field emits nothing (the field is optional unless the ledger already
  flagged the trap); a contract that volunteers a valid value early is only
  validated, never required.

  Three distinct ERROR message classes exist (unreadable file; missing
  declaration; illegal ``fully``; unrecognized value) so a missing-field
  finding and an out-of-vocabulary finding are never confused with each
  other.

What HR5 NEVER does:
  - It never redefines, narrows, or restates what "semi-additive" or "fully
    additive" MEANS in business terms -- that vocabulary and its retail
    meaning belongs to
    ``skills/retail-kpi-knowledge/knowledge/kpi-additivity-and-grain.md``.
    ``time_additivity`` is a schema slot for a human to name an
    already-defined classification; HR5 validates the word chosen, it never
    chooses the word (Principle V).
  - It never decides whether a contract IS a snapshot fact. Its sole
    detection trigger is the pre-existing, human-authored A10 ambiguities-
    ledger entry; HR5 does not infer snapshot grain from a table/column name,
    and does not gate on the entry's ``decision_status`` (a `decided` A10
    entry still requires the declaration -- the two fields answer different
    questions).
  - It never reads or duplicates AD1's additivity-composition legality table
    or its define-layer prose corpus
    (``skills/retail-kpi-knowledge/contracts/*.md``,
    ``src/seshat/rules/additivity_consistency.py``). AD1's "additivity
    classification" is a whole-metric composition class (can this metric be
    validly summed from its stated parents/children); HR5's
    ``time_additivity`` is narrower and orthogonal -- one measure's behavior
    specifically when summed ACROSS DATES. The two rules may both fire on the
    same contract for unrelated reasons.
  - It never opens a database or network connection, executes DAX, or reads
    any PBIP/visual surface (Principle VIII -- static only).
  - It never emits a numeric score, confidence value, or threshold -- ERROR
    is categorical, never graded (hard rule #9).
  - It never advances a readiness stage or grants an approval (off-spine,
    exactly like AD1/AL1/AL2 -- it only returns findings via the
    ``retail check`` exit code).

Clones the AL1/AD1 scaffold named in spec 091's plan/tasks: lazy ``import
yaml`` inside the registered function (module stays stdlib-only at import
scope), the generic ``mappings/[^/]+/metrics/[^/]+\\.ya?ml`` glob, the
template + ``is_test_path(...)`` exemption, fail-loud on an unreadable file,
ERROR-only, never-resolves.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "HR5"

_METRICS_RE = re.compile(r"^mappings/[^/]+/metrics/[^/]+\.ya?ml$")
_TEMPLATE_PATH = "templates/metric-contract.yaml"

_A10_ID = "A10"
_VOCAB = {"fully", "semi", "non"}

# normalized time_additivity states
_ABSENT = "ABSENT"
_OUT_OF_VOCAB = "OUT_OF_VOCAB"


def _iter_contracts(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if _METRICS_RE.match(p) and p != _TEMPLATE_PATH and not is_test_path(p)
    ]


def _has_a10_entry(contract: dict) -> bool:
    """True iff ``ambiguities[]`` contains an entry whose ``id`` is EXACTLY
    the literal ``A10`` (case-sensitive, no substring/prefix match). Does
    NOT gate on ``decision_status`` -- a `decided` A10 entry still counts."""
    ambiguities = contract.get("ambiguities") or []
    if not isinstance(ambiguities, list):
        return False
    for entry in ambiguities:
        if isinstance(entry, dict) and entry.get("id") == _A10_ID:
            return True
    return False


def _normalize_time_additivity(contract: dict) -> str:
    """Return one of ``ABSENT`` / ``fully`` / ``semi`` / ``non`` /
    ``OUT_OF_VOCAB`` per the field's closed-vocabulary rules.

    - key entirely absent, YAML null, or empty string -> ``ABSENT``.
    - a non-scalar node (list/mapping) -> ``OUT_OF_VOCAB`` (read without
      raising -- an ``isinstance`` guard precedes any string comparison).
    - exact, case-sensitive, untrimmed match to ``fully``/``semi``/``non`` ->
      that word.
    - any other string (including a case/whitespace variant) ->
      ``OUT_OF_VOCAB``.
    """
    if "time_additivity" not in contract:
        return _ABSENT
    value = contract.get("time_additivity")
    if value is None:
        return _ABSENT
    if not isinstance(value, str):
        # non-scalar (list/mapping) or a non-string scalar (e.g. a number)
        return _OUT_OF_VOCAB
    if value == "":
        return _ABSENT
    if value in _VOCAB:
        return value
    return _OUT_OF_VOCAB


@register(RULE_ID, "snapshot fact measures declare time_additivity")
def check_snapshot_time_additivity(ctx: RuleContext) -> Iterable[Finding]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    findings: list[Finding] = []
    for rel in sorted(_iter_contracts(ctx)):
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

        has_a10 = _has_a10_entry(contract)
        state = _normalize_time_additivity(contract)

        if state == _OUT_OF_VOCAB:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        "unrecognized time_additivity value -- must be exactly "
                        "one of 'fully', 'semi', 'non' (case-sensitive, "
                        "untrimmed); the agent never infers or defaults a value"
                    ),
                    locator=rel,
                )
            )
            continue

        if not has_a10:
            # optional field, validated-only when volunteered; never required
            continue

        if state == _ABSENT:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        "missing time_additivity declaration on an "
                        "A10-flagged (snapshot) contract -- a human owner "
                        "must declare 'semi' or 'non' over the date axis"
                    ),
                    locator=rel,
                )
            )
        elif state == "fully":
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        "an A10-flagged (snapshot) contract cannot declare "
                        "time_additivity: fully -- a snapshot fact is never "
                        "fully additive over time"
                    ),
                    locator=rel,
                )
            )
        # state in {"semi", "non"}: valid declaration, no finding
    return findings
