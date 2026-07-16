"""Unit tests for the Dagster adapter redaction module (spec 134, T007/T008).

Every error or output surfaced by the adapter passes through here first:
DSNs, hosts, user names, passwords, and secret-bearing environment values must
never reach evidence, console output, or exception text (FR-008, Principle IX).
"""

from __future__ import annotations

import pytest

from seshat.dagster_adapter import redaction

pytestmark = pytest.mark.unit


class TestRedactText:
    def test_url_dsn_is_scrubbed(self) -> None:
        text = "connect failed: postgresql://alice:s3cret@db.example.com:5432/gold"
        out = redaction.redact_text(text)
        assert "s3cret" not in out
        assert "alice" not in out
        assert "db.example.com" not in out
        assert "[REDACTED-DSN]" in out

    def test_keyword_credentials_are_scrubbed(self) -> None:
        text = "host=10.1.2.3 port=5432 user=svc password=hunter2 dbname=gold"
        out = redaction.redact_text(text)
        assert "hunter2" not in out
        assert "10.1.2.3" not in out
        assert "svc" not in out

    def test_env_secret_values_are_scrubbed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:pw@h:5/d")
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "topsecretvalue")
        text = "error: could not use topsecretvalue or postgresql://u:pw@h:5/d"
        out = redaction.redact_text(text)
        assert "topsecretvalue" not in out
        assert "pw@h" not in out

    def test_plain_text_is_untouched(self) -> None:
        text = "3 orphan FKs in dim_product; reconcile delta 0.07"
        assert redaction.redact_text(text) == text

    def test_none_and_empty_are_safe(self) -> None:
        assert redaction.redact_text("") == ""


class TestRedactPayload:
    def test_nested_payloads_are_scrubbed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "deepsecret")
        payload = {
            "message": "auth failed with deepsecret",
            "detail": ["dsn postgresql://a:b@c/d", {"inner": "password=oops"}],
        }
        out = redaction.redact_payload(payload)
        text = repr(out)
        assert "deepsecret" not in text
        assert "a:b@c" not in text
        assert "oops" not in text

    def test_payload_structure_preserved(self) -> None:
        payload = {"rows": 12, "names": ["a", "b"]}
        assert redaction.redact_payload(payload) == payload
