"""Review Pack Exporter -- stable serialization formats for a review/evidence pack.

Feature spec: ``specs/081-review-pack-exporter/``.

This module is a **formatter over a stable pack shape**, not a producer. It takes
an already-produced, in-memory ``Pack`` (a header + ordered ``Section`` objects,
each carrying a status token + evidence + blocking reasons + optional embedded
``FindingRecord``s) and renders it into three output shapes:

- ``to_markdown(pack) -> str``            -- for humans
- ``to_json(pack) -> dict``               -- for machines (carries ``schema_version``)
- ``to_compact_ci_summary(pack) -> str``  -- worst-status + blocking reasons, for CI/PR

It does NOT read ``readiness-status.yaml``, metric contracts, or the parked-on
map, and it does NOT decide any status -- it renders whatever status the pack
already carries, verbatim (FR-001, FR-003, FR-004). It emits no numeric
confidence/health/maturity score and no completeness tally in any format
(FR-005, FR-006, hard rule #9). It never mutates its input (the dataclasses are
``frozen=True``). Deterministic: same pack in -> same output out; no wall-clock
read (FR-013).

Consumed seams (confirmed unchanged at build time, 2026-07-03):

- ``core.Finding.to_dict()`` (``src/seshat/core.py``) yields exactly
  ``{rule_id, severity, message, locator}`` -- this module's ``FindingRecord``
  documents the SAME four field names so a caller may pass ``Finding.to_dict()``
  output directly into a section's ``findings``. This module does NOT import
  ``core.Finding`` (FR-009: reuse by field convention, not a hard dependency).
- No YAML writer enters this module's import path (FR-016; the B3
  import-boundary discipline from ``readiness_evidence.py`` / spec 057).

Backwards-compatibility -- the additive-only rule (data-model.md section 4):
``schema_version`` is ``"<MAJOR>.<MINOR>"``. The rule is ADDITIVE-ONLY within one
MAJOR: a MINOR bump may ADD an optional field only; it MUST NOT remove/rename a
field or change an existing value's meaning (including a status token's meaning).
Removing/renaming a field or a status token requires a MAJOR bump. A consumer
written against ``"1.x"`` MUST ignore unknown fields in a ``"1.y"`` (y >= x)
document rather than fail closed. Keep this additive-only discipline in mind
before editing the dataclasses below.
"""

from __future__ import annotations

from dataclasses import dataclass

# The current pack schema version emitted in JSON output (data-model.md section 4).
SCHEMA_VERSION = "1.0"

# Recognized status tokens, passed through VERBATIM and never remapped
# (data-model.md section 1; FR-003/FR-004). Any token not in this set is
# unrecognized: passed through verbatim, flagged visibly in Markdown/compact and
# with "recognized": false in JSON (FR-017).
RECOGNIZED_STATUS_TOKENS = frozenset(
    {"not_started", "blocked", "warning", "pass", "pending", "not_applicable"}
)


@dataclass(frozen=True)
class FindingRecord:
    """A B2-compatible embedded finding.

    Identical field names to ``core.Finding.to_dict()``. This feature does not
    redefine the Finding shape; it documents the contract so a caller may pass
    ``Finding.to_dict()`` output (or any dict with these four keys) directly.
    """

    rule_id: str
    severity: str  # serialized Finding.severity value, e.g. "error" | "warning"
    message: str
    locator: str


@dataclass(frozen=True)
class Section:
    """One section of a review pack -- a status token + evidence/blockers/findings.

    Empty ``evidence``/``blocking_reasons`` render as an explicit "none recorded"
    statement, never a blank/ambiguous line (data-model.md section 3).
    """

    name: str
    status: str  # one token from RECOGNIZED_STATUS_TOKENS, or an unrecognized string
    evidence: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    findings: tuple[FindingRecord, ...] | None = None
    note: str | None = None


@dataclass(frozen=True)
class Pack:
    """The top-level object a producer constructs and passes to a render function."""

    title: str
    sections: tuple[Section, ...] = ()
    schema_version: str = SCHEMA_VERSION
    # generated_at OPTIONAL; if absent, no generated-at line is rendered.
    generated_at: str | None = None
    # source_note OPTIONAL free-text; rendered verbatim if present.
    source_note: str | None = None


# Fixed worst-status severity ordering for the compact CI/PR summary
# (data-model.md section 5). A mechanical, reversible convention -- NOT a
# business-rule judgment. Higher rank = "worse". An unrecognized token ranks at
# least as severe as "warning" so it is never silently hidden.
_STATUS_SEVERITY_ORDER: dict[str, int] = {
    "blocked": 4,
    "warning": 3,
    "pending": 1,
    "not_started": 1,
    "pass": 0,
    "not_applicable": 0,
}
_UNRECOGNIZED_RANK = 2  # between warning(3) and pending(1); data-model.md section 5


def _rank(status: str) -> int:
    """Severity rank for the worst-status pick; unrecognized tokens get rank 2."""
    return _STATUS_SEVERITY_ORDER.get(status, _UNRECOGNIZED_RANK)


def to_markdown(pack: Pack) -> str:
    """Render a Pack to human-readable Markdown (US1). Deterministic; no clock read."""
    lines: list[str] = [f"# {pack.title}", ""]
    if pack.generated_at is not None:
        lines.append(f"_generated: {pack.generated_at}_")
        lines.append("")
    if pack.source_note is not None:
        lines.append(f"_source: {pack.source_note}_")
        lines.append("")
    for section in pack.sections:
        lines.append(f"## {section.name}")
        lines.append("")
        status_line = f"**Status**: {section.status}"
        if section.status not in RECOGNIZED_STATUS_TOKENS:
            status_line += " (unrecognized status token -- passed through verbatim)"
        lines.append(status_line)
        lines.append("")
        if section.evidence:
            lines.append("**Evidence**:")
            lines.extend(f"- {item}" for item in section.evidence)
        else:
            lines.append("**Evidence**: none recorded")
        lines.append("")
        if section.blocking_reasons:
            lines.append("**Blocking reasons**:")
            lines.extend(f"- {item}" for item in section.blocking_reasons)
        else:
            lines.append("**Blocking reasons**: none recorded")
        if section.findings:
            lines.append("")
            lines.append("**Findings**:")
            lines.extend(
                f"- [{f.severity}] {f.rule_id}: {f.message} ({f.locator})"
                for f in section.findings
            )
        if section.note is not None:
            lines.append("")
            lines.append(f"**Note**: {section.note}")
        lines.append("")
    return "\n".join(lines)


def to_json(pack: Pack) -> dict:
    """Render a Pack to a machine-readable dict (US2), carrying schema_version.

    Conventions (contracts/json-schema.md): the ``findings`` key is OMITTED
    entirely when a section carries none (a consumer checks key presence); the
    ``recognized`` companion field is present ONLY when the status token is
    unrecognized (value ``False``).
    """
    sections_out: list[dict] = []
    for section in pack.sections:
        sec: dict = {
            "name": section.name,
            "status": section.status,
        }
        if section.status not in RECOGNIZED_STATUS_TOKENS:
            sec["recognized"] = False
        sec["evidence"] = list(section.evidence)
        sec["blocking_reasons"] = list(section.blocking_reasons)
        if section.findings is not None:
            sec["findings"] = [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "message": f.message,
                    "locator": f.locator,
                }
                for f in section.findings
            ]
        sec["note"] = section.note
        sections_out.append(sec)
    return {
        "schema_version": pack.schema_version,
        "title": pack.title,
        "generated_at": pack.generated_at,
        "source_note": pack.source_note,
        "sections": sections_out,
    }


def to_compact_ci_summary(pack: Pack) -> str:
    """Render a Pack to a compact CI/PR summary (US3): worst status + reasons.

    Carries NO numeric score, percentage, ratio, or completeness tally in ANY
    form (FR-005/FR-006, hard rule #9). The leading bracketed token is the worst
    recognized status, verbatim, uppercased for the CI label.
    """
    title = pack.title
    if not pack.sections:
        return f"[NO SECTIONS] {title}\n\nNo sections in pack."

    worst_rank = max(_rank(s.status) for s in pack.sections)
    worst_sections = [s for s in pack.sections if _rank(s.status) == worst_rank]

    # Rank-0 ("nothing blocking"): decide the label by what is actually PRESENT
    # so it never overstates. A pack with >=1 pass reports PASS; a zero-pass (all
    # not_applicable) pack reports NOT_APPLICABLE, never a fabricated PASS
    # (data-model.md section 5).
    if worst_rank == 0:
        has_pass = any(s.status == "pass" for s in pack.sections)
        if has_pass:
            evidence_lines = [
                e for s in pack.sections if s.status == "pass" for e in s.evidence
            ]
            body = (
                "\n".join(f"- {e}" for e in evidence_lines)
                if evidence_lines
                else "- (no evidence recorded)"
            )
            return f"[PASS] {title}\n\nEvidence:\n{body}"
        return (
            f"[NOT_APPLICABLE] {title}\n\n"
            "No section was applicable to this pack (nothing to pass or block)."
        )

    label = worst_sections[0].status
    if label in RECOGNIZED_STATUS_TOKENS:
        label_token = label.upper()
    else:
        label_token = f"{label} (UNRECOGNIZED)"
    reasons = [r for s in worst_sections for r in s.blocking_reasons]
    parts = [f"[{label_token}] {title}", ""]
    if reasons:
        parts.append("Blocking reasons:")
        parts.extend(f"- {r}" for r in reasons)
        parts.append("")
    parts.append("See full pack for detail.")
    return "\n".join(parts)
