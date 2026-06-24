from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.sql import (
    s1_snake_case_identifiers,
    s2_medallion_schemas,
    s3_vw_prefix,
    s4a_migration_numbering,
    s4b_guard_form,
)

pytestmark = pytest.mark.unit

# Canonical fixture content lives in flat tracked files (read-only source); each
# test stages copies into its own tmp_path so tests never write into the real
# repo tree and never depend on a file another test wrote.
FIXTURES = Path(__file__).parent.parent / "fixtures" / "sql"


def _stage(tmp_path: Path, name: str) -> str:
    """Copy fixture `name` into tmp_path/warehouse/ and return its rel path."""
    src = FIXTURES / name
    dest_dir = tmp_path / "warehouse"
    dest_dir.mkdir(exist_ok=True)
    (dest_dir / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return f"warehouse/{name}"


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


def test_s1_passes_snake_case(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s1_s2.sql"))
    assert list(s1_snake_case_identifiers(ctx)) == []


def test_s1_flags_quoted_caps(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s1_quoted_caps.sql"))
    findings = list(s1_snake_case_identifiers(ctx))
    assert findings
    assert all(f.rule_id == "S1" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


def test_s2_passes_raw_amount_column(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s1_s2.sql"))
    assert list(s2_medallion_schemas(ctx)) == []


def test_s2_flags_create_schema_raw(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s2_create_schema_raw.sql"))
    findings = list(s2_medallion_schemas(ctx))
    assert len(findings) >= 1
    assert any("raw" in f.message for f in findings)
    assert all(f.rule_id == "S2" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


def test_s2_exempts_warehouse_readme(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "warehouse/README.md")  # not a .sql -> never scanned
    assert list(s2_medallion_schemas(ctx)) == []


def test_s3_passes_prefixed_views(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s3_vw.sql"))
    assert list(s3_vw_prefix(ctx)) == []


def test_s3_flags_unprefixed_view(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s3_no_prefix.sql"))
    findings = list(s3_vw_prefix(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "S3"
    assert findings[0].severity is Severity.ERROR
    assert findings[0].locator == "warehouse/fail_s3_no_prefix.sql:1"


def test_s4a_passes_contiguous_unique(tmp_path: Path) -> None:
    ctx = _ctx(
        tmp_path,
        "warehouse/migrations/0001_init.sql",
        "warehouse/migrations/0002_add_sales.sql",
    )
    assert list(s4a_migration_numbering(ctx)) == []


def test_s4a_flags_bad_name(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, "warehouse/migrations/1_init.sql")
    findings = list(s4a_migration_numbering(ctx))
    assert any(f.rule_id == "S4a" for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)
    assert all(":" not in f.locator.rsplit(".sql", 1)[-1] for f in findings)


def test_s4a_flags_gap(tmp_path: Path) -> None:
    ctx = _ctx(
        tmp_path,
        "warehouse/migrations/0001_init.sql",
        "warehouse/migrations/0003_skip.sql",
    )
    findings = list(s4a_migration_numbering(ctx))
    assert any("gap" in f.message or "contiguous" in f.message for f in findings)


def test_s4a_flags_duplicate(tmp_path: Path) -> None:
    ctx = _ctx(
        tmp_path,
        "warehouse/migrations/0001_init.sql",
        "warehouse/migrations/0001_again.sql",
    )
    findings = list(s4a_migration_numbering(ctx))
    assert any("duplicate" in f.message for f in findings)


def test_s4b_passes_guarded_forms(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "pass_s4b_guarded.sql"))
    assert list(s4b_guard_form(ctx)) == []


def test_s4b_warns_on_bare_create_and_alter(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, _stage(tmp_path, "fail_s4b_bare.sql"))
    findings = list(s4b_guard_form(ctx))
    assert len(findings) == 2
    assert all(f.rule_id == "S4b" for f in findings)
    assert all(f.severity is Severity.WARNING for f in findings)
    assert {f.locator for f in findings} == {
        "warehouse/fail_s4b_bare.sql:1",
        "warehouse/fail_s4b_bare.sql:2",
    }
