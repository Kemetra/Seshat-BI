"""US2 JSON format tests for the review pack exporter (spec 081)."""

import json
import re

import pytest

from retail.review_pack_export import FindingRecord, Pack, Section

pytestmark = pytest.mark.unit


def _contract_pack() -> Pack:
    return Pack(
        schema_version="1.0",
        title="<TABLE>: <STAGE> review pack",
        generated_at=None,
        source_note="composed by <producer>, <date>",
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
                findings=(
                    FindingRecord(
                        rule_id="S5",
                        severity="WARNING",
                        message="type discipline check",
                        locator="warehouse/silver/<table>.sql:12",
                    ),
                ),
            ),
        ),
    )


def test_json_roundtrips_and_matches_contract():
    """T008: to_json round-trips and matches json-schema.md field-for-field."""
    from retail.review_pack_export import to_json

    doc = to_json(_contract_pack())
    reloaded = json.loads(json.dumps(doc))
    assert reloaded["schema_version"] == "1.0"
    assert reloaded["title"] == "<TABLE>: <STAGE> review pack"
    assert reloaded["generated_at"] is None
    assert reloaded["source_note"] == "composed by <producer>, <date>"
    assert len(reloaded["sections"]) == 2
    s0, s1 = reloaded["sections"]
    assert s0["name"] == "Gate requirement"
    assert s0["status"] == "pass"
    assert s0["blocking_reasons"] == []
    assert s1["status"] == "blocked"
    assert s1["blocking_reasons"][0] == "grain not confirmed unique on data"


def test_json_embedded_finding_matches_finding_to_dict():
    """T009: an embedded FindingRecord keeps the exact B2 four-field shape."""
    from retail.core import Finding, Severity
    from retail.review_pack_export import to_json

    synthetic = Finding(
        rule_id="S5",
        severity=Severity.WARNING,
        message="type discipline check",
        locator="warehouse/silver/<table>.sql:12",
    )
    # Build a section from Finding.to_dict() directly (the documented convention).
    fd = synthetic.to_dict()
    pack = Pack(
        title="t",
        sections=(
            Section(
                name="S",
                status="blocked",
                findings=(FindingRecord(**fd),),
            ),
        ),
    )
    doc = to_json(pack)
    got = doc["sections"][0]["findings"][0]
    assert set(got.keys()) == {"rule_id", "severity", "message", "locator"}
    assert got == fd


def test_json_omits_findings_key_when_none():
    """T010: a section with no findings omits the 'findings' key entirely."""
    from retail.review_pack_export import to_json

    pack = Pack(title="t", sections=(Section(name="S", status="pass"),))
    doc = to_json(pack)
    assert "findings" not in doc["sections"][0]


def test_json_no_score_or_count_keys():
    """T011: no key is a score/health/confidence/percentage or completeness count."""
    from retail.review_pack_export import to_json

    doc = to_json(_contract_pack())
    forbidden = re.compile(r".*(_score|_health|_confidence|_of_|_percent|_pct)$")
    blob = json.dumps(doc)

    def _walk_keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert not forbidden.match(k), f"forbidden key: {k}"
                _walk_keys(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk_keys(v)

    _walk_keys(doc)
    assert "%" not in blob


def test_json_unrecognized_token_carries_recognized_false():
    """T012: an unrecognized status carries recognized:false + the verbatim token."""
    from retail.review_pack_export import to_json

    pack = Pack(title="t", sections=(Section(name="S", status="frobnicated"),))
    doc = to_json(pack)
    sec = doc["sections"][0]
    assert sec["status"] == "frobnicated"
    assert sec["recognized"] is False


def test_json_recognized_key_omitted_for_known_token():
    """A recognized token omits the 'recognized' field (present only when false)."""
    from retail.review_pack_export import to_json

    pack = Pack(title="t", sections=(Section(name="S", status="pass"),))
    assert "recognized" not in to_json(pack)["sections"][0]
