"""AL1 -- assumption-ledger rule.

A metric contract records an UNRESOLVED human judgment call through the existing
open-state mechanism the template defines: ``readiness.status == "blocked"`` with a
non-empty ``readiness.blocking_reasons[]``. Separately, a contract binds a metric to a
gold column via ``binds_to.gold_table`` + ``binds_to.columns``.

AL1 ERRORs when BOTH coexist on the same contract: a self-declared open question
(``blocked`` + reasons) presented atop a SETTLED gold binding (a real ``gold.<...>``
table -- not the ``<...>`` placeholder -- AND a non-empty, non-placeholder ``columns``
list). That combination is dishonest: the binding claims the metric is wired while the
readiness block says a blocking assumption is still open. An honest blocked DRAFT
(binding still a placeholder) does not fire; a ``pass`` contract does not fire.

AL1 is the CHECK half of the Per-Contract Ambiguity Decision Ledger (spec 058) but
depends on it for nothing -- it keys on the EXISTING readiness/binding fields, so it has
a real convention to check on day one and a genuine zero-findings baseline on ``main``
(all committed contracts are ``status: pass``). AL1 NEVER resolves the assumption
(Principle V -- that is a human ruling it cannot clear); it only surfaces the
contradiction. It is a pure static YAML read (lazy ``import yaml`` inside the function,
keeping the retail-check core stdlib-only per B1/B3), never executes, opens no
connection, and modifies no contract.

Ratified rulings (spec 059 ## Clarifications): C1 = marker is the existing ``blocked`` +
``blocking_reasons[]`` (no new token); C2 = the settled-binding trigger is a
non-placeholder ``gold_table`` AND a non-empty non-placeholder ``columns``; C3 =
standalone (not gated on the unshipped Ambiguity-Ledger define half). Scan per-table
``mappings/*/metrics/*.yaml`` only; exclude the generic template + tests/ fixtures; a
tracked-but-unreadable contract fails loud.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

_METRICS_RE = re.compile(r"^mappings/[^/]+/metrics/[^/]+\.ya?ml$")
_TEMPLATE_PATH = "templates/metric-contract.yaml"
_PLACEHOLDER_RE = re.compile(r"<[^>]*>")


def _iter_contracts(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if _METRICS_RE.match(p) and p != _TEMPLATE_PATH and not is_test_path(p)
    ]


def _is_placeholder(value: object) -> bool:
    """True if a scalar is an angle-bracket placeholder like ``gold.<fact_or_dim>``."""
    return isinstance(value, str) and bool(_PLACEHOLDER_RE.search(value))


def _has_unresolved_marker(contract: dict) -> bool:
    readiness = contract.get("readiness") or {}
    if not isinstance(readiness, dict):
        return False
    status = readiness.get("status")
    reasons = readiness.get("blocking_reasons") or []
    return status == "blocked" and isinstance(reasons, list) and len(reasons) > 0


def _has_settled_binding(contract: dict) -> bool:
    binds_to = contract.get("binds_to") or {}
    if not isinstance(binds_to, dict):
        return False
    gold_table = binds_to.get("gold_table")
    columns = binds_to.get("columns") or []
    if not isinstance(gold_table, str) or not gold_table or _is_placeholder(gold_table):
        return False
    if not isinstance(columns, list) or not columns:
        return False
    # At least one real, non-placeholder column.
    return any(isinstance(c, str) and c and not _is_placeholder(c) for c in columns)


@register(
    "AL1",
    "Metric contract with an unresolved assumption also carries a settled binding",
)
def check_unresolved_assumptions(ctx: RuleContext) -> Iterable[Finding]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    findings: list[Finding] = []
    for rel in sorted(_iter_contracts(ctx)):
        try:
            raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
            contract = yaml.safe_load(raw)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            findings.append(
                Finding(
                    rule_id="AL1",
                    severity=Severity.ERROR,
                    message=f"could not read/parse metric contract: {exc}",
                    locator=rel,
                )
            )
            continue

        if not isinstance(contract, dict):
            continue

        if _has_unresolved_marker(contract) and _has_settled_binding(contract):
            findings.append(
                Finding(
                    rule_id="AL1",
                    severity=Severity.ERROR,
                    message=(
                        "metric contract records an unresolved assumption "
                        "(readiness.status blocked with blocking_reasons) yet carries "
                        "a settled gold binding -- resolve the assumption or revert "
                        "binding to a placeholder; the agent cannot clear the "
                        "assumption (Principle V)"
                    ),
                    locator=rel,
                )
            )
    return findings
