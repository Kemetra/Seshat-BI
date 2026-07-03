"""US1 Markdown format tests for the review pack exporter (spec 081)."""

import pytest

from retail.review_pack_export import FindingRecord, Pack, Section

pytestmark = pytest.mark.unit


def _contract_pack() -> Pack:
    """The two-section worked example from contracts/markdown.md."""
    return Pack(
        schema_version="1.0",
        title="<TABLE>: <STAGE> review pack",
        generated_at=None,
        source_note="composed by <producer skill/module>, <date>",
        sections=(
            Section(
                name="Gate requirement",
                status="pass",
                evidence=(
                    "<STAGE> gate documented at docs/readiness/<stage>-ready.md",
                ),
                blocking_reasons=(),
                findings=None,
                note=None,
            ),
            Section(
                name="Readiness state",
                status="blocked",
                evidence=(),
                blocking_reasons=(
                    "grain not confirmed unique on data",
                    "PII ruling pending on column <col>",
                ),
                findings=(
                    FindingRecord(
                        rule_id="S5",
                        severity="WARNING",
                        message="type discipline check",
                        locator="warehouse/silver/<table>.sql:12",
                    ),
                ),
                note=None,
            ),
        ),
    )


EXPECTED_MARKDOWN = """# <TABLE>: <STAGE> review pack

_source: composed by <producer skill/module>, <date>_

## Gate requirement

**Status**: pass

**Evidence**:
- <STAGE> gate documented at docs/readiness/<stage>-ready.md

**Blocking reasons**: none recorded

## Readiness state

**Status**: blocked

**Evidence**: none recorded

**Blocking reasons**:
- grain not confirmed unique on data
- PII ruling pending on column <col>

**Findings**:
- [WARNING] S5: type discipline check (warehouse/silver/<table>.sql:12)
"""


def test_markdown_matches_contract_byte_exact():
    """T003: the contracts/markdown.md worked example renders byte-exact."""
    from retail.review_pack_export import to_markdown

    assert to_markdown(_contract_pack()) == EXPECTED_MARKDOWN


def test_markdown_empty_lists_render_none_recorded():
    """T004: empty evidence/blockers -> explicit 'none recorded', not a blank line."""
    from retail.review_pack_export import to_markdown

    pack = Pack(title="t", sections=(Section(name="S", status="pass"),))
    out = to_markdown(pack)
    assert "**Evidence**: none recorded" in out
    assert "**Blocking reasons**: none recorded" in out


def test_markdown_not_applicable_token_verbatim():
    """T005: not_applicable renders that token, never coerced to pass/blocked."""
    from retail.review_pack_export import to_markdown

    pack = Pack(title="t", sections=(Section(name="S", status="not_applicable"),))
    out = to_markdown(pack)
    assert "**Status**: not_applicable" in out
    assert "**Status**: pass" not in out


def test_markdown_deterministic():
    """T006: rendering the same Pack twice (no generated_at) is byte-identical."""
    from retail.review_pack_export import to_markdown

    pack = _contract_pack()
    assert to_markdown(pack) == to_markdown(pack)


def test_markdown_unrecognized_token_flagged():
    """T007: an unrecognized status token is visibly flagged, not shown as known."""
    from retail.review_pack_export import to_markdown

    pack = Pack(title="t", sections=(Section(name="S", status="frobnicated"),))
    out = to_markdown(pack)
    assert "frobnicated" in out
    # visibly flagged as unrecognized (not silently passed as if known)
    assert "unrecognized" in out.lower()


def test_markdown_omits_generated_at_when_absent():
    """generated_at None -> no timestamp line anywhere (FR-013 determinism)."""
    from retail.review_pack_export import to_markdown

    out = to_markdown(_contract_pack())
    assert "generated" not in out.lower()
