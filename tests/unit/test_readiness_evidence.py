"""Unit tests for the live-validation evidence recorder (spec 057).

`build_gold_ready_block(findings, table_identity, run_mode, timestamp=None, dsn=None)`
is a PURE, stdlib-only serializer: it maps validate.py `Finding[]` + a run mode into a
proposed `gold_ready` readiness block (a dict). EMIT-only -- it writes no file. It never
sets `status: pass` (FR-012), never mutates its inputs (FR-007), scrubs any DSN out of
recorded text (FR-006), and emits no numeric score (FR-005).
"""

from __future__ import annotations

import pytest

from seshat.core import Finding, Severity
from seshat.readiness_evidence import build_gold_ready_block

pytestmark = pytest.mark.unit


def _err(msg="dup PK", loc="raw.tbl"):
    return Finding(rule_id="V-RC2", severity=Severity.ERROR, message=msg, locator=loc)


def _warn(msg="soft issue", loc="raw.tbl"):
    return Finding(
        rule_id="V-RC15", severity=Severity.WARNING, message=msg, locator=loc
    )


# T002: clean live run -> evidence, no blockers, NOT pass, no score
def test_clean_live_run_evidence_no_pass():
    b = build_gold_ready_block([], "schema.tbl", run_mode="live")
    assert b["evidence"]  # non-empty
    assert any("schema.tbl" in e for e in b["evidence"])
    assert b["blocking_reasons"] == []
    assert b["status"] != "pass"  # FR-012: recorder never self-grants pass
    assert b["status"] == "warning"
    assert "score" not in b and "confidence" not in b  # FR-005


# T003: N ERROR findings -> N blocking_reasons, status blocked
def test_error_findings_become_blockers():
    findings = [_err("dup A", "t.a"), _err("dup B", "t.b")]
    b = build_gold_ready_block(findings, "schema.tbl", run_mode="live")
    assert b["status"] == "blocked"
    assert len(b["blocking_reasons"]) == 2
    joined = " ".join(b["blocking_reasons"])
    assert "V-RC2" in joined and "dup A" in joined and "t.a" in joined


# T004: WARNING findings -> warnings[], never blockers; warning-only run is warning
def test_warnings_recorded_not_blocking():
    b = build_gold_ready_block([_warn("w1")], "schema.tbl", run_mode="live")
    assert b["status"] == "warning"
    assert b["blocking_reasons"] == []
    assert any("w1" in w for w in b["warnings"])


# T005: DSN embedded in a finding message is scrubbed; redaction idempotent
def test_dsn_scrubbed_from_recorded_text():
    dsn = "postgresql://admin:secret@dbhost:5432/prod"
    findings = [_err(f"connect failed: {dsn}", "t.a")]
    b = build_gold_ready_block(findings, "schema.tbl", run_mode="live", dsn=dsn)
    blob = " ".join(b["blocking_reasons"])
    assert "secret" not in blob and "admin" not in blob and "dbhost" not in blob
    # idempotent: feeding the already-redacted block text back changes nothing further
    b2 = build_gold_ready_block(
        [_err(blob, "t.a")], "schema.tbl", run_mode="live", dsn=dsn
    )
    assert "secret" not in " ".join(b2["blocking_reasons"])


# T005b: overlapping DSN components are redacted longest-first (no host leak)
def test_dsn_overlapping_components_redacted():
    # username "db" is a substring of host "dbhost.internal".
    dsn = "postgresql://db:pw@dbhost.internal:5432/prod"
    findings = [_err("connect to dbhost.internal failed for user db", "t.a")]
    b = build_gold_ready_block(findings, "schema.tbl", run_mode="live", dsn=dsn)
    blob = " ".join(b["blocking_reasons"])
    assert "dbhost.internal" not in blob  # the full host must not survive
    assert "host.internal" not in blob  # nor a mangled remnant of it


# T005c: percent-encoded DSN credentials are redacted in their DECODED form too
def test_dsn_percent_encoded_credentials_redacted():
    # DSN encodes user "svc/etl" and password "p@ss" as %2F / %40; a driver message
    # prints the DECODED values.
    dsn = "postgresql://svc%2Fetl:p%40ss@dbhost/prod"
    findings = [_err("auth failed for user svc/etl with p@ss", "t.a")]
    b = build_gold_ready_block(findings, "schema.tbl", run_mode="live", dsn=dsn)
    blob = " ".join(b["blocking_reasons"])
    assert "svc/etl" not in blob
    assert "p@ss" not in blob


# T005d: the DB-NAME (DSN path) is scrubbed too. The hand-rolled _scrub only
# covered host/user/password; a "database ... does not exist" error leaked the
# db-name into recorded readiness evidence. Delegating to the shared hardened
# decomposition (redaction_core) closes it -- the same class as #385, #384-review.
def test_dsn_db_name_redacted():
    dsn = "postgresql://admin:pw@dbhost/secret_prod_db"
    findings = [_err('database "secret_prod_db" does not exist', "t.a")]
    b = build_gold_ready_block(findings, "schema.tbl", run_mode="live", dsn=dsn)
    blob = " ".join(b["blocking_reasons"])
    assert "secret_prod_db" not in blob, blob


# T006: deferred mode -> blocked with deferred-boundary reason, no clean evidence
def test_deferred_mode_blocked_no_clean_evidence():
    b = build_gold_ready_block([], "schema.tbl", run_mode="deferred")
    assert b["status"] == "blocked"
    assert any(
        "defer" in r.lower() or "no live" in r.lower() or "pending" in r.lower()
        for r in b["blocking_reasons"]
    )
    # must NOT read as a completed clean run
    assert not any("passed" in e.lower() for e in b.get("evidence", []))


# T007: never mutates input findings list / objects
def test_inputs_not_mutated():
    findings = [_err("x", "t.a"), _warn("y", "t.b")]
    before = list(findings)
    build_gold_ready_block(findings, "schema.tbl", run_mode="live")
    assert findings == before  # same objects, same order, unchanged


# T008: missing/blank table_identity raises, never emits a placeholder identity
def test_blank_identity_raises():
    with pytest.raises(ValueError):
        build_gold_ready_block([], "", run_mode="live")
    with pytest.raises(ValueError):
        build_gold_ready_block([], "   ", run_mode="live")


# T009: deterministic -- same inputs (incl. explicit timestamp) -> identical output
def test_deterministic_output():
    args = ([_err("x", "t.a")], "schema.tbl")
    b1 = build_gold_ready_block(*args, run_mode="live", timestamp="2026-07-01")
    b2 = build_gold_ready_block(*args, run_mode="live", timestamp="2026-07-01")
    assert b1 == b2
