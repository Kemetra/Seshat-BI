from __future__ import annotations

import pytest

from seshat.disclosure import scan_disclosure

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("document", "rule"),
    [
        ({"dsn": "postgresql://user:secret@db/prod"}, "secret_field"),
        ({"note": "mysql://user:pw@db/prod"}, "connection_string"),
        ({"path": r"C:\\Users\\person\\secret.txt"}, "absolute_path"),
        ({"path": "/home/person/secret.txt"}, "absolute_path"),
        ({"email": "person@example.com"}, "pii_value"),
        ({"raw_values": ["a", "b"]}, "raw_value_array"),
        ({"sample_values": list(range(25))}, "raw_value_array"),
    ],
)
def test_sensitive_shapes_block_disclosure(document: object, rule: str) -> None:
    result = scan_disclosure(document)
    assert result["status"] == "blocked"
    assert any(finding["rule"] == rule for finding in result["findings"])


def test_safe_readiness_projection_passes() -> None:
    result = scan_disclosure(
        {
            "table": "orders",
            "source_path": "mappings/orders/readiness-status.yaml",
            "status": "blocked",
            "blocking_reasons": ["grain needs data-owner review"],
            "evidence": ["mappings/orders/source-profile.md"],
        }
    )
    assert result["status"] == "pass"
    assert result["inspected_values"] >= 5
    assert result["findings"] == []


def test_messages_do_not_echo_sensitive_values() -> None:
    secret = "postgresql://admin:super-secret@private-host/prod"
    result = scan_disclosure({"note": secret})
    assert secret not in str(result)
    assert "super-secret" not in str(result)
    assert "private-host" not in str(result)


@pytest.mark.parametrize(
    "document",
    [
        {"database_url": "postgresql+psycopg2://u:p" + "@h/d"},
        {"note": "failed reading C:\\Users\\bob\\x.csv"},
        {"conn": "host=h password=p"},
        {"DB_PASSWORD": "hunter2"},
        {"x": "mssql+pyodbc://sa:pw" + "@h/db"},
        {"p": "/root/.pgpass"},
        {"p": "copied from \\\\fileserver\\share\\x.csv"},
    ],
)
def test_common_dsn_credential_and_path_shapes_block(document: object) -> None:
    assert scan_disclosure(document)["status"] == "blocked"


@pytest.mark.parametrize(
    "document",
    [
        {"token_count": "12"},
        {"connection_status": "ok"},
        {"link": "https://example.com/home/page"},
        {"path": "mappings/orders/source-profile.md"},
    ],
)
def test_benign_keys_urls_and_relative_paths_pass(document: object) -> None:
    assert scan_disclosure(document)["status"] == "pass"
