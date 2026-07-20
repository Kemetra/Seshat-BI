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

    def test_odbc_style_credentials_are_scrubbed(self) -> None:
        text = "Driver=x;Server=y;UID=svcuser;PWD=odbcsecret;Database=gold"
        out = redaction.redact_text(text)
        assert "odbcsecret" not in out
        assert "svcuser" not in out

    def test_env_secret_values_are_scrubbed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:pw@h:5/d")
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "topsecretvalue")
        text = "error: could not use topsecretvalue or postgresql://u:pw@h:5/d"
        out = redaction.redact_text(text)
        assert "topsecretvalue" not in out
        assert "pw@h" not in out

    def test_non_secret_analytics_defaults_are_not_over_redacted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Codex P2 (#348): with `.env` now loaded into the process env, the
        fixed-vocabulary config values (ANALYTICS_DB_PORT / _SSLMODE / _ENGINE)
        must NOT be treated as secrets -- redacting them would mangle legitimate
        output (the literal 'require'/'25060'/'postgres'). The real password IS
        still redacted."""
        monkeypatch.setenv("ANALYTICS_DB_PORT", "25060")
        monkeypatch.setenv("ANALYTICS_DB_SSLMODE", "require")
        monkeypatch.setenv("ANALYTICS_DB_ENGINE", "postgres")
        monkeypatch.setenv("ANALYTICS_DB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
        monkeypatch.setenv("ANALYTICS_DB_TRUST_CERT", "true")
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "realsecretpw")

        text = (
            "connect to port 25060 sslmode require trust true "
            "driver ODBC Driver 18 for SQL Server but pw realsecretpw"
        )
        out = redaction.redact_text(text)

        # fixed-vocabulary config words survive (no over-redaction)
        assert "25060" in out and "require" in out
        assert "true" in out and "ODBC Driver 18 for SQL Server" in out
        assert "realsecretpw" not in out  # the credential is still scrubbed

    def test_plain_text_is_untouched(self) -> None:
        text = "3 orphan FKs in dim_product; reconcile delta 0.07"
        assert redaction.redact_text(text) == text


class TestRedactionRobustness357:
    """#357: an explicit SECRET-key set replaces the 'ANALYTICS_DB_* prefix minus
    enumerated non-secret allowlist' + len>=4 gate. Config keys are non-secret by
    default (no churn); short secret values are redacted (no under-redaction)."""

    def test_short_secret_value_is_redacted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The under-redaction fix: a short HOST/USER (< 4 chars) in a reformatted
        (non key=value) driver error must be redacted, not printed verbatim."""
        for key in list(__import__("os").environ):
            if key == "DATABASE_URL" or key.startswith("ANALYTICS_DB_"):
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("ANALYTICS_DB_HOST", "db")
        monkeypatch.setenv("ANALYTICS_DB_USER", "sa")

        text = 'connection to server at "db" failed for user "sa"'
        out = redaction.redact_text(text)

        assert "db" not in out.replace("[REDACTED-ENV]", "")  # host scrubbed
        assert '"sa"' not in out  # user scrubbed

    def test_future_config_key_is_non_secret_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The over-redaction fix (structural): a NEW ANALYTICS_DB_* config key
        the module has never heard of must NOT be redacted -- non-secret by
        default, no enumerated allowlist entry needed."""
        monkeypatch.setenv("ANALYTICS_DB_APP_NAME", "seshat_bi_app")

        text = "the app_name seshat_bi_app connected cleanly"
        out = redaction.redact_text(text)

        assert "seshat_bi_app" in out  # a future config value is NOT clobbered

    def test_snowflake_target_labels_are_not_redacted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The tool reads ANALYTICS_DB_SCHEMA / _ROLE / _WAREHOUSE (Snowflake),
        but none is in any dialect's _secret_keys -- they are target/authz labels,
        not credentials (matching dbt's SESHAT_DBT_SCHEMA). They must survive
        redaction verbatim; only host/name/user/password/account are secret."""
        monkeypatch.setenv("ANALYTICS_DB_SCHEMA", "gold_shadow")
        monkeypatch.setenv("ANALYTICS_DB_ROLE", "analyst_ro")
        monkeypatch.setenv("ANALYTICS_DB_WAREHOUSE", "compute_wh_s")

        text = "role analyst_ro on warehouse compute_wh_s writing gold_shadow"
        out = redaction.redact_text(text)

        assert "analyst_ro" in out
        assert "compute_wh_s" in out
        assert "gold_shadow" in out

    def test_credential_keys_still_redacted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The credential subset (HOST/NAME/USER/PASSWORD/ACCOUNT) stays redacted
        at any length."""
        monkeypatch.setenv("ANALYTICS_DB_HOST", "db.internal.example")
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "hunter2secret")
        monkeypatch.setenv("ANALYTICS_DB_ACCOUNT", "acme-xy12345")

        text = "host db.internal.example pw hunter2secret account acme-xy12345"
        out = redaction.redact_text(text)

        assert "db.internal.example" not in out
        assert "hunter2secret" not in out
        assert "acme-xy12345" not in out

    def test_database_url_still_redacted_via_dsn_pass(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Preserved coverage: DATABASE_URL is a DSN, scrubbed by the DSN pass --
        the refactor must not drop it from the secret handling."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:pw@h.example:5432/gold")
        text = "connect failed: postgresql://u:pw@h.example:5432/gold"
        out = redaction.redact_text(text)
        assert "pw@h.example" not in out

    def test_generic_token_env_still_redacted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Preserved coverage: a non-ANALYTICS secret (*_TOKEN) must still redact
        via the generic keyword matcher -- the refactor must not narrow to only
        the ANALYTICS namespace."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_notarealtoken12345")
        text = "auth failed with ghp_notarealtoken12345"
        out = redaction.redact_text(text)
        assert "ghp_notarealtoken12345" not in out

    def test_short_generic_secret_value_is_not_a_redaction_wildcard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """#357 regression guard: dropping the len gate is scoped to the KNOWN
        credential set. A generic `_SECRET_ENV_RE`-matched key with a tiny value
        (a flag `1`) must keep the length floor -- otherwise every '1' in the
        payload (run ids, exit codes) would be clobbered."""
        for key in list(__import__("os").environ):
            if key.endswith("_TOKEN") or key.startswith("ANALYTICS_DB_"):
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("MY_DEPLOY_TOKEN", "1")  # a flag, not a credential

        text = "run 1 of 1 exited with code 1"
        out = redaction.redact_text(text)

        assert out == text  # no digit '1' clobbered

    def test_value_is_redacted_before_regex_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """#357 (Codex #4 / dialect.py order): exact secret values are replaced
        BEFORE the keyword regex, so a keyword-shaped fragment inside a secret
        value cannot leave its head/tail surviving."""
        # A pathological password whose middle looks like a keyword pair.
        monkeypatch.setenv("ANALYTICS_DB_PASSWORD", "abc;user=bob;xyz")

        text = "auth string abc;user=bob;xyz rejected"
        out = redaction.redact_text(text)

        # The WHOLE secret value is gone -- no 'abc;' / ';xyz' fragment survives.
        assert "abc;" not in out
        assert ";xyz" not in out
        assert "bob" not in out

    def test_none_and_empty_are_safe(self) -> None:
        assert redaction.redact_text("") == ""


class TestRedactPayload:
    def test_nested_payloads_are_scrubbed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
