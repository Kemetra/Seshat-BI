"""dbt and Dagster output surfaces scrub secret-shaped spans, not only known values.

Token literals are assembled from parts so this file never carries a
secret-shaped literal itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_GH_TOKEN = "gh" + "p_" + "abcdefghijklmnopqrstuvwxyz0123456789"
_CLOUD_KEY = "AK" + "IA" + "IOSFODNN7EXAMPLE"
_GUID = "12345678-1234-1234-1234-" + "123456789abc"


def test_redaction_core_scrubs_token_key_and_guid_shapes() -> None:
    from seshat.redaction_core import scrub_secret_shaped

    text = f"token {_GH_TOKEN} and {_CLOUD_KEY} and {_GUID}"
    scrubbed, labels = scrub_secret_shaped(text)
    for value in (_GH_TOKEN, _CLOUD_KEY, _GUID):
        assert value not in scrubbed
    assert labels


def test_already_redacted_assignment_is_left_readable() -> None:
    from seshat.redaction_core import scrub_secret_shaped

    scrubbed, _ = scrub_secret_shaped("password=[REDACTED] failed", keep_redacted=True)
    assert scrubbed == "password=[REDACTED] failed"


def test_pbi_mcp_scan_reuses_the_shared_pattern_table() -> None:
    from seshat import redaction_core
    from seshat.pbi_mcp import scan

    assert scan.SECRET_PATTERNS is redaction_core.SECRET_PATTERNS


def test_dbt_sanitize_scrubs_secret_shaped_spans() -> None:
    from seshat.dbt.redaction import sanitize

    text = f"token {_GH_TOKEN} and {_CLOUD_KEY} and {_GUID}"
    cleaned = sanitize(text, (), Path("."))
    assert isinstance(cleaned, str)
    for value in (_GH_TOKEN, _CLOUD_KEY, _GUID):
        assert value not in cleaned


def test_dbt_sanitize_keeps_non_string_evidence_values_typed() -> None:
    from seshat.dbt.redaction import sanitize

    cleaned = sanitize({"count": 3, "ok": True, "none": None}, (), Path("."))
    assert cleaned == {"count": 3, "ok": True, "none": None}


def test_dagster_redaction_knows_the_forwarded_dbt_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from seshat.dagster_adapter.redaction import redact_text

    monkeypatch.setenv("SESHAT_DBT_HOST", "db-internal.example.org")
    monkeypatch.setenv("SESHAT_DBT_USER", "svc_loader")
    monkeypatch.setenv("SESHAT_DBT_DBNAME", "warehouse_prod")
    monkeypatch.setenv("SESHAT_DBT_SCHEMA", "seshat_dbt_shadow")
    message = (
        'connection to server at "db-internal.example.org" failed for user '
        '"svc_loader" database "warehouse_prod" schema seshat_dbt_shadow_silver'
    )
    out = redact_text(message)
    for value in ("db-internal.example.org", "svc_loader", "warehouse_prod"):
        assert value not in out
    # The non-secret shadow schema name stays verbatim (documented decision).
    assert "seshat_dbt_shadow_silver" in out


def test_dagster_redaction_scrubs_secret_shaped_spans() -> None:
    from seshat.dagster_adapter.redaction import redact_text

    out = redact_text(f"leaked {_GH_TOKEN} / {_CLOUD_KEY}")
    assert _GH_TOKEN not in out
    assert _CLOUD_KEY not in out


def test_dbt_runner_redacts_an_exception_message(tmp_path: Path) -> None:
    """An OSError passed to the text sanitizer must be rendered THEN redacted."""
    from seshat.dbt import runner

    context = type(
        "Ctx",
        (),
        {"environment": {"SESHAT_DBT_PASSWORD": "hunter2"}, "repo_root": tmp_path},
    )()
    exc = FileNotFoundError(2, "No such file", f"{tmp_path}/dbt.exe password hunter2")
    detail = runner._sanitized_text(exc, context)
    assert "hunter2" not in detail
    assert str(tmp_path) not in detail
