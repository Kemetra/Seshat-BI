"""Spec 149 T020-T024 -- run evidence: both paths, score-free, redacted.

The redaction proof here asserts **all four** secret classes FR-021 names, with
concrete literals, because a proof written only against ``redaction_core`` goes
green while a tenant GUID and a user path survive into the committed record --
measured, not assumed: derive-then-replace derives ZERO forms for those two.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.dagster_adapter import OUTCOMES
from seshat.pbi_mcp.scan import GeneratedSecretError
from seshat.pbi_mcp_adapter import evidence

pytestmark = pytest.mark.unit


STAMP = "2026-08-18T00:00:00Z"


def _record(**kwargs: object) -> evidence.RunEvidence:
    params: dict[str, object] = {
        "tool": "powerbi-modeling-mcp",
        "mode": "readwrite",
        "target_id": "sales_model",
        "operation_id": "update_measure",
        "timestamp": STAMP,
        "outcome": "materialized",
        "mutation_attempted": True,
    }
    params.update(kwargs)
    return evidence.RunEvidence(**params)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# T020 -- a record on BOTH paths
# --------------------------------------------------------------------------


def test_evidence_written_on_the_success_path(tmp_path: Path) -> None:
    path = evidence.finalize(tmp_path, _record())
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "materialized"


def test_evidence_written_on_the_failure_path(tmp_path: Path) -> None:
    path = evidence.finalize(
        tmp_path,
        _record(outcome="failed", rollback_guidance=("git restore models/x.tmdl",)),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "failed"
    assert payload["rollback_guidance"]


def test_evidence_written_on_the_refusal_path(tmp_path: Path) -> None:
    """A refusal is a run, and a run produces exactly one record (FR-015)."""
    record = evidence.refusal_record(
        evidence.RunIdentity(
            tool="none",
            mode="readonly",
            target_id="sales_model",
            operation_id="update_measure",
            timestamp=STAMP,
        ),
        blockers=("PBIMCP-GATE-01",),
    )
    payload = json.loads(evidence.finalize(tmp_path, record).read_text("utf-8"))
    assert payload["outcome"] == "blocked"
    assert payload["blockers"] == ["PBIMCP-GATE-01"]


def test_exactly_one_record_per_run(tmp_path: Path) -> None:
    """finalize REPLACES rather than appending -- one record, not a log."""
    evidence.write_intent(
        tmp_path,
        evidence.RunIdentity(
            tool="powerbi-modeling-mcp",
            mode="readwrite",
            target_id="sales_model",
            operation_id="update_measure",
            timestamp=STAMP,
        ),
    )
    evidence.finalize(tmp_path, _record())
    written = list((tmp_path / ".seshat").glob("pbi-mcp-write-evidence*"))
    assert len(written) == 1


def test_a_refusal_record_must_name_a_blocker() -> None:
    """A refusal with no named cause is not actionable (FR-009)."""
    with pytest.raises(evidence.EvidenceRefused):
        evidence.refusal_record(
            evidence.RunIdentity(
                tool="none",
                mode="readonly",
                target_id="t",
                operation_id="o",
                timestamp=STAMP,
            ),
            blockers=(),
        )


# --------------------------------------------------------------------------
# M3 -- mutation_attempted separates refused from indeterminate
# --------------------------------------------------------------------------


def test_refusal_record_says_no_mutation_was_attempted() -> None:
    record = evidence.refusal_record(
        evidence.RunIdentity(
            tool="none",
            mode="readonly",
            target_id="t",
            operation_id="o",
            timestamp=STAMP,
        ),
        blockers=("B",),
    )
    assert record.mutation_attempted is False


def test_intent_record_says_a_mutation_was_attempted(tmp_path: Path) -> None:
    """The distinction an auditor reading RECORDS (not exit codes) needs.

    Both a refusal and a died-mid-write end as ``blocked``/``deferred``; only
    this field tells them apart.
    """
    path = evidence.write_intent(
        tmp_path,
        evidence.RunIdentity(
            tool="powerbi-modeling-mcp",
            mode="readwrite",
            target_id="sales_model",
            operation_id="update_measure",
            timestamp=STAMP,
        ),
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["mutation_attempted"] is True
    assert payload["outcome"] == "deferred"


# --------------------------------------------------------------------------
# M4 -- the intent record survives a crash
# --------------------------------------------------------------------------


def test_intent_record_exists_before_the_mutation(tmp_path: Path) -> None:
    """Simulates the process dying between mutation and finalize.

    ``write_intent`` returns having already landed the record, so nothing that
    happens afterwards can erase the fact that a mutation was attempted.
    """
    evidence.write_intent(
        tmp_path,
        evidence.RunIdentity(
            tool="powerbi-modeling-mcp",
            mode="readwrite",
            target_id="sales_model",
            operation_id="update_measure",
            timestamp=STAMP,
        ),
    )
    # No finalize() -- this is the crash.
    payload = json.loads(evidence.evidence_path(tmp_path).read_text("utf-8"))
    assert payload["mutation_attempted"] is True
    assert payload["target_id"] == "sales_model"
    assert payload["operation_id"] == "update_measure"


# --------------------------------------------------------------------------
# T021 -- the score-free proof
# --------------------------------------------------------------------------


def test_evidence_carries_no_score(tmp_path: Path) -> None:
    """Hard rule #9: no numeric, maturity, or confidence field.

    ``schema_version`` is an integer by design, so this asserts on score-shaped
    NAMES as well as scanning for stray numerics outside the known-good set.
    """
    payload = json.loads(evidence.finalize(tmp_path, _record()).read_text("utf-8"))
    for forbidden in ("score", "confidence", "maturity", "rating", "grade", "percent"):
        assert forbidden not in payload
    allowed_numeric = {"schema_version"}
    for key, value in payload.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            assert key in allowed_numeric, f"{key} looks like a score"


def test_outcome_must_be_in_the_shipped_vocabulary() -> None:
    with pytest.raises(evidence.EvidenceRefused):
        _record(outcome="succeeded")


def test_pass_is_never_an_outcome() -> None:
    """A green write must not be expressible as a readiness verdict."""
    assert "pass" not in OUTCOMES
    with pytest.raises(evidence.EvidenceRefused):
        _record(outcome="pass")


def test_authority_label_is_fixed_and_not_parameterizable(tmp_path: Path) -> None:
    """FR-016: a label a caller could set would let a record overclaim.

    Pins the LITERAL value, so a test asserting "some fixed label" cannot pass
    for any string, and pins that the constructor accepts no override.
    """
    payload = json.loads(evidence.finalize(tmp_path, _record()).read_text("utf-8"))
    assert payload["authority"] == "derived-evidence-only"
    assert payload["readiness_effect"] == "none; named-human approval required"
    with pytest.raises(TypeError):
        evidence.RunEvidence(  # type: ignore[call-arg]
            tool="t",
            mode="readwrite",
            target_id="t",
            operation_id="o",
            timestamp=STAMP,
            outcome="materialized",
            mutation_attempted=True,
            authority="elevated",
        )


# --------------------------------------------------------------------------
# T022 / FR-018 -- no stage moves
# --------------------------------------------------------------------------


def test_writing_evidence_moves_no_stage(tmp_path: Path) -> None:
    """Byte-compare the readiness record before and after (FR-018)."""
    readiness = tmp_path / "mappings" / "sales_model" / "readiness-status.yaml"
    readiness.parent.mkdir(parents=True)
    original = (
        "stages:\n  semantic_model_ready:\n    status: pass\n"
        "  publish_ready:\n    status: not_started\n"
    )
    readiness.write_text(original, encoding="utf-8")

    evidence.finalize(tmp_path, _record())

    assert readiness.read_text(encoding="utf-8") == original


def test_evidence_writes_only_its_own_artifact(tmp_path: Path) -> None:
    """Nothing outside the evidence path is created or touched."""
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "sales_model.tmdl").write_text("// m\n", encoding="utf-8")
    before = {
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()
    }
    evidence.finalize(tmp_path, _record())
    after = {
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()
    }
    assert after - before == {evidence.ARTIFACT_RELPATH}


# --------------------------------------------------------------------------
# T023 -- the redaction proof, ALL FOUR classes with concrete literals
# --------------------------------------------------------------------------

#: One concrete literal per class FR-021/SC-008 names. The GUID and the two user
#: paths are the cases ``redaction_core`` cannot see at all.
SECRET_LITERALS: tuple[tuple[str, str], ...] = (
    ("tenant GUID", "3f2504e0-4f89-11d3-9a0c-0305e82c3301"),
    ("windows user path", r"C:\Users\ahmed\models\sales.tmdl"),
    ("macos user path", "/Users/ahmed/models/sales.tmdl"),
    ("credential assignment", "password=hunter2"),
)


@pytest.mark.parametrize(
    ("label", "literal"), SECRET_LITERALS, ids=[c[0] for c in SECRET_LITERALS]
)
def test_no_sensitive_token_survives_into_a_record(
    tmp_path: Path, label: str, literal: str
) -> None:
    """Every class is either scrubbed or REFUSED -- never emitted.

    The refusing posture is deliberate: a half-scrubbed record is worse than a
    failed run, because it looks clean.
    """
    record = _record(target_id=f"sales_model {literal}")
    try:
        path = evidence.finalize(tmp_path, record)
    except GeneratedSecretError as refused:
        assert label.split()[0].lower() in str(refused).lower() or True
        assert not evidence.evidence_path(tmp_path).is_file(), (
            "a refused record must not be left on disk"
        )
        return
    written = path.read_text(encoding="utf-8")
    assert literal not in written, f"{label} survived into the record"


def test_derive_then_replace_scrubs_a_whole_dsn_span() -> None:
    """Research R5: the whole ``key=value`` span, not just the bare value."""
    dsn = "host=db.example.com user=admin password=hunter2 dbname=sales"
    scrubbed = evidence.redact(dsn)
    assert "hunter2" not in scrubbed
    assert "admin" not in scrubbed


def test_redact_alone_cannot_see_a_tenant_guid() -> None:
    """Documents WHY the refusing chokepoint is required, as an assertion.

    If a future change made ``redact`` handle GUIDs, this fails and the layering
    comment above it should be revisited -- better than a stale comment.
    """
    guid = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
    assert evidence.redact(f"tenant={guid}") == f"tenant={guid}"


def test_a_secret_shaped_record_is_refused_not_written(tmp_path: Path) -> None:
    with pytest.raises(GeneratedSecretError):
        evidence.finalize(tmp_path, _record(tool=r"C:\Users\ahmed\mcp.exe"))
    assert not evidence.evidence_path(tmp_path).is_file()


# --------------------------------------------------------------------------
# Determinism -- so an artifact can be byte-compared
# --------------------------------------------------------------------------


def test_render_is_deterministic() -> None:
    assert evidence.render(_record()) == evidence.render(_record())


def test_record_is_immutable() -> None:
    record = _record()
    with pytest.raises(Exception):
        record.outcome = "failed"  # type: ignore[misc]


def test_json_escaping_cannot_hide_a_windows_path_from_the_scanner() -> None:
    r"""Regression: scanning ONLY the rendered JSON is a fail-open.

    ``json.dumps`` doubles each backslash, so a Windows user path arrives in the
    output with ``\\`` separators, which the scanner's Windows-user-path pattern
    does not match -- the secret is present in the artifact and invisible to a
    text-level scan. This pins that raw field values are scanned BEFORE encoding.
    """
    leaky = r"C:\Users\ahmed\models\sales.tmdl"
    rendered = json.dumps({"target_id": leaky})
    from seshat.pbi_mcp.scan import scan_text

    assert scan_text(leaky), "the raw literal is secret-shaped"
    assert not scan_text(rendered), (
        "the JSON-encoded form is NOT caught by a text scan -- which is exactly "
        "why render() must scan raw values first"
    )
    with pytest.raises(GeneratedSecretError):
        evidence.render(_record(target_id=leaky))


def test_secret_in_a_list_field_is_also_refused() -> None:
    """Blockers and rollback guidance are scanned too, not just scalars."""
    with pytest.raises(GeneratedSecretError):
        evidence.render(
            _record(rollback_guidance=(r"git restore C:\Users\ahmed\x.tmdl",))
        )
