"""US3 compact CI/PR summary tests -- highest fake-confidence-risk surface (081).

The T016 negative test below is the most important in the suite: the compact
output must NEVER contain a fabricated-confidence pattern. Do not weaken it.
"""

import re

import pytest

from retail.review_pack_export import Pack, Section

pytestmark = pytest.mark.unit


def _blocked_pack() -> Pack:
    """compact-ci-summary.md first example: one pass + one blocked section."""
    return Pack(
        title="<TABLE>: <STAGE> review pack",
        sections=(
            Section(
                name="Gate requirement",
                status="pass",
                evidence=(
                    "<STAGE> gate documented at docs/readiness/<stage>-ready.md",
                ),
            ),
            Section(
                name="Readiness state",
                status="blocked",
                blocking_reasons=(
                    "grain not confirmed unique on data",
                    "PII ruling pending on column <col>",
                ),
            ),
        ),
    )


def test_compact_blocked_shape():
    """T013: worst status blocked -> [BLOCKED] + every worst-rank reason."""
    from retail.review_pack_export import to_compact_ci_summary

    out = to_compact_ci_summary(_blocked_pack())
    assert out.startswith("[BLOCKED] <TABLE>: <STAGE> review pack")
    assert "grain not confirmed unique on data" in out
    assert "PII ruling pending on column <col>" in out


def test_compact_all_clear_has_pass_and_evidence():
    """T014 (amended): >=1 pass (rest not_applicable) -> [PASS] + evidence."""
    from retail.review_pack_export import to_compact_ci_summary

    pack = Pack(
        title="<TABLE>: <STAGE> review pack",
        sections=(
            Section(
                name="Gate requirement",
                status="pass",
                evidence=(
                    "<STAGE> gate documented at docs/readiness/<stage>-ready.md",
                ),
            ),
            Section(name="Approval slot", status="not_applicable"),
        ),
    )
    out = to_compact_ci_summary(pack)
    assert out.startswith("[PASS]")
    assert "docs/readiness/<stage>-ready.md" in out


def test_compact_zero_pass_all_not_applicable_reports_not_applicable():
    """Amended data-model.md sec 5: a zero-pass (all not_applicable) pack
    reports [NOT_APPLICABLE], never [PASS] (a pass with no passing section is
    a fabricated pass)."""
    from retail.review_pack_export import to_compact_ci_summary

    pack = Pack(
        title="<TABLE>: <STAGE> review pack",
        sections=(
            Section(name="Approval slot A", status="not_applicable"),
            Section(name="Approval slot B", status="not_applicable"),
        ),
    )
    out = to_compact_ci_summary(pack)
    assert out.startswith("[NOT_APPLICABLE]")
    assert "[PASS]" not in out


def test_compact_zero_section_pack_no_sections():
    """T015: a zero-section pack renders [NO SECTIONS], never [PASS]."""
    from retail.review_pack_export import to_compact_ci_summary

    out = to_compact_ci_summary(Pack(title="<TABLE>: <STAGE> review pack", sections=()))
    assert out.startswith("[NO SECTIONS]")
    assert "[PASS]" not in out


# T016 -- fake-confidence NEGATIVE test. Runs against EVERY fixture pack here.
_FORBIDDEN_PATTERNS = [
    (r"\d+\s+of\s+\d+", "N of M count"),
    (r"%", "percent sign"),
    (r"\d+\s*(?:percent|pct)\b", "percent word"),
    (r"\b\d+\s*/\s*\d+\b", "bare ratio"),
    (r"\b(?:mostly|partially|somewhat)\s+ready\b", "maturity adjective"),
]


def _all_fixture_outputs():
    from retail.review_pack_export import to_compact_ci_summary

    packs = [
        _blocked_pack(),
        Pack(
            title="t",
            sections=(
                Section(name="A", status="pass", evidence=("e",)),
                Section(name="B", status="not_applicable"),
            ),
        ),
        Pack(title="t", sections=(Section(name="A", status="not_applicable"),)),
        Pack(title="t", sections=()),
        Pack(
            title="t",
            sections=(
                Section(name="A", status="blocked", blocking_reasons=("r1",)),
                Section(name="B", status="blocked", blocking_reasons=("r2",)),
            ),
        ),
    ]
    return [to_compact_ci_summary(p) for p in packs]


@pytest.mark.parametrize("pattern,label", _FORBIDDEN_PATTERNS)
def test_compact_never_emits_fake_confidence(pattern, label):
    """T016: no compact output, for any fixture, has a fake-confidence pattern."""
    rx = re.compile(pattern, re.IGNORECASE)
    for out in _all_fixture_outputs():
        assert not rx.search(out), f"forbidden {label} in output:\n{out}"


def test_compact_dual_worst_rank_lists_all_reasons():
    """T017: two sections tied at the worst rank each add their reasons."""
    from retail.review_pack_export import to_compact_ci_summary

    pack = Pack(
        title="t",
        sections=(
            Section(name="A", status="blocked", blocking_reasons=("reason-A",)),
            Section(name="B", status="warning"),
            Section(name="C", status="blocked", blocking_reasons=("reason-C",)),
        ),
    )
    out = to_compact_ci_summary(pack)
    assert "reason-A" in out
    assert "reason-C" in out
