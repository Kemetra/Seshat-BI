"""Live-validation evidence recorder (spec 057).

A PURE, stdlib-only serializer that maps ``validate.py`` live-check ``Finding``s
into a PROPOSED ``gold_ready`` readiness block (a plain dict). It is the missing
evidence half of a live ``retail validate`` run: today ``cli._run_validate`` only
prints findings to the console and sets an exit code -- nothing records them as
structured readiness evidence.

Consumed seams (confirmed unchanged, T001):
  - ``core.Finding`` fields: ``rule_id``, ``severity`` (a ``Severity`` enum),
    ``message``, ``locator``.
  - The DSN-redaction contract: scrub the literal DSN AND each of its parsed
    components (host, username, password, db-name) wherever they appear, since a
    driver can reformat a DSN into text where the literal never appears yet
    components leak. The decomposition is DELEGATED to ``seshat.redaction_core``
    (the single hardened source of truth, #365/#366) -- a stdlib-only leaf, so this
    path stays stdlib-only and does NOT import from ``cli`` (which would pull a
    heavy import in and trip the B3 import-boundary guard). Sharing that one
    decomposition -- rather than re-implementing it -- is what keeps this recorder
    from drifting weaker than the boundary redactors (#385 class).

Ratified rulings (spec 057 ## Clarifications):
  - FR-012: NEVER set ``status: pass``. A clean run is at most ``warning`` (advanced
    with recorded evidence); granting ``pass`` is a human/approval action (the
    Principle-V self-grant boundary).
  - FR-013: EMIT-only. This returns a dict; it writes no ``readiness-status.yaml``.
  - FR-014: an empty V-RC2 (no duplicate) is recorded as the OBSERVATION "no duplicate
    observed on current rows", never as a ratified grain claim.
  - FR-006: any DSN/credential embedded in a finding message is scrubbed.
  - FR-005: no numeric confidence/score field is emitted.
  - FR-007: inputs are never mutated; a NEW dict is returned.
  - Deterministic: any timestamp is an explicit argument, never read from the clock.
"""

from __future__ import annotations

from typing import Optional

from .core import Finding, Severity
from .redaction_core import replace_fragments, uri_components

_VALID_MODES = ("live", "deferred")


def _scrub(text: str, dsn: Optional[str]) -> str:
    """Redact the literal DSN and its non-empty components from ``text``.

    Delegates the component decomposition to :mod:`seshat.redaction_core` -- the
    single hardened source of truth (#365/#366) -- so recorded readiness evidence
    scrubs the DB-NAME and the percent-decoded form of every component (which the
    old hand-rolled copy missed), and can never drift from the shared decomposition
    (#385 class). Idempotent: a string with no surviving credential is unchanged.
    """
    out = str(text)
    if not dsn:
        return out
    # Literal DSN first (keeps the "<redacted DSN>" token), then every component;
    # uri_components sorts longest-first and is ValueError-total on a malformed DSN.
    out = out.replace(dsn, "<redacted DSN>")
    return replace_fragments(out, uri_components([dsn]), "<redacted>")


def build_gold_ready_block(
    findings: list[Finding],
    table_identity: str,
    run_mode: str = "live",
    timestamp: Optional[str] = None,
    dsn: Optional[str] = None,
) -> dict:
    """Build a proposed ``gold_ready`` readiness block from live-check findings.

    Pure and stdlib-only. Returns a NEW dict; mutates nothing. Never sets ``pass``.

    Status derivation:
      - ``run_mode="deferred"``          -> ``blocked`` (a live check could not run).
      - any ERROR finding                -> ``blocked`` (one blocking_reason per ERROR).
      - WARNING-only or clean live run -> ``warning`` (evidence recorded; not
        ``pass``).
    """
    if run_mode not in _VALID_MODES:
        raise ValueError(f"run_mode must be one of {_VALID_MODES}, got {run_mode!r}")
    if not table_identity or not table_identity.strip():
        raise ValueError("table_identity must be a non-empty table name")

    table = table_identity.strip()
    errors = [f for f in findings if f.severity is Severity.ERROR]
    warnings = [f for f in findings if f.severity is Severity.WARNING]

    def _line(f: Finding) -> str:
        return _scrub(f"{f.rule_id}: {f.message} [{f.locator}]", dsn)

    block: dict = {
        "stage": "gold_ready",
        "table": table,
        "run_mode": run_mode,
        "evidence": [],
        "warnings": [_line(f) for f in warnings],
        "blocking_reasons": [],
    }
    if timestamp is not None:
        block["recorded_at"] = timestamp

    if run_mode == "deferred":
        block["status"] = "blocked"
        block["blocking_reasons"] = [
            "no live validate run occurred (deferred: no DSN / no DB driver) "
            "-- gold_ready evidence is PENDING LIVE PROFILE"
        ]
        return block

    if errors:
        block["status"] = "blocked"
        block["blocking_reasons"] = [_line(f) for f in errors]
        return block

    # Clean or warning-only live run: record evidence, never grant pass (FR-012).
    # Both cases resolve to `warning` -- a clean run is "advanced with recorded
    # evidence", NOT `pass` (setting pass is a human/approval action).
    block["status"] = "warning"
    block["evidence"] = [
        f"live validate run for {table}: "
        f"{len(errors)} ERROR, {len(warnings)} WARNING findings",
        # FR-014: an empty V-RC2 is an observation, not a ratified grain claim.
        "no duplicate observed on current rows (V-RC2 clean) -- an observation, "
        "not a ratified grain/uniqueness claim",
    ]
    return block
