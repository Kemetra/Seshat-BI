"""Business-interview review artifact generator (spec 121).

Deterministically render the project Decision Store into the human-readable
``evidence/business-interview-review.md``: eleven fixed sections a non-technical
owner can read without opening YAML. The artifact holds NO independent state --
the same store always produces byte-identical output (NFR-002), so a stale copy
is always reproducible. Masked values only; the generator never emits a raw
suspected-PII value (it renders the store's ``statement`` text, which the DS1
guard already forbids from carrying raw PII).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from seshat.decision_gate import Verdict, compute_verdict
from seshat.decision_store import Store, load_store

REVIEW_REL_PATH = "evidence/business-interview-review.md"

# Defense-in-depth: even though DS1 flags a suspected-PII/secret value in a store
# field, mask obvious shapes at render time so a warned-but-committed value never
# appears verbatim in the human-facing artifact (FR-005 / SC-006).
_MASK_SHAPES: tuple[re.Pattern[str], ...] = (
    re.compile(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"\b\d{3}[ .-]\d{2}[ .-]\d{4}\b"),  # SSN-like
    re.compile(r"\b(?:\d[ -]?){12,19}\b"),  # long digit run
    re.compile(
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|token)\b\s*[:=]\s*\S+"
    ),  # secret assignment
)


def _mask(text: str) -> str:
    for pattern in _MASK_SHAPES:
        text = pattern.sub("[REDACTED]", text)
    return text


_OPEN_STATUSES = ("pending", "needs_user_input", "needs_sample", "blocked")
_GRAIN_TYPES = ("table_grain", "primary_key", "relationship_cardinality")
_KPI_TYPES = ("kpi_definition", "policy_ruling")
_CLEANING_TYPES = ("missing_value_rule",)


def _sorted(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable ordering by id for deterministic output (NFR-001/002)."""
    return sorted(decisions, key=lambda d: str(d.get("id", "")))


def _line(decision: dict[str, Any]) -> str:
    did = decision.get("id", "<no-id>")
    raw_statement = decision.get("statement")
    statement = _mask(raw_statement.strip()) if isinstance(raw_statement, str) else ""
    status = decision.get("status", "?")
    approver = ""
    approval = decision.get("approval")
    if isinstance(approval, dict) and approval.get("approved_by"):
        approver = f" -- approved by {_mask(str(approval['approved_by']))}"
    return f"- `{did}` ({status}): {statement}{approver}"


def _section(title: str, decisions: list[dict[str, Any]]) -> str:
    body = "\n".join(_line(d) for d in _sorted(decisions)) if decisions else "_None._"
    return f"## {title}\n\n{body}\n"


def _by_status(decisions: list[dict[str, Any]], *statuses: str) -> list[dict[str, Any]]:
    wanted = set(statuses)
    return [d for d in decisions if d.get("status") in wanted]


def _by_type(decisions: list[dict[str, Any]], *types: str) -> list[dict[str, Any]]:
    wanted = set(types)
    return [d for d in decisions if d.get("decision_type") in wanted]


def _verdict_section(verdict: Verdict) -> str:
    lines = [
        "## Gate verdict\n",
        f"**{verdict.verdict.upper()}** for stage `{verdict.stage}`.\n",
    ]
    if verdict.blocking:
        lines.append("Blocking decisions:\n")
        for b in verdict.blocking:
            lines.append(f"- `{b.decision_id}`: {b.reason}")
        lines.append("")
    if verdict.warnings:
        lines.append("Warnings:\n")
        lines += [f"- {w}" for w in verdict.warnings]
        lines.append("")
    return "\n".join(lines) + "\n"


def render_review(store: Store, verdict: Verdict) -> str:
    """Render the eleven-section review markdown from the store + a gate verdict."""
    decisions = store.decisions()
    blocking_ids = {b.decision_id for b in verdict.blocking}
    blocking = [d for d in decisions if str(d.get("id")) in blocking_ids]

    parts = [
        "# Business Knowledge Interview -- Review\n",
        "_Generated from the project Decision Store. "
        "Do not edit by hand; regenerate._\n",
        _verdict_section(verdict),
        _section("Approved decisions", _by_status(decisions, "approved")),
        _section("Pending decisions", _by_status(decisions, *_OPEN_STATUSES)),
        _section("Blocking decisions", blocking),
        _section("Rejected assumptions", _by_status(decisions, "rejected")),
        _section("Deferred decisions", _by_status(decisions, "deferred")),
        _section("PII handling", _by_type(decisions, "pii_handling")),
        _section("KPI-impacting decisions", _by_type(decisions, *_KPI_TYPES)),
        _section(
            "Grain and relationship decisions", _by_type(decisions, *_GRAIN_TYPES)
        ),
        _section(
            "Cleaning and missing-value decisions",
            _by_type(decisions, *_CLEANING_TYPES),
        ),
        _section(
            "Next questions", _by_status(decisions, "needs_user_input", "needs_sample")
        ),
    ]
    return "\n".join(parts).rstrip() + "\n"


def generate_review(
    repo_root: Path | str, tracked_files: tuple[str, ...], stage: str
) -> str:
    """Load the store, compute the stage verdict, and render the review text."""
    store = load_store(repo_root, tracked_files)
    verdict = compute_verdict(repo_root, store, stage)
    return render_review(store, verdict)


def write_review(
    repo_root: Path | str, tracked_files: tuple[str, ...], stage: str
) -> Path:
    """Write the generated review to ``evidence/business-interview-review.md``.

    UTF-8 without BOM, ``\\n`` line endings (byte-stable under core.autocrlf)."""
    text = generate_review(repo_root, tracked_files, stage)
    path = Path(repo_root) / REVIEW_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path
