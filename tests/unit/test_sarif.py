from seshat.core import Finding, Severity
from seshat.sarif import finding_fingerprint, sarif_document


def _finding(severity: Severity = Severity.ERROR) -> Finding:
    return Finding("S1", severity, "silver is premature", "warehouse/silver/x.sql:12:3")


def test_sarif_has_required_21_shape_and_location() -> None:
    document = sarif_document([_finding()])
    result = document["runs"][0]["results"][0]
    assert document["version"] == "2.1.0"
    assert result["ruleId"] == "S1"
    assert result["locations"][0]["physicalLocation"] == {
        "artifactLocation": {"uri": "warehouse/silver/x.sql"},
        "region": {"startLine": 12, "startColumn": 3},
    }


def test_sarif_severity_parity() -> None:
    results = sarif_document(
        [_finding(Severity.INFO), _finding(Severity.WARNING), _finding(Severity.ERROR)]
    )["runs"][0]["results"]
    assert sorted(result["level"] for result in results) == ["error", "note", "warning"]


def test_fingerprint_is_stable_and_material() -> None:
    finding = _finding()
    assert finding_fingerprint(finding) == finding_fingerprint(finding)
    changed = Finding(finding.rule_id, finding.severity, "different", finding.locator)
    assert finding_fingerprint(finding) != finding_fingerprint(changed)


def test_sarif_order_is_deterministic() -> None:
    first = _finding()
    second = Finding("A1", Severity.INFO, "ok", "docs/a.md")
    assert sarif_document([first, second]) == sarif_document([second, first])


def test_non_file_locator_has_no_location() -> None:
    result = sarif_document(
        [Finding("A1", Severity.INFO, "skipped", "(foreign repo)")]
    )["runs"][0]["results"][0]
    assert "locations" not in result
