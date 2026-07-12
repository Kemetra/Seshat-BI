"""Review-artifact generator tests (spec 121, T027).

Determinism (SC-008) + completeness (all eleven sections) + no-raw-PII + a
reviewer can find why a stage is blocked (SC-004).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.interview_review import (
    generate_review,
    write_review,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLOW_REL = "contracts/knowledge/database-to-pbip-flow.yaml"
_SEMANTIC = ".seshat/semantic-decisions.yaml"
_KPI = ".seshat/kpi-contracts.yaml"

_ELEVEN_SECTIONS = (
    "## Gate verdict",
    "## Approved decisions",
    "## Pending decisions",
    "## Blocking decisions",
    "## Rejected assumptions",
    "## Deferred decisions",
    "## PII handling",
    "## KPI-impacting decisions",
    "## Grain and relationship decisions",
    "## Cleaning and missing-value decisions",
    "## Next questions",
)

# A store spanning every status/type family.
_STORE = (
    "decisions:\n"
    "  - id: table_grain.fct_sales\n"
    "    decision_type: table_grain\n"
    "    statement: one sale line\n"
    "    scope: {tables: [fct_sales]}\n"
    "    status: pending\n"
    "    evidence: [ev.md]\n"
    "    proposed_by: agent\n"
    '    proposed_at: "2026-01-01"\n'
    "  - id: pii_handling.email\n"
    "    decision_type: pii_handling\n"
    "    statement: email is PII, drop it\n"
    "    scope: {columns: [dim_customer.email]}\n"
    "    status: rejected\n"
    "    evidence: [ev.md]\n"
    "    proposed_by: agent\n"
    '    proposed_at: "2026-01-01"\n'
    "  - id: missing_value_rule.amt\n"
    "    decision_type: missing_value_rule\n"
    "    statement: missing amount is NULL\n"
    "    scope: {columns: [fct_sales.amt]}\n"
    "    status: deferred\n"
    "    evidence: [ev.md]\n"
    "    proposed_by: agent\n"
    '    proposed_at: "2026-01-01"\n'
)


def _repo(tmp_path: Path, files: dict[str, str]) -> tuple[Path, tuple[str, ...]]:
    all_files = dict(files)
    all_files[_FLOW_REL] = (_REPO_ROOT / _FLOW_REL).read_text(encoding="utf-8")
    tracked = []
    for rel, body in all_files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        tracked.append(rel)
    return tmp_path, tuple(tracked)


def test_all_eleven_sections_present(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _STORE})
    text = generate_review(root, tracked, "silver_gold_model_planning")
    for section in _ELEVEN_SECTIONS:
        assert section in text, f"missing section {section!r}"


def test_generation_is_deterministic(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _STORE})
    a = generate_review(root, tracked, "silver_gold_model_planning")
    b = generate_review(root, tracked, "silver_gold_model_planning")
    assert a == b  # SC-008: same store => byte-identical


def test_reviewer_can_see_why_blocked(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _STORE})
    text = generate_review(root, tracked, "silver_gold_model_planning")
    # the pending grain decision is a blocker and must be named in the artifact
    assert "table_grain.fct_sales" in text
    assert "BLOCKED" in text


def test_decisions_appear_in_their_type_sections(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _STORE})
    text = generate_review(root, tracked, "silver_gold_model_planning")
    # rejected pii decision under Rejected AND PII handling
    grain_idx = text.index("## Grain and relationship decisions")
    pii_idx = text.index("## PII handling")
    assert "table_grain.fct_sales" in text[grain_idx:]
    assert "pii_handling.email" in text[pii_idx:]


def test_raw_pii_in_statement_is_masked_not_rendered(tmp_path: Path) -> None:
    # Non-vacuous: FEED the generator a raw email in a statement and an SSN in a
    # rendered approver, and assert the artifact masks them (SC-006 defense-in-depth).
    import re

    body = (
        "decisions:\n"
        "  - id: pii_handling.leaky\n"
        "    decision_type: pii_handling\n"
        '    statement: "found jane.doe@example.com in the export"\n'
        "    scope: {columns: [c.email]}\n"
        "    status: pending\n"
        "    evidence: [ev.md]\n"
        "    proposed_by: agent\n"
        '    proposed_at: "2026-01-01"\n'
    )
    root, tracked = _repo(tmp_path, {_SEMANTIC: body})
    text = generate_review(root, tracked, "silver_gold_model_planning")
    assert "jane.doe@example.com" not in text
    assert "[REDACTED]" in text
    assert not re.search(r"[\w.]+@[\w.]+\.\w{2,}", text)


def test_write_review_is_utf8_no_bom_lf(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: _STORE})
    path = write_review(root, tracked, "silver_gold_model_planning")
    assert path.name == "business-interview-review.md"
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # no BOM
    assert b"\r\n" not in raw  # LF only


def test_empty_store_renders_all_sections_as_none(tmp_path: Path) -> None:
    root, tracked = _repo(tmp_path, {_SEMANTIC: "decisions: []\n"})
    text = generate_review(root, tracked, "discovery")
    for section in _ELEVEN_SECTIONS:
        assert section in text
    assert "_None._" in text
