"""Repository tests for the contributor surfaces (spec 120, US6).

FR-034: structured entry paths exist for defects, capabilities, packs,
compatibility, and starter contributions. FR-035: the PR template prompts for
readiness stage, scope, tests, evidence, human decisions, and data safety.
FR-036: every lane declares scope, acceptance, verification, forbidden scope,
and maintainer response. FR-037: the newcomer path needs at most three
documents and none of the governance archive.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]
_FORMS = {
    "bug": _REPO / ".github/ISSUE_TEMPLATE/bug.yml",
    "feature": _REPO / ".github/ISSUE_TEMPLATE/feature.yml",
    "pack": _REPO / ".github/ISSUE_TEMPLATE/pack.yml",
    "compatibility": _REPO / ".github/ISSUE_TEMPLATE/compatibility.yml",
    "starter": _REPO / ".github/ISSUE_TEMPLATE/starter.yml",
}
_LANES = _REPO / "docs/contributing/contribution-lanes.yaml"
_FIRST = _REPO / "docs/contributing/first-contribution.md"
_PR_TEMPLATE = _REPO / ".github/pull_request_template.md"

_LANE_REQUIRED_FIELDS = {
    "id",
    "intended_contributor",
    "summary",
    "owned_files",
    "forbidden_scope",
    "prerequisites",
    "acceptance",
    "verification",
    "expected_evidence",
    "difficulty",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(_FORMS))
def test_issue_form_is_valid_and_triageable(name: str) -> None:
    form = _load(_FORMS[name])
    assert form["name"]
    assert form["description"]
    assert "needs-triage" in form["labels"]
    body_types = [element["type"] for element in form["body"]]
    assert any(kind != "markdown" for kind in body_types)
    required = [
        element
        for element in form["body"]
        if element.get("validations", {}).get("required")
        or any(
            option.get("required")
            for option in element.get("attributes", {}).get("options", [])
            if isinstance(option, dict)
        )
    ]
    assert required, f"{name} form has no required triage field"


@pytest.mark.parametrize("name", ["bug", "compatibility", "pack", "starter"])
def test_data_safety_is_a_required_assertion(name: str) -> None:
    text = _FORMS[name].read_text(encoding="utf-8").lower()
    assert "secret" in text or "synthetic" in text
    form = _load(_FORMS[name])
    checkbox_groups = [
        element for element in form["body"] if element["type"] == "checkboxes"
    ]
    assert any(
        option.get("required")
        for group in checkbox_groups
        for option in group["attributes"]["options"]
    )


def test_bug_form_requires_reproduction_and_expected_vs_observed() -> None:
    form = _load(_FORMS["bug"])
    ids = {element.get("id") for element in form["body"]}
    assert {"version", "reproduction", "expected", "observed"} <= ids


def test_pr_template_prompts_for_every_evidence_dimension() -> None:
    text = _PR_TEMPLATE.read_text(encoding="utf-8").lower()
    for prompt in (
        "readiness stage",
        "scope",
        "tests",
        "evidence",
        "human decisions",
        "secret",
    ):
        assert prompt in text, f"PR template lacks the {prompt!r} prompt"
    assert "score" not in text.replace("never a score", "")


def test_lanes_declare_the_full_contract() -> None:
    document = _load(_LANES)
    lanes = document["lanes"]
    assert len(lanes) >= 5
    ids = [lane["id"] for lane in lanes]
    assert len(ids) == len(set(ids))
    for lane in lanes:
        missing = _LANE_REQUIRED_FIELDS - set(lane)
        assert not missing, f"lane {lane.get('id')} missing {sorted(missing)}"
        assert lane["owned_files"], lane["id"]
        assert lane["forbidden_scope"], lane["id"]
        assert lane["verification"], lane["id"]
    assert document["maintainer_response"]["first_reply_within"]


def test_expected_lane_topics_are_covered() -> None:
    ids = {lane["id"] for lane in _load(_LANES)["lanes"]}
    assert {
        "kpi-contract-templates",
        "synthetic-fixtures",
        "dialect-renderings",
        "accessibility-checks",
        "blocker-explanations",
    } <= ids


def test_starter_form_lists_every_lane() -> None:
    form = _load(_FORMS["starter"])
    dropdowns = [element for element in form["body"] if element["type"] == "dropdown"]
    options = {
        option for dropdown in dropdowns for option in dropdown["attributes"]["options"]
    }
    lane_ids = {lane["id"] for lane in _load(_LANES)["lanes"]}
    assert lane_ids <= options


def test_newcomer_path_is_three_documents_and_skips_the_archive() -> None:
    text = _FIRST.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "three documents" in lowered
    assert "contribution-lanes.yaml" in text
    assert "CONTRIBUTING.md" in text
    # FR-037: the starter path must not require the governance archive.
    for archive in ("constitution.md", "roadmap.md", "specs/"):
        assert archive not in text, f"newcomer path requires {archive}"


def test_contributing_links_the_newcomer_path() -> None:
    text = (_REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "docs/contributing/first-contribution.md" in text
    assert "docs/contributing/contribution-lanes.yaml" in text
