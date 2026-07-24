"""Library tests for the read-only narrative-brief checker (spec 021, T012/T013).

Three outcome classes, per SC-003 and FR-007/008/009:

(a) a clean brief conforming to the FROZEN ``seshat.narrative-brief/v1`` schema
    (derivation-route.md) -> ``pass``, no findings, ``grants_approval`` False;
(b) each single-mutation brief -> exactly the one named finding it should
    trigger (bare-total headline, missing/mismatched story order, [GAP]
    rendered as a framed question, ungrounded cite, stale contract revision,
    non-literal stage, empty callout) with a non-``pass`` status;
(c) missing / unreadable / schema-invalid brief -> a fail-closed ``blocked``
    naming the problem -- NEVER a silent ``pass`` over nothing (the #453 lesson).

The checker validates the narrative BRIEF against its schema. The
visual<->question binding-map orphan checks land with Phase B (T010) -- the map
does not exist yet; those fixtures are visible skips below, never faked.

Read-only: the checker opens nothing for write, sets no readiness stage, and
``grants_approval`` is structurally always False.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.narrative_check import NarrativeCheckResult, check_narrative

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Fixtures: a committed workspace with an approved contract + a clean brief
# --------------------------------------------------------------------------- #

_CONTRACT_TEXT = "metric: NetSales\nowner: analytics\nstatus: approved\n"

# A REAL-format source-profile: the committed convention is a per-column PIPE
# TABLE of bare column names (see mappings/*/source-profile.md), NOT a
# `## Dimensions` bullet list of dotted `entity.attribute` ids. Fixtures must
# mirror the shape real profiles ship, not a shape invented to match the code.
_PROFILE_TEXT = """# source-profile: orders

## Per-column profile

| Column | Type as landed | Missing | Distinct | PK? | Notes |
|--------|----------------|---------|----------|-----|-------|
| `division` | TEXT | 0 / 0.00% | 6 | no | product division -> dim attribute |
| `region` | TEXT | 0 / 0.00% | 4 | no | store region -> dim attribute |
"""


def _blob_sha(path: Path) -> str:
    """The git blob sha of a file's *content* -- matches how the brief cites a
    contract revision (``git hash-object``), computed with no repo required."""
    out = subprocess.run(
        ["git", "hash-object", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _clean_brief_front(contract_sha: str) -> str:
    return f"""```yaml
schema: seshat.narrative-brief/v1
table: orders
source_profile: mappings/orders/source-profile.md
contracts:
  - id: NetSales
    revision: {contract_sha}
questions:
  - id: Q1
    decision: Where is net sales concentrated so I know where to defend?
    stage: overview
    framing: concentration
    cites:
      measures: [NetSales]
      dimensions: [division]
    comparison: portfolio average
    guardrail:
      basis: portfolio average
    callout: The top division carries a disproportionate share of net sales.
  - id: Q2
    decision: What moved net sales versus last year?
    stage: change
    framing: period-variance
    cites:
      measures: [NetSales]
      dimensions: [region]
    comparison: same period last year
    guardrail:
      basis: same period last year
    callout: Net sales rose, driven by the northern region.
story_order:
  overview:  [Q1]
  change:    [Q2]
  why_where: []
  action:    []
gaps:
  - question: Which SKUs drive the margin gap?
    missing_source_fact: no unit-cost column in the profile
    unlocking_feed: add a cost feed to the source
```

# Narrative brief: orders

## Q1 -- where is net sales concentrated
The owner defends the biggest contributors first...
"""


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """A committed-shape workspace: an approved contract, a source-profile, and
    a clean narrative brief citing the contract's current blob sha."""
    table_dir = tmp_path / "mappings" / "orders"
    (table_dir / "contracts").mkdir(parents=True)
    contract = table_dir / "contracts" / "NetSales.yaml"
    contract.write_text(_CONTRACT_TEXT, encoding="utf-8")
    (table_dir / "source-profile.md").write_text(_PROFILE_TEXT, encoding="utf-8")
    brief = table_dir / "narrative-brief.md"
    brief.write_text(_clean_brief_front(_blob_sha(contract)), encoding="utf-8")
    return tmp_path


def _mutate_brief(workspace: Path, old: str, new: str) -> None:
    brief = workspace / "mappings" / "orders" / "narrative-brief.md"
    text = brief.read_text(encoding="utf-8")
    assert old in text, f"fixture drift: {old!r} not in the clean brief"
    brief.write_text(text.replace(old, new, 1), encoding="utf-8")


def _run(workspace: Path) -> NarrativeCheckResult:
    return check_narrative(table="orders", repo_root=workspace)


# --------------------------------------------------------------------------- #
# Class (a): a clean brief passes with no findings and grants nothing
# --------------------------------------------------------------------------- #


def test_clean_brief_passes(workspace: Path):
    result = _run(workspace)
    assert result.status == "pass"
    assert result.findings == ()


def test_clean_brief_grants_no_approval(workspace: Path):
    result = _run(workspace)
    assert result.grants_approval is False


def test_clean_brief_evidence_states_not_approval(workspace: Path):
    result = _run(workspace)
    joined = " ".join(result.evidence).lower()
    assert "evidence" in joined and "approval" in joined


# --------------------------------------------------------------------------- #
# Class (b): each single mutation triggers exactly its one named finding
# --------------------------------------------------------------------------- #


def test_bare_total_headline_is_a_finding(workspace: Path):
    # An overview (headline) question with comparison "none" -- a bare total
    # (FR-006). Non-overview questions may be "none"; overview may not.
    _mutate_brief(workspace, "comparison: portfolio average", "comparison: none")
    result = _run(workspace)
    assert result.status == "blocked"
    dims = {f.dimension for f in result.findings}
    assert "bare_total_headline" in dims
    assert any("Q1" in f.message for f in result.findings)


def test_story_order_stage_mismatch_is_a_finding(workspace: Path):
    # Q1 declares stage: overview but story_order lists it under `change`.
    _mutate_brief(workspace, "overview:  [Q1]", "overview:  []")
    _mutate_brief(workspace, "change:    [Q2]", "change:    [Q2, Q1]")
    result = _run(workspace)
    assert result.status == "blocked"
    assert "story_order_mismatch" in {f.dimension for f in result.findings}


def test_missing_story_order_stage_key_is_a_finding(workspace: Path):
    # All four stage keys are REQUIRED; drop `action`.
    _mutate_brief(workspace, "  action:    []\n", "")
    result = _run(workspace)
    assert result.status == "blocked"
    assert "story_order_incomplete" in {f.dimension for f in result.findings}


def test_empty_overview_stage_is_a_finding(workspace: Path):
    # A report with no overview is a defect even if the keys are all present.
    _mutate_brief(workspace, "overview:  [Q1]", "overview:  []")
    _mutate_brief(workspace, "why_where: []", "why_where: [Q1]")
    _mutate_brief(workspace, "    stage: overview", "    stage: why_where")
    result = _run(workspace)
    assert result.status == "blocked"
    assert "empty_overview" in {f.dimension for f in result.findings}


def test_gap_rendered_as_question_is_a_finding(workspace: Path):
    # The [GAP] question text ALSO appears as a framed question -- you cannot
    # frame what you cannot answer.
    _mutate_brief(
        workspace,
        "    decision: What moved net sales versus last year?",
        "    decision: Which SKUs drive the margin gap?",
    )
    result = _run(workspace)
    assert result.status == "blocked"
    assert "gap_framed_as_question" in {f.dimension for f in result.findings}


def test_ungrounded_measure_cite_is_a_finding(workspace: Path):
    # A measure not among the declared contracts (measure-grounding is the v1
    # grounded-only enforcement: cites.measures MUST be declared contracts).
    _mutate_brief(
        workspace,
        "measures: [NetSales]\n      dimensions: [division]",
        "measures: [PhantomMeasure]\n      dimensions: [division]",
    )
    result = _run(workspace)
    assert result.status == "blocked"
    assert "ungrounded_cite" in {f.dimension for f in result.findings}


def test_dimension_cite_is_not_grounded_checked_in_v1(workspace: Path):
    # Dimension-grounding against the profile is OUT of v1 scope: a dimension
    # cite is a semantic-model reference (dotted entity.attribute), the v1
    # source-profile carries only bare source columns, and resolving one to the
    # other needs a THIRD artifact the two-input rule forbids. So a not-in-
    # profile dimension must NOT be flagged -- the checker never claims a
    # grounding it cannot actually verify (no false ungrounded_cite; the HIGH
    # from the Opus review). Measure grounding still applies (test above).
    _mutate_brief(workspace, "dimensions: [division]", "dimensions: [product.anything]")
    result = _run(workspace)
    assert result.status == "pass"
    assert not any(f.dimension == "ungrounded_cite" for f in result.findings)


def test_stale_contract_revision_is_a_finding(workspace: Path):
    # A revision sha that does not match the committed contract's current blob.
    _mutate_brief(
        workspace,
        "revision: ",
        "revision: 0000000000000000000000000000000000000000  # was: ",
    )
    result = _run(workspace)
    assert result.status == "blocked"
    assert "stale_contract_revision" in {f.dimension for f in result.findings}


def test_non_literal_stage_is_a_finding(workspace: Path):
    _mutate_brief(workspace, "    stage: change", "    stage: middlebit")
    result = _run(workspace)
    assert result.status == "blocked"
    assert "invalid_stage" in {f.dimension for f in result.findings}


def test_empty_callout_is_a_finding(workspace: Path):
    _mutate_brief(
        workspace,
        "    callout: Net sales rose, driven by the northern region.",
        "    callout: ''",
    )
    result = _run(workspace)
    assert result.status == "blocked"
    assert "empty_callout" in {f.dimension for f in result.findings}


def test_missing_guardrail_basis_is_a_finding(workspace: Path):
    # period-variance is a guardrail-bearing framing; drop Q2's guardrail basis.
    _mutate_brief(
        workspace,
        "    guardrail:\n      basis: same period last year",
        "    guardrail:\n      basis: ''",
    )
    result = _run(workspace)
    assert result.status == "blocked"
    assert "missing_guardrail_basis" in {f.dimension for f in result.findings}


def test_invalid_framing_is_a_finding(workspace: Path):
    # A framing that is not one of the eight cards -- a typo (e.g. a
    # guardrail-bearing framing misspelled) must NOT silently escape the
    # guardrail rule; the framing literal is validated.
    _mutate_brief(workspace, "framing: period-variance", "framing: period-varyance")
    result = _run(workspace)
    assert result.status == "blocked"
    assert "invalid_framing" in {f.dimension for f in result.findings}


def test_story_order_stage_not_a_list_fails_closed(workspace: Path):
    # A stage value that is a scalar/string (author forgot the list brackets)
    # must be a NAMED finding, never a crash (FR-008).
    _mutate_brief(workspace, "  change:    [Q2]", "  change:    Q2")
    result = _run(workspace)
    assert result.status == "blocked"
    assert "story_order_not_a_list" in {f.dimension for f in result.findings}


def test_duplicate_question_id_is_a_finding(workspace: Path):
    # Two questions sharing an id -> ambiguous rank + non-unique binding-map
    # reference; must be flagged, not silently collapsed to one.
    _mutate_brief(workspace, "  - id: Q2", "  - id: Q1")
    result = _run(workspace)
    assert result.status == "blocked"
    assert "duplicate_question_id" in {f.dimension for f in result.findings}


# --------------------------------------------------------------------------- #
# Class (c): fail-closed on missing / unreadable / schema-invalid brief
# --------------------------------------------------------------------------- #


def test_missing_brief_fails_closed(tmp_path: Path):
    (tmp_path / "mappings" / "orders").mkdir(parents=True)
    result = check_narrative(table="orders", repo_root=tmp_path)
    assert result.status == "blocked"
    assert result.grants_approval is False
    assert any("narrative-brief.md" in f.message for f in result.findings)
    assert any(f.dimension == "missing_brief" for f in result.findings)


def test_no_yaml_front_section_fails_closed(workspace: Path):
    brief = workspace / "mappings" / "orders" / "narrative-brief.md"
    brief.write_text("# just prose, no fenced yaml front section\n", encoding="utf-8")
    result = _run(workspace)
    assert result.status == "blocked"
    assert any(f.dimension == "no_front_section" for f in result.findings)


def test_malformed_yaml_fails_closed(workspace: Path):
    brief = workspace / "mappings" / "orders" / "narrative-brief.md"
    brief.write_text("```yaml\n: : not: valid: yaml\n```\n", encoding="utf-8")
    result = _run(workspace)
    assert result.status == "blocked"
    assert any(f.dimension == "malformed_front_section" for f in result.findings)


def test_wrong_schema_literal_fails_closed(workspace: Path):
    _mutate_brief(
        workspace, "schema: seshat.narrative-brief/v1", "schema: something/else"
    )
    result = _run(workspace)
    assert result.status == "blocked"
    assert any(f.dimension == "wrong_schema" for f in result.findings)


def test_never_silent_nothing(workspace: Path):
    # The core FR-008 guarantee: a malformed brief NEVER exits pass-with-nothing.
    brief = workspace / "mappings" / "orders" / "narrative-brief.md"
    brief.write_text("garbage", encoding="utf-8")
    result = _run(workspace)
    assert result.status != "pass"
    assert result.findings  # non-empty


# --------------------------------------------------------------------------- #
# Deferred to Phase B (T010): the visual<->question binding-map orphan checks.
# The three-way map is authored by the Phase-B dashboard-design upgrade and does
# not exist yet. Visible skips, never a silent pass over an absent map.
# --------------------------------------------------------------------------- #


@pytest.mark.skip(
    reason="visual->question binding-map orphan check lands with Phase B / T010"
)
def test_orphan_visual_no_question(): ...


@pytest.mark.skip(reason="page->question coverage check lands with Phase B / T010")
def test_page_missing_question(): ...
