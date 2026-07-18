"""Static validation for the governed dbt project and model citations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import PROFILE_NAME, TARGET_NAME
from .contracts import (
    Blocker,
    ColumnCitation,
    ModelContract,
    ProjectValidation,
    ShadowSchemas,
    WorkingSet,
)

_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")
_PROTECTED_SCHEMAS = frozenset({"bronze", "silver", "gold", "public"})
_LAYERS = frozenset({"silver", "gold", "audit"})
_RUNTIME_DIRS = frozenset({"target", "logs", "dbt_packages"})
_ALLOWED_DERIVATIONS = frozenset(
    {"surrogate_key", "date_spine", "unknown_member", "parity_measure"}
)
_PROFILE_ENV = {
    "host": "SESHAT_DBT_HOST",
    "port": "SESHAT_DBT_PORT",
    "user": "SESHAT_DBT_USER",
    "password": "SESHAT_DBT_PASSWORD",
    "dbname": "SESHAT_DBT_DBNAME",
    "schema": "SESHAT_DBT_SCHEMA",
    "sslmode": "SESHAT_DBT_SSLMODE",
}
_EXAMPLE_TOKENS = ("retail_store_sales", "c086", "pharmacy")


@dataclass(frozen=True, slots=True)
class _ContractContext:
    selector_name: str
    table_id: str
    source_map: str
    source_map_revision: str


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return None


def fingerprint_project(repo_root: Path) -> str:
    """Hash sorted dbt source paths and bytes, excluding runtime outputs."""

    root = Path(repo_root).resolve()
    project_dir = root / "dbt"
    digest = hashlib.sha256()
    if not project_dir.is_dir():
        return digest.hexdigest()
    for path in sorted(project_dir.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative_project = path.relative_to(project_dir)
        if _RUNTIME_DIRS.intersection(relative_project.parts):
            continue
        relative_repo = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative_repo).to_bytes(4, "big"))
        digest.update(relative_repo)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _env_reference(value: Any, key: str) -> tuple[bool, str | None]:
    if not isinstance(value, str):
        return False, None
    pattern = re.compile(
        rf"^\s*\{{\{{\s*env_var\('{re.escape(key)}'"
        r"(?:\s*,\s*'([^']*)')?\s*\)(?:\s*\|\s*int)?\s*\}\}\s*$"
    )
    match = pattern.fullmatch(value)
    return (match is not None, match.group(1) if match else None)


def _invalid_profile(blockers: list[Blocker], message: str) -> None:
    blockers.append(Blocker("DBT_PROFILE_INVALID", message))


def _profile_output(document: Any, blockers: list[Blocker]) -> dict[str, Any] | None:
    if not isinstance(document, dict):
        _invalid_profile(blockers, "profiles.example.yml is missing or invalid")
        return None
    profile = document.get(PROFILE_NAME)
    if not isinstance(profile, dict) or profile.get("target") != TARGET_NAME:
        _invalid_profile(
            blockers,
            "profile must define seshat_bi_warehouse target shadow",
        )
        return None
    outputs = profile.get("outputs")
    output = outputs.get(TARGET_NAME) if isinstance(outputs, dict) else None
    if not isinstance(output, dict) or output.get("type") != "postgres":
        _invalid_profile(blockers, "shadow output must use the Postgres adapter")
        return None
    return output


def _profile_schema_default(output: dict[str, Any], blockers: list[Blocker]) -> str:
    schema_default: str | None = None
    for field, env_key in _PROFILE_ENV.items():
        valid, default = _env_reference(output.get(field), env_key)
        if not valid:
            blockers.append(
                Blocker(
                    "DBT_PROFILE_LITERAL_VALUE",
                    f"profile field {field} must use env_var('{env_key}')",
                )
            )
        if field == "schema":
            schema_default = default
    return schema_default or ""


def _validate_profile_threads(output: dict[str, Any], blockers: list[Blocker]) -> None:
    threads = output.get("threads")
    if not isinstance(threads, int) or threads < 1:
        blockers.append(
            Blocker("DBT_PROFILE_INVALID", "profile threads must be a positive integer")
        )


def _profile(
    root: Path,
    blockers: list[Blocker],
    explicit_target_schema: str | None,
) -> str:
    output = _profile_output(_load_yaml(root / "profiles.example.yml"), blockers)
    if output is None:
        return explicit_target_schema or ""
    schema_default = _profile_schema_default(output, blockers)
    _validate_profile_threads(output, blockers)
    if explicit_target_schema is not None:
        return explicit_target_schema
    return schema_default


def _schemas(target_schema: str, blockers: list[Blocker]) -> ShadowSchemas:
    safe = bool(_IDENTIFIER.fullmatch(target_schema)) and (
        target_schema not in _PROTECTED_SCHEMAS
    )
    if not safe:
        blockers.append(
            Blocker(
                "DBT_SHADOW_SCHEMA_UNSAFE",
                "target schema must be a safe non-production Postgres identifier",
            )
        )
    return ShadowSchemas(
        silver=f"{target_schema}_silver",
        gold=f"{target_schema}_gold",
        audit=f"{target_schema}_audit",
    )


def _nested_config_values(value: Any) -> list[tuple[str | None, Any]]:
    if isinstance(value, dict):
        return list(value.items())
    if isinstance(value, list):
        return [(None, nested) for nested in value]
    return []


def _configured_layers(value: Any) -> list[Any]:
    layers: list[Any] = []
    for key, nested in _nested_config_values(value):
        if key == "+schema":
            layers.append(nested)
        else:
            layers.extend(_configured_layers(nested))
    return layers


def _selector_rows(document: Any) -> list[Any]:
    rows = document.get("selectors") if isinstance(document, dict) else None
    return rows if isinstance(rows, list) else []


def _named_selector(rows: list[Any], selector_name: str) -> dict[str, Any] | None:
    for row in rows:
        if isinstance(row, dict) and row.get("name") == selector_name:
            return row
    return None


def _valid_selector(selector: dict[str, Any] | None, selector_name: str) -> bool:
    if selector is None:
        return False
    definition = selector.get("definition")
    if not isinstance(definition, dict):
        return False
    return (definition.get("method"), definition.get("value")) == (
        "tag",
        selector_name,
    )


def _selector(
    project_dir: Path,
    table_id: str,
    blockers: list[Blocker],
) -> str:
    selector_name = f"seshat_table_{table_id}"
    rows = _selector_rows(_load_yaml(project_dir / "selectors.yml"))
    if not _valid_selector(_named_selector(rows, selector_name), selector_name):
        blockers.append(
            Blocker(
                "DBT_SELECTOR_MISSING",
                f"selectors.yml must define tag selector {selector_name}",
            )
        )
    return selector_name


def _column_input(raw: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
        return None
    meta = raw.get("meta")
    seshat = meta.get("seshat") if isinstance(meta, dict) else None
    return raw["name"], seshat if isinstance(seshat, dict) else {}


def _source_columns(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        return ()
    sources = tuple(item for item in value if isinstance(item, str) and item.strip())
    return sources if len(sources) == len(value) else ()


def _derivation(value: Any) -> str | None:
    if isinstance(value, str) and value in _ALLOWED_DERIVATIONS:
        return value
    return None


def _column_citation(
    model_name: str,
    raw: Any,
    blockers: list[Blocker],
) -> ColumnCitation | None:
    column = _column_input(raw)
    if column is None:
        blockers.append(
            Blocker(
                "DBT_COLUMN_CITATION_MISSING",
                f"{model_name} has an invalid column",
            )
        )
        return None
    name, seshat = column
    sources = _source_columns(seshat.get("source_columns"))
    derivation = _derivation(seshat.get("derivation"))
    if not sources and derivation is None:
        blockers.append(
            Blocker(
                "DBT_COLUMN_CITATION_MISSING",
                f"{model_name}.{name} needs source_columns or a governed derivation",
            )
        )
        return None
    return ColumnCitation(
        name=name,
        source_columns=sources,
        derivation=derivation,
    )


def _property_rows(path: Path) -> list[Any]:
    document = _load_yaml(path)
    rows = document.get("models") if isinstance(document, dict) else None
    return rows if isinstance(rows, list) else []


def _model_name(row: Any) -> str | None:
    if isinstance(row, dict) and isinstance(row.get("name"), str):
        return row["name"]
    return None


_SESHAT_TABLE_TAG = re.compile(r"^seshat_table_([a-z][a-z0-9_]*)$")


def _is_validatable_table(root: Path, table_id: str) -> bool:
    """True iff a real ``validate --table <table_id>`` run would reach model
    checking -- i.e. the table can ACTUALLY be validated on its own run.

    This is the single authority for "governed enough to absorb another table's
    skipped models". It mirrors EVERY precondition the CLI entry point
    (``_validated_project``) enforces before it reaches ``validate_project``'s
    model stage: (1) ``resolve_working_set`` succeeds (full mapping working set +
    the source map git-tracked, clean, and revision-resolvable), and (2) the
    Mapping Ready gate (``evaluate_mapping_gate``) is allowed. Both are leaf checks
    -- neither re-enters ``_model_contracts`` -- so this is recursion-safe; do NOT
    delegate to ``_validated_project``/``validate_project`` (that would recurse
    back into this predicate). Mirroring the entry point's complete precondition
    set -- not just one of its checks -- is what keeps the skip bar and the
    validate bar the same: a table whose map is untracked/dirty OR whose Mapping
    Ready gate is still blocked is NOT validatable, so its models orphan-block
    instead of being silently skipped and thus never reached by any check. The
    table resolved here is always another table, never the one under validation.
    """
    from seshat.dbt.gate import (
        GovernanceError,
        evaluate_mapping_gate,
        resolve_working_set,
    )

    try:
        working_set = resolve_working_set(root, table_id)
    except GovernanceError:
        return False
    return evaluate_mapping_gate(working_set).allowed


def _governed_table_ids(root: Path) -> frozenset[str]:
    """Table ids that can actually be validated on their own (see
    ``_is_validatable_table``) -- the authoritative set a governed dbt model may be
    attributed to when deciding whether to skip it under a different table.
    """
    mappings_dir = root / "mappings"
    if not mappings_dir.is_dir():
        return frozenset()
    return frozenset(
        child.name
        for child in mappings_dir.iterdir()
        if child.is_dir() and _is_validatable_table(root, child.name)
    )


def _model_table_tags(row: dict[str, Any]) -> frozenset[str]:
    """The governed-table ids a model row declares via its ``seshat_table_*`` tags."""
    config = row.get("config")
    tags = config.get("tags") if isinstance(config, dict) else None
    if not isinstance(tags, list):
        return frozenset()
    ids: set[str] = set()
    for tag in tags:
        if isinstance(tag, str):
            match = _SESHAT_TABLE_TAG.match(tag)
            if match is not None:
                ids.add(match.group(1))
    return frozenset(ids)


def _check_model_selector(
    name: str,
    row: dict[str, Any],
    selector_name: str,
    blockers: list[Blocker],
) -> None:
    config = row.get("config")
    tags = config.get("tags") if isinstance(config, dict) else None
    if not isinstance(tags, list) or selector_name not in tags:
        blockers.append(
            Blocker(
                "DBT_MODEL_SELECTOR_MISSING",
                f"model {name} is not tagged for {selector_name}",
            )
        )


def _model_metadata(row: dict[str, Any]) -> dict[str, Any] | None:
    meta = row.get("meta")
    seshat = meta.get("seshat") if isinstance(meta, dict) else None
    return seshat if isinstance(seshat, dict) else None


def _check_model_citation(
    name: str,
    seshat: dict[str, Any],
    context: _ContractContext,
    blockers: list[Blocker],
) -> None:
    actual = (
        seshat.get("table_id"),
        seshat.get("source_map"),
        seshat.get("source_map_revision"),
    )
    expected = (
        context.table_id,
        context.source_map,
        context.source_map_revision,
    )
    if actual != expected:
        blockers.append(
            Blocker(
                "DBT_MODEL_CITATION_STALE",
                f"model {name} does not cite the current approved map revision",
            )
        )


def _model_grain(name: str, value: Any, blockers: list[Blocker]) -> str:
    if isinstance(value, str) and value.strip():
        return value
    blockers.append(Blocker("DBT_MODEL_CONTRACT_INVALID", f"model {name} has no grain"))
    return ""


def _model_business_key(
    name: str, value: Any, blockers: list[Blocker]
) -> tuple[str, ...]:
    if isinstance(value, list) and value:
        entries = tuple(item for item in value if isinstance(item, str) and item)
        business_key = entries if len(entries) == len(value) else ()
    else:
        business_key = ()
    if business_key:
        return business_key
    blockers.append(
        Blocker("DBT_MODEL_CONTRACT_INVALID", f"model {name} has no business key")
    )
    return ()


def _check_model_authority(name: str, authority: Any, blockers: list[Blocker]) -> None:
    if authority != "derived":
        blockers.append(
            Blocker(
                "DBT_MODEL_AUTHORITY_INVALID",
                f"model {name} authority must be derived",
            )
        )


def _model_columns(
    name: str, raw_columns: Any, blockers: list[Blocker]
) -> tuple[ColumnCitation, ...]:
    rows = raw_columns if isinstance(raw_columns, list) else []
    columns = tuple(
        citation
        for raw in rows
        if (citation := _column_citation(name, raw, blockers)) is not None
    )
    if not columns:
        blockers.append(
            Blocker(
                "DBT_COLUMN_CITATION_MISSING",
                f"model {name} has no cited output columns",
            )
        )
    return columns


def _model_contract(
    context: _ContractContext,
    row: dict[str, Any],
    blockers: list[Blocker],
) -> ModelContract | None:
    name = row["name"]
    _check_model_selector(name, row, context.selector_name, blockers)
    seshat = _model_metadata(row)
    if seshat is None:
        blockers.append(
            Blocker(
                "DBT_MODEL_CONTRACT_MISSING",
                f"model {name} has no meta.seshat contract",
            )
        )
        return None
    _check_model_citation(name, seshat, context, blockers)
    grain = _model_grain(name, seshat.get("grain"), blockers)
    business_key = _model_business_key(name, seshat.get("business_key"), blockers)
    authority = seshat.get("authority")
    _check_model_authority(name, authority, blockers)
    columns = _model_columns(name, row.get("columns"), blockers)
    return ModelContract(
        name=name,
        table_id=str(seshat.get("table_id", "")),
        source_map=str(seshat.get("source_map", "")),
        source_map_revision=str(seshat.get("source_map_revision", "")),
        grain=grain,
        business_key=business_key,
        authority=str(authority or ""),
        columns=columns,
    )


def _model_contracts(
    root: Path,
    working_set: WorkingSet,
    selector_name: str,
    blockers: list[Blocker],
) -> tuple[ModelContract, ...]:
    models_dir = root / "dbt" / "models"
    contracts: list[ModelContract] = []
    context = _ContractContext(
        selector_name=selector_name,
        table_id=working_set.table_id,
        source_map=working_set.source_map.relative_to(root).as_posix(),
        source_map_revision=working_set.source_map_revision,
    )
    property_paths = sorted([*models_dir.rglob("*.yml"), *models_dir.rglob("*.yaml")])
    governed_tables = _governed_table_ids(root)
    contracts.extend(
        contract
        for path in property_paths
        for row in _property_rows(path)
        if (
            contract := _row_contract(
                context, row, working_set.table_id, governed_tables, blockers
            )
        )
        is not None
    )
    if not contracts:
        blockers.append(
            Blocker("DBT_MODEL_CONTRACT_MISSING", "no dbt model contracts were found")
        )
    return tuple(sorted(contracts, key=lambda contract: contract.name))


def _row_contract(
    context: _ContractContext,
    row: dict[str, Any],
    table_id: str,
    governed_tables: frozenset[str],
    blockers: list[Blocker],
) -> ModelContract | None:
    """Attribute one model row to a governed table, then validate it if it is ours.

    Partitions models so a multi-table dbt project validates each table's models
    under that table's own working set (spec 133: validate covers ONE working set;
    models are isolated under the worked selector).

    Attribution uses BOTH the model's ``seshat_table_*`` tag AND its
    ``meta.seshat.table_id`` contract, so a model belongs to THIS table if either
    names it. That is deliberate: a model whose tag was accidentally copied from
    another table but whose contract still cites this table is validated here (not
    skipped), where ``_check_model_selector`` then catches the tag/contract
    mismatch -- otherwise such a model would be skipped under this table AND
    excluded from dbt's ``selector:seshat_table_<this>`` build, vanishing silently.

    A model belonging to this table -> validated in full. A model belonging only to
    ANOTHER table that has a COMPLETE committed working set (see
    ``_governed_table_ids``) -> out of scope here, validated when its own table
    runs. Anything else -- a phantom/mistyped tag, a partial-mapping table that can
    never be validated, or no seshat attribution at all -> orphan blocker: every
    model must be reachable by some table's checks, or governance never sees it.
    """
    name = _model_name(row)
    if name is None:
        return None
    model_tags = _model_table_tags(row)
    contract_table = _model_contract_table_id(row)
    # Owns THIS table if either the tag or the committed contract names it.
    if table_id in model_tags or contract_table == table_id:
        return _model_contract(context, row, blockers)
    # Owned only by another table that can actually be validated on its own.
    other_tables = model_tags | ({contract_table} if contract_table else set())
    if other_tables & governed_tables:
        return None
    blockers.append(
        Blocker(
            "DBT_MODEL_ORPHANED",
            f"model {name} is not attributable to any governed table "
            "(no seshat_table_<table> tag or meta.seshat.table_id matches a "
            "complete committed mapping working set)",
        )
    )
    return None


def _model_contract_table_id(row: dict[str, Any]) -> str | None:
    """The table id a model row declares in its ``meta.seshat.table_id`` contract."""
    seshat = _model_metadata(row)
    table_id = seshat.get("table_id") if isinstance(seshat, dict) else None
    return table_id if isinstance(table_id, str) and table_id else None


def _generic_example_leaks(project_dir: Path) -> bool:
    paths = [project_dir / "dbt_project.yml"]
    macros = project_dir / "macros"
    if macros.is_dir():
        paths.extend(path for path in macros.rglob("*") if path.is_file())
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        if any(token in text for token in _EXAMPLE_TOKENS):
            return True
    return False


def _project_document(project_dir: Path, blockers: list[Blocker]) -> dict[str, Any]:
    document = _load_yaml(project_dir / "dbt_project.yml")
    if isinstance(document, dict):
        return document
    blockers.append(
        Blocker("DBT_PROJECT_INVALID", "dbt/dbt_project.yml is missing or invalid")
    )
    return {}


def _check_project_identity(
    project_document: dict[str, Any], blockers: list[Blocker]
) -> None:
    expected = (
        ("name", "seshat_bi", "dbt project name must be seshat_bi"),
        (
            "profile",
            PROFILE_NAME,
            f"dbt project profile must be {PROFILE_NAME}",
        ),
    )
    for field, value, message in expected:
        if project_document.get(field) != value:
            blockers.append(Blocker("DBT_PROJECT_INVALID", message))


def _check_project_layers(value: Any, blockers: list[Blocker]) -> None:
    invalid = (layer for layer in _configured_layers(value) if layer not in _LAYERS)
    for layer in invalid:
        blockers.append(
            Blocker(
                "DBT_MODEL_SCHEMA_INVALID",
                f"dbt model custom schema {layer!r} is not an allowed shadow layer",
            )
        )


def _check_generic_boundary(project_dir: Path, blockers: list[Blocker]) -> None:
    if _generic_example_leaks(project_dir):
        blockers.append(
            Blocker(
                "DBT_GENERIC_EXAMPLE_LEAK",
                "generic dbt project or macro files contain worked-example answers",
            )
        )


def validate_project(
    repo_root: Path,
    working_set: WorkingSet,
    *,
    target_schema: str | None = None,
) -> ProjectValidation:
    """Validate the table-neutral project boundary and filled model contracts."""

    root = Path(repo_root).resolve()
    project_dir = root / "dbt"
    blockers: list[Blocker] = []
    project_document = _project_document(project_dir, blockers)
    _check_project_identity(project_document, blockers)
    _check_project_layers(project_document.get("models"), blockers)

    resolved_target_schema = _profile(root, blockers, target_schema)
    schemas = _schemas(resolved_target_schema, blockers)
    selector_name = _selector(project_dir, working_set.table_id, blockers)
    contracts = _model_contracts(root, working_set, selector_name, blockers)
    _check_generic_boundary(project_dir, blockers)

    return ProjectValidation(
        valid=not blockers,
        project_fingerprint=fingerprint_project(root),
        selector_name=selector_name,
        profile_name=PROFILE_NAME,
        target_name=TARGET_NAME,
        schemas=schemas,
        model_contracts=contracts,
        blocking_reasons=tuple(blockers),
    )
