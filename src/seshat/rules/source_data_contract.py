"""HR12 -- forward source data-contract presence (spec 105, gap #10).

What HR12 does (STATIC, fail-closed, opt-in):
  Scans ``ctx.tracked_files`` for a table's forward source data-contract at
  ``mappings/<table>/source-data-contract.yaml`` (instantiated from the NEW
  generic ``templates/source-data-contract.yaml``). When that file exists for a
  table, HR12 verifies it is present and STRUCTURALLY WELL-FORMED: three
  required sections -- ``schema`` (a non-empty list of entries, each carrying a
  non-placeholder ``name`` AND ``type``), ``arrival.cadence`` (a non-blank,
  non-placeholder free-text statement of when data is expected to land), and
  ``restatement.policy`` (a non-blank, non-placeholder free-text statement of
  whether/how the supplier resends or corrects rows for an already-loaded
  period). A required field that is absent, blank, or still holds the
  template's literal sentinel token is treated as equivalent to missing
  (structural, non-semantic detection only -- never a judgment on whether a
  filled value is a "good" answer).

  - No contract file for a table -> NO Finding (opt-in per FR-002; absence is
    not-applicable, never penalized, never defaulted to an empty contract).
  - A present, fully-filled contract -> NO Finding (pass-eligible; the file's
    own path is the passing evidence, per SC-001).
  - A present but incomplete/placeholder contract -> one ``Severity.ERROR``
    Finding PER incomplete section (schema / arrival / restatement), never one
    combined undifferentiated message (FR-006).
  - A present file that is not valid YAML at all (a parse error) or cannot be
    read -> exactly one ``Severity.ERROR`` Finding naming the FILE ITSELF (never
    a section, since none could be parsed), mirroring SF1's/AL2's
    ``except (OSError, yaml.YAMLError)`` fail-loud precedent. HR12 never raises
    an unhandled exception out of the rule handler.

What HR12 NEVER does:
  - It never opens a database connection, never reads/computes a live
    ``MAX(<date column>)`` or any other live arrival signal, and never detects
    an actual restatement event on live data (Principle VIII, static-first /
    live-deferred). Live enforcement of this contract is explicitly deferred to
    a future ``retail validate`` extension; a passing HR12 proves only that the
    forward declaration itself is present and well-formed, never that a live
    arrival cadence match or an absence of restatement has been confirmed.
  - It never reads or writes ``source-map.yaml`` or its ``meta.freshness`` key
    (090/HR4's collision-free concern -- a supplier-facing forward arrival
    agreement is distinct from an internal staleness tolerance), never reads
    ``readiness-status.yaml``, and never raises a ``stale_pass`` blocker
    (089/HR3's concern). It reads only
    ``mappings/<table>/source-data-contract.yaml``.
  - It never invents, infers, or defaults the actual VALUES of a table's
    schema, arrival cadence, or restatement policy -- these are owner-supplied
    facts about a real upstream system (Principle V). HR12's role is limited to
    checking presence/well-formedness; a human fills each table's copy. It
    performs no semantic parsing of cadence or restatement prose -- a stated
    "never resends, because <basis>" is exactly as complete an answer as a
    stated mechanism-plus-lookback.
  - It never emits a numeric confidence/health/maturity score or an "N of M"
    completeness tally (hard rule #9); its result is categorical (Finding(s) or
    no Finding) only.
  - It never changes the Mapping Ready gate's required five-artifact list; the
    contract is an additional, independent, opt-in artifact (FR-010).

Mirrors SF1's/AL2's structural shape: lazy ``import yaml`` inside the handler
only (kept out of the retail-check static-core stdlib-only chain), a compiled
path regex scanning ``ctx.tracked_files``, a template-path exclusion constant,
and an ``is_test_path`` exclusion for committed test fixtures.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "HR12"

_CONTRACT_RE = re.compile(r"^mappings/[^/]+/source-data-contract\.ya?ml$")
_TEMPLATE_PATH = "templates/source-data-contract.yaml"

# Exact, case-sensitive sentinel tokens the template ships per required field
# (spec Clarifications Q2). Detection is a byte-identical, whitespace-normalized
# match -- never a regex heuristic, never a semantic judgment (FR-006).
_SENTINEL_COLUMN_NAME = "REPLACE_ME_COLUMN_NAME"
_SENTINEL_COLUMN_TYPE = "REPLACE_ME_COLUMN_TYPE"
_SENTINEL_ARRIVAL_CADENCE = "REPLACE_ME_ARRIVAL_CADENCE"
_SENTINEL_RESTATEMENT_POLICY = "REPLACE_ME_RESTATEMENT_POLICY"


def _iter_contracts(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if _CONTRACT_RE.match(p) and p != _TEMPLATE_PATH and not is_test_path(p)
    ]


def _normalize(value: object) -> str | None:
    """Whitespace-normalized string, or None if not a usable string at all."""
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _is_placeholder_text(value: object, sentinel: str) -> bool:
    """True if a required free-text field is absent, blank, or the sentinel verbatim."""
    normalized = _normalize(value)
    if normalized is None:
        return True
    return normalized == sentinel


def _schema_incomplete(schema: object) -> bool:
    """True if the schema section fails closed (empty list, or any bad entry)."""
    if not isinstance(schema, list) or not schema:
        return True
    for entry in schema:
        if not isinstance(entry, dict):
            return True
        if _is_placeholder_text(entry.get("name"), _SENTINEL_COLUMN_NAME):
            return True
        if _is_placeholder_text(entry.get("type"), _SENTINEL_COLUMN_TYPE):
            return True
    return False


def _check_contract(rel: str, contract: dict) -> list[Finding]:
    findings: list[Finding] = []

    schema = contract.get("schema")
    if _schema_incomplete(schema):
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"{rel}: 'schema' section is incomplete -- it must be a "
                    "non-empty list where every entry carries a non-placeholder "
                    "'name' and 'type'"
                ),
                locator=rel,
            )
        )

    arrival = contract.get("arrival")
    cadence = arrival.get("cadence") if isinstance(arrival, dict) else None
    if _is_placeholder_text(cadence, _SENTINEL_ARRIVAL_CADENCE):
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"{rel}: 'arrival.cadence' is missing, blank, or still the "
                    "template placeholder -- state the supplier's actual "
                    "expected arrival cadence"
                ),
                locator=rel,
            )
        )

    restatement = contract.get("restatement")
    policy = restatement.get("policy") if isinstance(restatement, dict) else None
    if _is_placeholder_text(policy, _SENTINEL_RESTATEMENT_POLICY):
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"{rel}: 'restatement.policy' is missing, blank, or still "
                    "the template placeholder -- state whether/how the supplier "
                    "resends or corrects rows for an already-loaded period (an "
                    "explicit 'never, because <basis>' is a complete answer)"
                ),
                locator=rel,
            )
        )

    return findings


@register(RULE_ID, "forward source data-contract presence")
def check_hr12(ctx: RuleContext) -> Iterable[Finding]:
    import yaml  # lazy: keep the retail-check core stdlib-only at module scope

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
                    message=f"could not read/parse source data-contract: {exc}",
                    locator=rel,
                )
            )
            continue

        if not isinstance(contract, dict):
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"could not read/parse source data-contract: {rel} does "
                        "not contain a YAML mapping"
                    ),
                    locator=rel,
                )
            )
            continue

        findings.extend(_check_contract(rel, contract))

    return findings
