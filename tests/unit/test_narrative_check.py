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

import re
import subprocess
from pathlib import Path

import pytest
import yaml

from seshat.narrative_check import (
    NarrativeCheckResult,
    check_binding_map,
    check_narrative,
)

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
    a clean narrative brief citing the contract's current blob sha. The contract
    lives under ``mappings/<table>/metrics/`` -- the F009 store convention the
    rest of the kit uses (gap_detector, dashboard_coordinator, --metrics-dir);
    NOT a ``contracts/`` dir, which no real workspace ships."""
    table_dir = tmp_path / "mappings" / "orders"
    (table_dir / "metrics").mkdir(parents=True)
    contract = table_dir / "metrics" / "NetSales.yaml"
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
# Phase B (T010): the three-way binding-map checks (visual -> contract ->
# decision-question). The map is authored by the Phase-B dashboard-design
# upgrade and lives at mappings/<table>/design/visual-contract-binding-map.md
# with a machine-readable ``seshat.binding-map/v1`` front section, mirroring the
# brief's fenced-yaml pattern. The checker (``check_binding_map``) reads the map
# AND the brief it names, and reports categorical findings with named blockers:
#   - orphan_visual        : a visual whose decision_question is empty or not a
#                            declared brief question id (FR-005)
#   - page_missing_question: a declared page carrying no decision-question at all
#                            (coverage -- a page must serve >=1 owner decision)
#   - bare_total_headline_visual : a headline (KPI-card) visual whose bound
#                            question is not an overview-stage question -- a bare
#                            total on the headline (FR-006), transitive to the
#                            brief's already-enforced headline comparison rule
# Fail-closed on a missing / unreadable / schema-invalid map, and on an absent
# brief it references -- consistent with the brief-check posture, never a silent
# pass over an absent map.
# --------------------------------------------------------------------------- #


def _clean_binding_map() -> str:
    """A clean three-way map for the ``orders`` workspace: two pages, every
    visual answering a declared brief question, a headline visual on Q1 (an
    overview question) and a visual answering TWO questions (Q1 + Q2) to exercise
    the list-valued ``decision_questions`` form the real worked example needs
    (v03 answers Q1/Q5). Mirrors the taught ``seshat.binding-map/v1`` shape."""
    return """```yaml
schema: seshat.binding-map/v1
table: orders
brief: mappings/orders/narrative-brief.md
pages:
  - id: overview
    regions: [kpi_strip]
  - id: drivers
    regions: [main_insight]
visuals:
  - visual_id: v01
    page: overview
    region: kpi_strip
    visual_type: card
    contract: NetSales
    decision_questions: [Q1]
    headline: true
  - visual_id: v02
    page: drivers
    region: main_insight
    visual_type: bar
    contract: NetSales
    decision_questions: [Q2]
    headline: false
```

# Visual -> contract -> decision-question binding map: orders

The three-way map the design review signs off.
"""


@pytest.fixture()
def mapped_workspace(workspace: Path) -> Path:
    """The clean-brief workspace plus a clean three-way binding map."""
    design_dir = workspace / "mappings" / "orders" / "design"
    design_dir.mkdir(parents=True)
    (design_dir / "visual-contract-binding-map.md").write_text(
        _clean_binding_map(), encoding="utf-8"
    )
    return workspace


def _mutate_map(workspace: Path, old: str, new: str) -> None:
    m = workspace / "mappings" / "orders" / "design" / "visual-contract-binding-map.md"
    text = m.read_text(encoding="utf-8")
    assert old in text, f"fixture drift: {old!r} not in the clean binding map"
    m.write_text(text.replace(old, new, 1), encoding="utf-8")


def _run_map(workspace: Path) -> NarrativeCheckResult:
    return check_binding_map(table="orders", repo_root=workspace)


def test_clean_binding_map_passes(mapped_workspace: Path):
    result = _run_map(mapped_workspace)
    assert result.status == "pass"
    assert result.findings == ()
    assert result.grants_approval is False


def test_clean_binding_map_evidence_states_not_approval(mapped_workspace: Path):
    result = _run_map(mapped_workspace)
    joined = " ".join(result.evidence).lower()
    assert "evidence" in joined and "approval" in joined


def test_visual_answering_two_questions_passes(mapped_workspace: Path):
    # The spec edge case: one visual may answer >1 decision-question (the real
    # worked example's basket-value card answers Q1 AND Q5). Both listed -> no
    # orphan, and because Q1 is overview the headline rule is satisfied.
    _mutate_map(
        mapped_workspace,
        "    decision_questions: [Q1]\n    headline: true",
        "    decision_questions: [Q1, Q2]\n    headline: true",
    )
    result = _run_map(mapped_workspace)
    assert result.status == "pass"
    assert result.findings == ()


def test_orphan_visual_no_question(mapped_workspace: Path):
    # A measure-bearing visual with an empty decision_questions list -> orphan
    # (FR-005: a visual bound to a contract but answering no question is a defect
    # of the same class as an unbound visual).
    _mutate_map(mapped_workspace, "decision_questions: [Q2]", "decision_questions: []")
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert "orphan_visual" in {f.dimension for f in result.findings}
    assert any("v02" in f.locator for f in result.findings)


def test_visual_cites_undeclared_question_is_orphan(mapped_workspace: Path):
    # A decision_question that is not a declared brief question id is also an
    # orphan -- the map cannot reach past the brief's questions.
    _mutate_map(
        mapped_workspace, "decision_questions: [Q2]", "decision_questions: [Q99]"
    )
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert "orphan_visual" in {f.dimension for f in result.findings}
    assert any("Q99" in f.message for f in result.findings)


def test_one_undeclared_among_valid_is_still_orphan(mapped_workspace: Path):
    # A visual listing a valid AND an undeclared question is still an orphan for
    # the undeclared one -- the check is per-question, not "any grounded => ok".
    _mutate_map(
        mapped_workspace, "decision_questions: [Q2]", "decision_questions: [Q2, Q99]"
    )
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert "orphan_visual" in {f.dimension for f in result.findings}
    assert any("Q99" in f.message for f in result.findings)


def test_visual_with_no_contract_is_orphan(mapped_workspace: Path):
    # The CONTRACT leg (FR-005, "orphan in EITHER direction"): a visual with no
    # `contract` field is an orphan -- the three-way map must bind every visual to
    # an approved contract, not just to a question. (The old two-way markdown table
    # got human review; this machine-readable YAML section did not, so the checker
    # must police the contract leg it introduced.)
    _mutate_map(
        mapped_workspace,
        "    visual_type: bar\n    contract: NetSales\n",
        "    visual_type: bar\n",
    )
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert "orphan_visual" in {f.dimension for f in result.findings}
    assert any("v02" in f.locator and "contract" in f.message for f in result.findings)


def test_visual_with_undeclared_contract_is_orphan(mapped_workspace: Path):
    # A `contract` that is not among the brief's declared approved contracts is an
    # orphan -- the map cannot bind a visual to a metric the brief never approved
    # (same grounded-only posture as the brief's measure cites).
    _mutate_map(mapped_workspace, "contract: NetSales", "contract: TotallyFakeMetric")
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert "orphan_visual" in {f.dimension for f in result.findings}
    assert any("TotallyFakeMetric" in f.message for f in result.findings)


def test_page_missing_question(mapped_workspace: Path):
    # A declared page whose only visual carries no question -> the page serves no
    # owner decision (coverage defect). Blank Q2 so page `drivers` has no
    # question-bearing visual.
    _mutate_map(mapped_workspace, "decision_questions: [Q2]", "decision_questions: []")
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    dims = {f.dimension for f in result.findings}
    assert "page_missing_question" in dims
    assert any("drivers" in f.locator for f in result.findings)


def test_unanswered_brief_question_is_a_finding(mapped_workspace: Path):
    # The other orphan direction (FR-005 "either direction"): a brief
    # decision-question that NO visual answers. Q2 is declared in the brief;
    # remove the only visual that answers it (v02) so Q2 goes unanswered.
    _mutate_map(
        mapped_workspace,
        """  - visual_id: v02
    page: drivers
    region: main_insight
    visual_type: bar
    contract: NetSales
    decision_questions: [Q2]
    headline: false
""",
        "",
    )
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert "unanswered_question" in {f.dimension for f in result.findings}
    assert any("Q2" in f.locator or "Q2" in f.message for f in result.findings)


def test_headline_visual_on_nonoverview_question_is_a_finding(mapped_workspace: Path):
    # FR-006: a headline (KPI-card class) visual MUST carry a comparison framing.
    # Structurally, a headline visual answers an overview-stage question (which
    # the brief already forces to name a comparison). A headline answering only a
    # non-overview question is a bare-total headline defect.
    _mutate_map(
        mapped_workspace,
        "    decision_questions: [Q1]\n    headline: true",
        "    decision_questions: [Q2]\n    headline: true",
    )
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert "bare_total_headline_visual" in {f.dimension for f in result.findings}


def test_missing_binding_map_fails_closed(workspace: Path):
    # The brief exists but no three-way map -> Phase B flips map-absence to
    # fail-closed (a design gated on the brief but with no committed map is not
    # reviewable). Never a silent pass over an absent map.
    result = _run_map(workspace)
    assert result.status == "blocked"
    assert result.grants_approval is False
    assert any(f.dimension == "missing_binding_map" for f in result.findings)


def test_binding_map_missing_brief_fails_closed(tmp_path: Path):
    # A map that references a brief which does not exist -> fail closed naming the
    # absent brief (the map's question ids cannot be grounded).
    design_dir = tmp_path / "mappings" / "orders" / "design"
    design_dir.mkdir(parents=True)
    (design_dir / "visual-contract-binding-map.md").write_text(
        _clean_binding_map(), encoding="utf-8"
    )
    result = check_binding_map(table="orders", repo_root=tmp_path)
    assert result.status == "blocked"
    assert any(
        f.dimension in {"missing_brief", "missing_referenced_brief"}
        for f in result.findings
    )


def test_malformed_binding_map_fails_closed(mapped_workspace: Path):
    m = (
        mapped_workspace
        / "mappings"
        / "orders"
        / "design"
        / "visual-contract-binding-map.md"
    )
    m.write_text("```yaml\n: : not: valid: yaml\n```\n", encoding="utf-8")
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert result.status != "pass"
    assert result.findings


def test_binding_map_wrong_schema_fails_closed(mapped_workspace: Path):
    _mutate_map(mapped_workspace, "schema: seshat.binding-map/v1", "schema: other/v9")
    result = _run_map(mapped_workspace)
    assert result.status == "blocked"
    assert any(f.dimension == "wrong_schema" for f in result.findings)


# --------------------------------------------------------------------------- #
# Anti-circularity anchors (the circular-fixture lesson): the schema is proven
# against a REAL committed artifact, not only against fixtures this test wrote.
# --------------------------------------------------------------------------- #

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TAUGHT_EXAMPLE = (
    _REPO_ROOT / "skills" / "bi-analyst-knowledge" / "example-specialty-retail.md"
)
_REAL_MAP = (
    _REPO_ROOT
    / "mappings"
    / "retail_store_sales"
    / "design"
    / "visual-contract-binding-map.md"
)


def _second_yaml_block(text: str) -> str:
    """The SECOND fenced yaml block in the teaching file -- the first teaches the
    brief front section, the second teaches the three-way binding map."""
    blocks = re.findall(r"```ya?ml\s*\n(.*?)\n```", text, re.DOTALL)
    assert len(blocks) >= 2, "teaching file must teach both brief AND binding map"
    return blocks[1]


def test_taught_binding_map_example_parses_and_passes(tmp_path: Path):
    # HONESTY (SC-002-class): the bi-analyst-knowledge pack's OWN taught
    # binding-map example must parse under seshat.binding-map/v1 AND pass the
    # checker against a brief declaring the Q-ids it references. Built from the
    # committed teaching file verbatim -- never a shape invented here (the
    # circular-fixture trap: green on a self-invented format proves nothing).
    taught = _second_yaml_block(_TAUGHT_EXAMPLE.read_text(encoding="utf-8"))
    taught_map = taught.replace("<table>", "orders")
    taught_data = yaml.safe_load(taught_map)

    # Ground the fabricated brief in the taught map ITSELF: declare exactly the
    # Q-ids the map answers (so no unanswered-question orphan) AND exactly the
    # contracts the map binds (so the contract-leg grounding is exercised, not
    # bypassed). A brief with a mismatched single contract would let the honesty
    # test pass hollow -- the advisor's point.
    qids = sorted({q for v in taught_data["visuals"] for q in v["decision_questions"]})
    contracts = sorted({v["contract"] for v in taught_data["visuals"]})
    assert qids, "the taught map must reference decision-question ids"
    assert contracts, "the taught map must bind approved contracts"
    q_blocks = "\n".join(
        f"""  - id: {qid}
    decision: taught decision {qid}
    stage: {"overview" if qid == "Q1" else "why_where"}
    framing: contribution-mix
    cites:
      measures: [{contracts[0]}]
    comparison: {"same period last year" if qid == "Q1" else "none"}
    callout: taught callout {qid}"""
        for qid in qids
    )
    contract_blocks = "\n".join(
        f"  - id: {cid}\n    revision: deadbeef" for cid in contracts
    )
    overview_ids = ", ".join(q for q in qids if q == "Q1")
    other_ids = ", ".join(q for q in qids if q != "Q1")
    brief = f"""```yaml
schema: seshat.narrative-brief/v1
table: orders
source_profile: mappings/orders/source-profile.md
contracts:
{contract_blocks}
questions:
{q_blocks}
story_order:
  overview:  [{overview_ids}]
  change:    []
  why_where: [{other_ids}]
  action:    []
gaps: []
```
# taught brief
"""
    table_dir = tmp_path / "mappings" / "orders"
    (table_dir / "design").mkdir(parents=True)
    (table_dir / "narrative-brief.md").write_text(brief, encoding="utf-8")
    (table_dir / "design" / "visual-contract-binding-map.md").write_text(
        f"# taught map\n\n```yaml\n{taught_map}\n```\n", encoding="utf-8"
    )

    result = check_binding_map(table="orders", repo_root=tmp_path)
    assert result.status == "pass", [f._asdict() for f in result.findings]
    assert result.grants_approval is False


def test_real_worked_example_map_still_needs_phase_b_migration():
    # GUARD (owner-requested): the ONE real committed binding map
    # (retail_store_sales) is still the F011 two-way MARKDOWN pipe-table format
    # with no seshat.binding-map/v1 front section. The checker therefore fails
    # closed (no_front_section) on it -- Phase B ships the checker + the taught
    # example, and migrating this signed-off artifact into the new format is an
    # explicit owner-gated follow-up (Option A). This test makes "DOA on
    # reality" VISIBLE instead of hidden behind fixture-only green: when the map
    # is migrated, this test flips and must be updated deliberately.
    assert _REAL_MAP.is_file(), f"expected the real worked-example map at {_REAL_MAP}"
    result = check_binding_map(table="retail_store_sales", repo_root=_REPO_ROOT)
    assert result.status == "blocked"
    assert any(f.dimension == "no_front_section" for f in result.findings)
