"""AL2 -- cross-contract assumption-coherence rule.

Two metric contracts that bind to the SAME gold table may each record, in their
``ambiguities[]`` ledger, a DECIDED ruling for the same ambiguity code (A-code). If
those two decided rulings disagree, the gold table carries two contradictory settled
answers to the same question -- a coherence defect a reader of one contract would never
see. AL2 ERRORs on that contradiction.

Ratified build defaults -- provenance note: these were hand-ratified at the PR #129
adversarial review (commit cc606b8, "AL2 ... (067, H2)"); AL2 was hand-built, NOT
spec-driven. There is NO committed spec covering AL2. The bare "067" tag in the commit
matches neither committed 067 dir (specs/067-bi-python-cleaning-artifacts,
specs/067-seed-route-honesty-rule -- neither is about assumption-coherence). This is
acknowledged provenance debt: the defaults below (C1/C2/DEC-1) are honest but have no
committed spec backing them.
- C1 -- grouping key is ``binds_to.gold_table`` (non-placeholder); a missing or
  ``<...>`` placeholder gold_table excludes the contract from grouping.
- C2 -- a contradiction is >= 2 DISTINCT decided rulings for one code within a group,
  compared by whitespace-normalized, case-insensitive ``ruling`` text. Only
  ``decision_status == "decided"`` entries with a non-empty ``ruling`` contribute;
  ``undecided``/absent contributes nothing (decided-vs-undecided is NOT a conflict).
  No semantic interpretation -- normalized-text inequality only.
- DEC-1 -- the rule id ``AL2`` + title are author-supplied (the workflow does not
  invent rule intent).

AL2 keys on EXISTING fields (``binds_to.gold_table``, ``ambiguities[]``), so it has a
real convention to check on day one and a genuine zero-findings baseline on ``main``
(no committed contract carries a decided ``ambiguities[]`` entry today). It NEVER
resolves or reconciles a ruling (Principle V -- that is a human judgment); it only
surfaces the contradiction. Pure static YAML read (lazy ``import yaml`` inside the
function, keeping the retail-check core stdlib-only per B1/B3); never executes, opens no
connection, modifies no contract. Scans per-table ``mappings/*/metrics/*.yaml`` only,
excluding the generic template + ``tests/`` fixtures; a tracked-but-unreadable contract
fails loud.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

_METRICS_RE = re.compile(r"^mappings/[^/]+/metrics/[^/]+\.ya?ml$")
_TEMPLATE_PATH = "templates/metric-contract.yaml"
_PLACEHOLDER_RE = re.compile(r"<[^>]*>")

RULE_ID = "AL2"


def _iter_contracts(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if _METRICS_RE.match(p) and p != _TEMPLATE_PATH and not is_test_path(p)
    ]


def _is_placeholder(value: object) -> bool:
    """True if a scalar is an angle-bracket placeholder like ``gold.<fact_or_dim>``."""
    return isinstance(value, str) and bool(_PLACEHOLDER_RE.search(value))


def _group_key(contract: dict) -> str | None:
    """The non-placeholder ``binds_to.gold_table`` grouping key, or None (excluded)."""
    binds_to = contract.get("binds_to") or {}
    if not isinstance(binds_to, dict):
        return None
    gold_table = binds_to.get("gold_table")
    if not isinstance(gold_table, str) or not gold_table or _is_placeholder(gold_table):
        return None
    return gold_table


def _normalize_ruling(ruling: object) -> str | None:
    """Whitespace-collapsed, case-insensitive ruling text; None if not a real ruling."""
    if not isinstance(ruling, str):
        return None
    normalized = " ".join(ruling.split()).casefold()
    return normalized or None


def _decided_rulings(contract: dict) -> dict[str, set[str]]:
    """Map A-code -> set of normalized decided rulings recorded by this contract.

    Only ``decision_status == "decided"`` entries with a non-empty ``ruling`` and a
    string ``id`` contribute (C2). Everything else contributes nothing.
    """
    out: dict[str, set[str]] = {}
    ambiguities = contract.get("ambiguities") or []
    if not isinstance(ambiguities, list):
        return out
    for entry in ambiguities:
        if not isinstance(entry, dict):
            continue
        if entry.get("decision_status") != "decided":
            continue
        code = entry.get("id")
        if not isinstance(code, str) or not code:
            continue
        normalized = _normalize_ruling(entry.get("ruling"))
        if normalized is None:
            continue
        out.setdefault(code, set()).add(normalized)
    return out


@register(
    RULE_ID,
    "Contracts on one gold table record no contradictory decided ambiguity rulings",
)
def check_assumption_coherence(ctx: RuleContext) -> Iterable[Finding]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope (B1/B3)

    findings: list[Finding] = []
    # group_key -> code -> set of (normalized_ruling, source_rel) for locator context
    groups: dict[str, dict[str, set[str]]] = {}
    sources: dict[str, dict[str, set[str]]] = {}

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
        key = _group_key(contract)
        if key is None:
            continue

        for code, rulings in _decided_rulings(contract).items():
            groups.setdefault(key, {}).setdefault(code, set()).update(rulings)
            for r in rulings:
                sources.setdefault(key, {}).setdefault(code, set()).add(rel)

    # A code is contradictory within a group iff it carries >= 2 distinct rulings.
    for key in sorted(groups):
        for code in sorted(groups[key]):
            if len(groups[key][code]) >= 2:
                contracts = ", ".join(sorted(sources[key][code]))
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        severity=Severity.ERROR,
                        message=(
                            f"contracts on gold table {key!r} record contradictory "
                            f"decided rulings for ambiguity code {code!r} "
                            f"({len(groups[key][code])} distinct rulings across: "
                            f"{contracts}) -- reconcile the ruling; the agent cannot "
                            f"decide which is correct (Principle V)"
                        ),
                        locator=f"{key}#{code}",
                    )
                )
    return findings
