"""Human review projection for immutable statistical evidence."""

from __future__ import annotations

from pathlib import Path

from .contracts import AnalysisEvidence, Estimate
from .evidence import _atomic_write_text, evidence_payload


def _estimate_line(item: Estimate) -> str:
    value = item.value if item.value is not None else "not available"
    unit = f" {item.unit}" if item.unit else ""
    return f"- {item.name}: {value}{unit}"


def _lines_or_none(lines: list[str]) -> list[str]:
    return lines if lines else ["- None recorded."]


def render_review(evidence: AnalysisEvidence) -> str:
    """Render evidence for named-human review without recomputing statistics."""

    evidence_payload(evidence)
    input_data = evidence.input_provenance
    method = evidence.method
    lines = [
        "# Statistical analysis review",
        "",
        "This document projects immutable derived evidence. It does not recompute "
        "statistics, grant approval, or change readiness; readiness effect is none.",
        "",
        "## Evidence reference",
        "",
        f"- Invocation ID: {evidence.invocation_id}",
        f"- Outcome: {evidence.outcome.value}",
        f"- Authority: {evidence.authority}",
        f"- Review state: {evidence.review_state}",
        "",
        "## Population and exclusions",
        "",
        f"- Observation grain: {input_data.get('observation_grain', 'not recorded')}",
        f"- Input count: {input_data.get('input_count', 'not recorded')}",
        f"- Excluded count: {input_data.get('excluded_count', 'not recorded')}",
    ]
    exclusion_reasons = input_data.get("exclusion_reasons", ())
    if exclusion_reasons:
        lines.extend(f"- Exclusion: {reason}" for reason in exclusion_reasons)
    lines.extend(
        [
            "",
            "## Method",
            "",
            f"- {method.get('id', 'unknown')} ({method.get('version', 'unknown')})",
            f"- Random seed: {method.get('random_seed', 'not recorded')}",
            "",
            "## Estimates",
            "",
            *_lines_or_none([_estimate_line(item) for item in evidence.estimates]),
            "",
            "## Effect sizes",
            "",
            *_lines_or_none([_estimate_line(item) for item in evidence.effect_sizes]),
            "",
            "## Intervals",
            "",
            *_lines_or_none(
                [
                    (
                        f"- {item.name}: [{item.low}, {item.high}] "
                        f"at {item.level} ({item.method})"
                    )
                    for item in evidence.intervals
                ]
            ),
            "",
            "## Tests",
            "",
            *_lines_or_none(
                [
                    (
                        f"- {item.name}: statistic={item.statistic}, "
                        f"p={item.p_value}, adjusted_p={item.adjusted_p_value} "
                        f"({item.method})"
                    )
                    for item in evidence.tests
                ]
            ),
            "",
            "## Diagnostics",
            "",
            *_lines_or_none(
                [
                    (
                        f"- {item.code} [{item.status}]: {item.message}"
                        + (f" Observed: {item.observed}" if item.observed else "")
                    )
                    for item in evidence.diagnostics
                ]
            ),
            "",
            "## Warnings and blockers",
            "",
            *_lines_or_none(
                [
                    *(f"- Warning: {item}" for item in evidence.warnings),
                    *(
                        (
                            f"- Blocker {item.code}: {item.message} "
                            f"Recovery: {item.recovery}"
                        )
                        for item in evidence.blockers
                    ),
                ]
            ),
            "",
            "## Interpretation cautions",
            "",
            *_lines_or_none([f"- {item}" for item in evidence.cautions]),
            "",
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
        ]
    )
    return "\n".join(lines)


def write_review(
    path: Path,
    evidence: AnalysisEvidence,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Atomically write the deterministic human-review projection."""

    return _atomic_write_text(path, render_review(evidence), repo_root)
