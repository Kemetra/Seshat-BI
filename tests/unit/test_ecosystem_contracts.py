from __future__ import annotations

from pathlib import Path

import pytest

from seshat.artifact_identity import (
    artifact_identity,
    canonical_relative_path,
    resolve_within,
)
from seshat.ecosystem_contracts import (
    ContractError,
    parse_schema_version,
    require_supported_schema,
)

pytestmark = pytest.mark.unit


def test_schema_version_parses_major_minor() -> None:
    assert parse_schema_version("1.0") == (1, 0)
    assert parse_schema_version("12.34") == (12, 34)


@pytest.mark.parametrize("value", ["1", "v1.0", "1.0.0", "", None, 1])
def test_schema_version_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ContractError):
        parse_schema_version(value)


def test_unknown_schema_major_fails_closed() -> None:
    with pytest.raises(ContractError, match="unsupported schema major"):
        require_supported_schema({"schema_version": "2.0"}, supported_major=1)


def test_newer_minor_is_additive_and_accepted() -> None:
    assert require_supported_schema(
        {"schema_version": "1.99", "future_optional": True}, supported_major=1
    ) == (1, 99)


def test_canonical_path_and_hash_are_repository_relative(tmp_path: Path) -> None:
    artifact = tmp_path / "mappings" / "orders" / "source-map.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("table: orders\n", encoding="utf-8")

    assert canonical_relative_path(tmp_path, artifact) == (
        "mappings/orders/source-map.yaml"
    )
    identity = artifact_identity(tmp_path, artifact, kind="source_map")
    assert identity["path"] == "mappings/orders/source-map.yaml"
    assert len(identity["sha256"]) == 64
    assert identity["verification"] == "verified"
    assert str(tmp_path) not in str(identity)


def test_path_escape_and_absolute_outside_path_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside workspace"):
        resolve_within(tmp_path, tmp_path.parent / "secret.txt")
    with pytest.raises(ValueError, match="outside workspace"):
        resolve_within(tmp_path, Path("..") / "secret.txt")


def test_missing_artifact_is_reported_without_a_fake_hash(tmp_path: Path) -> None:
    identity = artifact_identity(tmp_path, "missing.txt", kind="other")
    assert identity["verification"] == "missing"
    assert identity["sha256"] is None
