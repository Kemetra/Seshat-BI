"""Human review projection for immutable statistical evidence."""

from __future__ import annotations

from pathlib import Path

from .contracts import AnalysisEvidence, Estimate
from .evidence import _atomic_write_text, evidence_payload

_PREAMBLE = (
    "This document projects immutable derived evidence. It does not recompute "
    "statistics, grant approval, or change readiness; readiness effect is none."
)

_DECISION_BLOCK = (
    "## Human review decision",
    "",
    "- [ ] accepted",
    "- [ ] rejected",
    "- [ ] changes requested",
    "",
    "Reviewer:",
    "Authority class:",
    "Reviewed at:",
    "Permitted narrative claim:",
    "Required caveats:",
    "",
)


def _estimate_line(item: Estimate) -> str:
    value = item.value if item.value is not None else "not available"
    unit = f" {item.unit}" if item.unit else ""
    return f"- {item.name}: {value}{unit}"


def _lines_or_none(lines: list[str]) -> list[str]:
    return lines if lines else ["- None recorded."]


def _section(title: str, lines: list[str]) -> list[str]:
    return ["", f"## {title}", "", *_lines_or_none(lines)]


def _reference_section(evidence: AnalysisEvidence) -> list[str]:
    return [
        "# Statistical analysis review",
        "",
        _PREAMBLE,
        "",
        "## Evidence reference",
        "",
        f"- Invocation ID: {evidence.invocation_id}",
        f"- Outcome: {evidence.outcome.value}",
        f"- Authority: {evidence.authority}",
        f"- Review state: {evidence.review_state}",
    ]


def _population_section(evidence: AnalysisEvidence) -> list[str]:
    input_data = evidence.input_provenance
    lines = [
        "",
        "## Population and exclusions",
        "",
        f"- Observation grain: {input_data.get('observation_grain', 'not recorded')}",
        f"- Input count: {input_data.get('input_count', 'not recorded')}",
        f"- Excluded count: {input_data.get('excluded_count', 'not recorded')}",
    ]
    reasons = input_data.get("exclusion_reasons", ())
    lines.extend(f"- Exclusion: {reason}" for reason in reasons)
    return lines


def _method_section(evidence: AnalysisEvidence) -> list[str]:
    method = evidence.method
    return [
        "",
        "## Method",
        "",
        f"- {method.get('id', 'unknown')} ({method.get('version', 'unknown')})",
        f"- Random seed: {method.get('random_seed', 'not recorded')}",
    ]


def _interval_lines(evidence: AnalysisEvidence) -> list[str]:
    return [
        f"- {item.name}: [{item.low}, {item.high}] at {item.level} ({item.method})"
        for item in evidence.intervals
    ]


def _test_lines(evidence: AnalysisEvidence) -> list[str]:
    return [
        (
            f"- {item.name}: statistic={item.statistic}, "
            f"p={item.p_value}, adjusted_p={item.adjusted_p_value} "
            f"({item.method})"
        )
        for item in evidence.tests
    ]


def _diagnostic_lines(evidence: AnalysisEvidence) -> list[str]:
    return [
        (
            f"- {item.code} [{item.status}]: {item.message}"
            + (f" Observed: {item.observed}" if item.observed else "")
        )
        for item in evidence.diagnostics
    ]


def _warning_lines(evidence: AnalysisEvidence) -> list[str]:
    return [
        *(f"- Warning: {item}" for item in evidence.warnings),
        *(
            f"- Blocker {item.code}: {item.message} Recovery: {item.recovery}"
            for item in evidence.blockers
        ),
    ]


def render_review(evidence: AnalysisEvidence) -> str:
    """Render evidence for named-human review without recomputing statistics."""

    evidence_payload(evidence)
    lines = [
        *_reference_section(evidence),
        *_population_section(evidence),
        *_method_section(evidence),
        *_section("Estimates", [_estimate_line(item) for item in evidence.estimates]),
        *_section(
            "Effect sizes", [_estimate_line(item) for item in evidence.effect_sizes]
        ),
        *_section("Intervals", _interval_lines(evidence)),
        *_section("Tests", _test_lines(evidence)),
        *_section("Diagnostics", _diagnostic_lines(evidence)),
        *_section("Warnings and blockers", _warning_lines(evidence)),
        *_section(
            "Interpretation cautions", [f"- {item}" for item in evidence.cautions]
        ),
        "",
        *_DECISION_BLOCK,
    ]
    return "\n".join(lines)


def write_review(
    path: Path,
    evidence: AnalysisEvidence,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Atomically write the deterministic human-review projection."""

    return _atomic_write_text(path, render_review(evidence), repo_root)
