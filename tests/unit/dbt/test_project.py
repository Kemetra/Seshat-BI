from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from seshat.dbt.contracts import WorkingSet

pytestmark = pytest.mark.unit

MAP_REVISION = "a" * 40


@dataclass(frozen=True)
class ProjectFixture:
    profile_literal: bool = False
    target_schema: str = "seshat_dbt_shadow"
    selector_name: str = "seshat_table_orders"
    citation_revision: str = MAP_REVISION
    cite_column: bool = True


def _working_set(root: Path) -> WorkingSet:
    mapping = root / "mappings/orders"
    mapping.mkdir(parents=True, exist_ok=True)
    source_map = mapping / "source-map.yaml"
    readiness = mapping / "readiness-status.yaml"
    questions = mapping / "unresolved-questions.md"
    source_map.write_text("meta:\n  table_id: orders\n", encoding="utf-8")
    readiness.write_text("stages: {}\n", encoding="utf-8")
    questions.write_text("Gate status: CLEARED\n", encoding="utf-8")
    return WorkingSet(
        repo_root=root,
        table_id="orders",
        mapping_dir=mapping,
        source_map=source_map,
        readiness_status=readiness,
        unresolved_questions=questions,
        source_map_revision=MAP_REVISION,
        source_map_sha256="b" * 64,
    )


def _project_yaml() -> str:
    return "\n".join(
        [
            "name: seshat_bi",
            "version: 1.0.0",
            "config-version: 2",
            "profile: seshat_bi_warehouse",
            "model-paths: [models]",
            "models:",
            "  seshat_bi:",
            "    staging:",
            "      +schema: silver",
            "",
        ]
    )


def _selectors_yaml(selector_name: str) -> str:
    return "\n".join(
        [
            "selectors:",
            f"  - name: {selector_name}",
            "    definition:",
            "      method: tag",
            "      value: seshat_table_orders",
            "",
        ]
    )


def _profile_yaml(fixture: ProjectFixture) -> str:
    host = (
        "private-host"
        if fixture.profile_literal
        else "{{ env_var('SESHAT_DBT_HOST') }}"
    )
    return "\n".join(
        [
            "seshat_bi_warehouse:",
            "  target: shadow",
            "  outputs:",
            "    shadow:",
            "      type: postgres",
            f'      host: "{host}"',
            "      port: \"{{ env_var('SESHAT_DBT_PORT', '5432') | int }}\"",
            "      user: \"{{ env_var('SESHAT_DBT_USER') }}\"",
            "      password: \"{{ env_var('SESHAT_DBT_PASSWORD') }}\"",
            "      dbname: \"{{ env_var('SESHAT_DBT_DBNAME') }}\"",
            "      schema: \"{{ env_var('SESHAT_DBT_SCHEMA', "
            f"'{fixture.target_schema}') }}}}\"",
            "      threads: 4",
            "      sslmode: \"{{ env_var('SESHAT_DBT_SSLMODE', 'prefer') }}\"",
            "",
        ]
    )


def _model_yaml(fixture: ProjectFixture) -> str:
    column_meta = (
        "\n".join(
            [
                "        meta:",
                "          seshat:",
                "            source_columns: [order_id]",
            ]
        )
        if fixture.cite_column
        else ""
    )
    return "\n".join(
        [
            "version: 2",
            "models:",
            "  - name: stg_orders",
            "    config:",
            "      tags: [seshat_table_orders]",
            "    meta:",
            "      seshat:",
            "        table_id: orders",
            "        source_map: mappings/orders/source-map.yaml",
            f"        source_map_revision: {fixture.citation_revision}",
            "        grain: one row per order",
            "        business_key: [order_id]",
            "        authority: derived",
            "    columns:",
            "      - name: order_id",
            column_meta,
            "",
        ]
    )


def _write_project(root: Path, fixture: ProjectFixture | None = None) -> WorkingSet:
    fixture = fixture or ProjectFixture()
    working_set = _working_set(root)
    project = root / "dbt"
    model_dir = project / "models/staging/orders"
    model_dir.mkdir(parents=True)
    (project / "dbt_project.yml").write_text(_project_yaml(), encoding="utf-8")
    (project / "selectors.yml").write_text(
        _selectors_yaml(fixture.selector_name), encoding="utf-8"
    )
    (root / "profiles.example.yml").write_text(_profile_yaml(fixture), encoding="utf-8")
    (model_dir / "stg_orders.sql").write_text(
        "select order_id from {{ source('bronze', 'orders') }}\n",
        encoding="utf-8",
    )
    (model_dir / "_models.yml").write_text(_model_yaml(fixture), encoding="utf-8")
    return working_set


def test_valid_project_returns_selector_schemas_and_contracts(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)

    result = validate_project(tmp_path, working_set)

    assert result.valid is True
    assert result.selector_name == "seshat_table_orders"
    assert result.profile_name == "seshat_bi_warehouse"
    assert result.target_name == "shadow"
    assert result.schemas.silver == "seshat_dbt_shadow_silver"
    assert result.schemas.gold == "seshat_dbt_shadow_gold"
    assert result.schemas.audit == "seshat_dbt_shadow_audit"
    assert len(result.model_contracts) == 1
    contract = result.model_contracts[0]
    assert contract.name == "stg_orders"
    assert contract.table_id == "orders"
    assert contract.source_map == "mappings/orders/source-map.yaml"
    assert contract.source_map_revision == MAP_REVISION
    assert contract.grain == "one row per order"
    assert contract.business_key == ("order_id",)
    assert contract.authority == "derived"
    assert len(contract.columns) == 1
    assert contract.columns[0].name == "order_id"
    assert contract.columns[0].source_columns == ("order_id",)
    assert contract.columns[0].derivation is None
    assert result.blocking_reasons == ()


def test_project_fingerprint_is_content_based_and_ignores_runtime_dirs(
    tmp_path: Path,
) -> None:
    from seshat.dbt.project import fingerprint_project

    _write_project(tmp_path)
    first = fingerprint_project(tmp_path)
    os.utime(tmp_path / "dbt/dbt_project.yml", None)
    (tmp_path / "dbt/target").mkdir()
    (tmp_path / "dbt/target/manifest.json").write_text("changed", encoding="utf-8")
    (tmp_path / "dbt/logs").mkdir()
    (tmp_path / "dbt/logs/dbt.log").write_text("changed", encoding="utf-8")

    assert fingerprint_project(tmp_path) == first

    model = tmp_path / "dbt/models/staging/orders/stg_orders.sql"
    model.write_text(model.read_text(encoding="utf-8") + "-- changed\n")
    assert fingerprint_project(tmp_path) != first


def test_profile_rejects_literal_connection_values(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(profile_literal=True))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_PROFILE_LITERAL_VALUE" in {b.code for b in result.blocking_reasons}


@pytest.mark.parametrize(
    "target_schema",
    ["silver", "gold", "public", "Unsafe-Name", "1shadow", "shadow;drop"],
)
def test_unsafe_target_schema_is_rejected(tmp_path: Path, target_schema: str) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(target_schema=target_schema))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_SHADOW_SCHEMA_UNSAFE" in {b.code for b in result.blocking_reasons}


def test_missing_governed_selector_is_rejected(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(
        tmp_path, ProjectFixture(selector_name="another_selector")
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_SELECTOR_MISSING" in {b.code for b in result.blocking_reasons}


def test_stale_model_citation_is_rejected(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(citation_revision="c" * 40))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_MODEL_CITATION_STALE" in {b.code for b in result.blocking_reasons}


def _append_model(root: Path, subdir: str, model_yaml: str) -> None:
    """Add a second model's _models.yml under dbt/models/<subdir>/."""
    model_dir = root / "dbt" / "models" / subdir
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "_models.yml").write_text(model_yaml, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q")


# A readiness-status.yaml whose Mapping Ready gate is ALLOWED: status pass + a
# valid named-human approval row. Paired with a CLEARED unresolved-questions
# mirror, evaluate_mapping_gate returns allowed.
_GATE_PASS_READINESS = "\n".join(
    [
        "stages:",
        "  mapping_ready:",
        "    status: pass",
        "approvals:",
        "  - stage: mapping_ready",
        "    owner: Test Owner (data_owner)",
        "    at: '2026-07-16'",
        "    note: approved for test",
        "",
    ]
)
# Mapping Ready still blocked (status not pass, no approval) -- the gate refuses it
# even when the map is tracked and clean.
_GATE_BLOCKED_READINESS = "stages:\n  mapping_ready:\n    status: blocked\n"


def _write_mapping_working_set(
    root: Path,
    table_id: str,
    complete: bool = True,
    committed: bool = False,
    gate_ok: bool = True,
) -> None:
    """Write a table's mapping dir. complete=True writes the full 3-file working set
    (source-map + readiness-status + unresolved-questions) that resolve_working_set
    requires; complete=False omits unresolved-questions.md (a partial mapping).
    committed=True git-adds + commits the source map so it is tracked and clean
    (resolve_working_set also requires that); committed=False leaves it untracked.
    gate_ok=True writes a readiness whose Mapping Ready gate is allowed; gate_ok=
    False writes one still blocked (evaluate_mapping_gate refuses it)."""
    mapping = root / "mappings" / table_id
    mapping.mkdir(parents=True, exist_ok=True)
    (mapping / "source-map.yaml").write_text(
        f"meta:\n  table_id: {table_id}\n", encoding="utf-8"
    )
    (mapping / "readiness-status.yaml").write_text(
        _GATE_PASS_READINESS if gate_ok else _GATE_BLOCKED_READINESS,
        encoding="utf-8",
    )
    if complete:
        (mapping / "unresolved-questions.md").write_text(
            "Gate status: CLEARED\n", encoding="utf-8"
        )
    if committed:
        _git(root, "add", f"mappings/{table_id}/source-map.yaml")
        _git(root, "commit", "-q", "-m", f"add {table_id} map")


def _tagged_model_yaml(name: str, tag: str, table_id: str) -> str:
    return "\n".join(
        [
            "version: 2",
            "models:",
            f"  - name: {name}",
            "    config:",
            f"      tags: [{tag}]",
            "    meta:",
            "      seshat:",
            f"        table_id: {table_id}",
            f"        source_map: mappings/{table_id}/source-map.yaml",
            f"        source_map_revision: {MAP_REVISION}",
            "        grain: one row per thing",
            "        business_key: [thing_id]",
            "        authority: derived",
            "    columns:",
            "      - name: thing_id",
            "        meta:",
            "          seshat:",
            "            source_columns: [thing_id]",
            "",
        ]
    )


def test_model_tagged_for_nonexistent_table_is_orphan_rejected(tmp_path: Path) -> None:
    """A model tagged seshat_table_<bogus> (no committed mapping) must block.

    This is the only guard against a mistyped/phantom selector tag once validation
    is partitioned per table: such a model matches no real governed table, so no
    table's validate run would otherwise ever check it. It must be an orphan
    blocker, not silently skipped as "some other table's model".
    """
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)  # governed table = orders
    _append_model(
        tmp_path,
        "staging/bogus",
        _tagged_model_yaml("stg_bogus", "seshat_table_bogus", "bogus"),
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_MODEL_ORPHANED" in {b.code for b in result.blocking_reasons}


def test_model_for_another_governed_table_is_out_of_scope(tmp_path: Path) -> None:
    """A model belonging to a DIFFERENT real governed table is skipped, not flagged.

    When validating table X, a model tagged for table Y -- where Y has its own
    committed mapping working set -- is out of scope (it is validated when Y runs).
    It must NOT raise a selector/citation/orphan blocker against X.
    """
    from seshat.dbt.project import validate_project

    _init_repo(tmp_path)
    working_set = _write_project(tmp_path)  # validating table = orders
    # A second real governed table "widgets" with a COMPLETE working set that is
    # also git-tracked + clean -- so resolve_working_set succeeds for it, which is
    # what makes skipping its models here safe.
    _write_mapping_working_set(tmp_path, "widgets", complete=True, committed=True)
    _append_model(
        tmp_path,
        "staging/widgets",
        _tagged_model_yaml("stg_widgets", "seshat_table_widgets", "widgets"),
    )

    result = validate_project(tmp_path, working_set)

    # orders is fully valid; the widgets model neither validated here nor flagged.
    assert result.valid is True, [b.code for b in result.blocking_reasons]


def test_model_for_uncommitted_mapping_table_is_orphan_rejected(tmp_path: Path) -> None:
    """A model tagged for a table whose map is present but NOT git-committed must
    block, not skip.

    Regression for the deepest partition hole (the same class as the phantom-tag
    and partial-mapping holes): a table can have all three mapping files yet still
    be non-validatable because resolve_working_set also requires the source map to
    be git-tracked and clean. If "governed" checked only file existence, such a
    table's models would be skipped under the current table AND never validated
    under their own (validation stops at the untracked/dirty gate). The governed
    bar therefore delegates to resolve_working_set itself, not a file check.
    """
    from seshat.dbt.project import validate_project

    _init_repo(tmp_path)
    working_set = _write_project(tmp_path)  # validating table = orders
    # "widgets" has all 3 files but its map is NOT committed (untracked).
    _write_mapping_working_set(tmp_path, "widgets", complete=True, committed=False)
    _append_model(
        tmp_path,
        "staging/widgets",
        _tagged_model_yaml("stg_widgets", "seshat_table_widgets", "widgets"),
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_MODEL_ORPHANED" in {b.code for b in result.blocking_reasons}


def test_model_for_gate_blocked_table_is_orphan_rejected(tmp_path: Path) -> None:
    """A model tagged for a table with a tracked, clean map but a still-BLOCKED
    Mapping Ready gate must block, not skip.

    Regression for the same partition hole one layer deeper: resolve_working_set
    succeeding is not the whole precondition a real validate run enforces --
    _validated_project also requires evaluate_mapping_gate to be allowed before it
    reaches model checking. A table whose map is committed but whose gate is still
    blocked (unapproved) can never reach model validation on its own run, so if it
    counted as governed here its models would be skipped and never checked. The
    governed bar therefore mirrors the entry point's FULL precondition set
    (resolve_working_set AND the mapping gate), not just the working-set resolve.
    """
    from seshat.dbt.project import validate_project

    _init_repo(tmp_path)
    working_set = _write_project(tmp_path)  # validating table = orders
    # "widgets" map is committed (tracked + clean) but its Mapping Ready gate is
    # still blocked -- resolve_working_set succeeds, the gate does not.
    _write_mapping_working_set(
        tmp_path, "widgets", complete=True, committed=True, gate_ok=False
    )
    _append_model(
        tmp_path,
        "staging/widgets",
        _tagged_model_yaml("stg_widgets", "seshat_table_widgets", "widgets"),
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_MODEL_ORPHANED" in {b.code for b in result.blocking_reasons}


def test_model_for_partial_mapping_table_is_orphan_rejected(tmp_path: Path) -> None:
    """A model tagged for a table whose mapping is INCOMPLETE must block, not skip.

    Regression for a partition hole: a table with source-map + readiness-status but
    no unresolved-questions.md cannot be validated (resolve_working_set requires all
    three). If such a table counted as "governed" for the skip decision, its models
    would be skipped under the current table AND never checked under their own
    (validation always fails there), escaping every citation/contract/orphan check.
    The governed bar must match resolve_working_set's 3-file bar exactly.
    """
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)  # validating table = orders
    # "widgets" is only PARTIALLY mapped (missing unresolved-questions.md).
    _write_mapping_working_set(tmp_path, "widgets", complete=False)
    _append_model(
        tmp_path,
        "staging/widgets",
        _tagged_model_yaml("stg_widgets", "seshat_table_widgets", "widgets"),
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_MODEL_ORPHANED" in {b.code for b in result.blocking_reasons}


def test_model_tag_from_other_table_but_contract_cites_current_is_validated(
    tmp_path: Path,
) -> None:
    """A model tagged for another table but whose contract cites THIS table is
    validated here (and its tag/contract mismatch caught), never silently skipped.

    Regression for the second partition hole: attributing by tag alone would skip a
    model whose selector tag was copied from another real governed table, even
    though its meta.seshat.table_id still cites the table under validation. dbt's
    selector:seshat_table_<current> would not select it either, so the mis-tagged
    current-table model would vanish from the build with no blocker. Attribution by
    tag OR contract keeps it in scope, where _check_model_selector flags the tag.
    """
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)  # validating table = orders
    # "widgets" is a real, fully-governed other table.
    _write_mapping_working_set(tmp_path, "widgets", complete=True)
    # A model tagged for widgets but whose contract cites orders (the current table).
    mismatched = "\n".join(
        [
            "version: 2",
            "models:",
            "  - name: stg_mislabeled",
            "    config:",
            "      tags: [seshat_table_widgets]",  # foreign tag
            "    meta:",
            "      seshat:",
            "        table_id: orders",  # contract cites the CURRENT table
            "        source_map: mappings/orders/source-map.yaml",
            f"        source_map_revision: {MAP_REVISION}",
            "        grain: one row per order",
            "        business_key: [order_id]",
            "        authority: derived",
            "    columns:",
            "      - name: order_id",
            "        meta:",
            "          seshat:",
            "            source_columns: [order_id]",
            "",
        ]
    )
    _append_model(tmp_path, "staging/mislabeled", mismatched)

    result = validate_project(tmp_path, working_set)

    # In scope for orders (contract cites it), so the foreign tag is caught here --
    # not silently skipped as "widgets' model".
    assert result.valid is False
    assert "DBT_MODEL_SELECTOR_MISSING" in {b.code for b in result.blocking_reasons}


def test_missing_column_citation_is_rejected(tmp_path: Path) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path, ProjectFixture(cite_column=False))

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_COLUMN_CITATION_MISSING" in {b.code for b in result.blocking_reasons}


def test_generic_project_files_cannot_contain_worked_table_answers(
    tmp_path: Path,
) -> None:
    from seshat.dbt.project import validate_project

    working_set = _write_project(tmp_path)
    macros = tmp_path / "dbt/macros"
    macros.mkdir()
    (macros / "generic.sql").write_text(
        "{% macro generic() %}retail_store_sales{% endmacro %}\n",
        encoding="utf-8",
    )

    result = validate_project(tmp_path, working_set)

    assert result.valid is False
    assert "DBT_GENERIC_EXAMPLE_LEAK" in {b.code for b in result.blocking_reasons}
