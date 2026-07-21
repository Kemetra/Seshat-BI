"""Orchestrate ``seshat dbt scaffold``: approved map -> written governed models.

Gating reuses the existing approved-mapping path (``planning._approved_mapping``
+ ``fact_semantics.load_fact_semantics``): the scaffold materializes FROM the
*approved, committed* source map, exactly like ``seshat dbt plan``/``validate``,
so ``source_map_revision`` resolves to the committed blob and the generated
citations are stable. A blocked gate, an untracked/dirty map, or missing fact
tags fail closed with the same governance codes the rest of the family raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.dbt.contracts import GovernanceError
from seshat.dbt.fact_semantics import load_fact_semantics
from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set

from . import model_plan, sql_render, writer, yaml_render


@dataclass(frozen=True)
class ScaffoldReport:
    """What one ``scaffold_models`` call did, per file, plus operator notes."""

    table_id: str
    written: tuple[str, ...]
    kept: tuple[str, ...]
    merged: tuple[str, ...]
    notes: tuple[str, ...]


def _approved_working_set(root: Path, table_id: str):
    working_set = resolve_working_set(root, table_id)
    gate = evaluate_mapping_gate(working_set)
    if not gate.allowed:
        codes = ", ".join(blocker.code for blocker in gate.blocking_reasons)
        raise GovernanceError(
            "DBT_MAPPING_GATE_BLOCKED",
            f"Mapping Ready gate blocks dbt scaffold: {codes}",
        )
    return working_set


def _load_map_document(source_map: Path) -> dict:
    try:
        document = yaml.safe_load(source_map.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise model_plan.ScaffoldError(
            f"approved source map is unreadable: {exc.__class__.__name__}"
        ) from exc
    if not isinstance(document, dict):
        raise model_plan.ScaffoldError("approved source map must be a YAML mapping")
    return document


def _build_plan(root: Path, table_id: str) -> model_plan.ScaffoldPlan:
    working_set = _approved_working_set(root, table_id)
    fact = load_fact_semantics(working_set.source_map)
    source = model_plan.MapSource(
        document=_load_map_document(working_set.source_map),
        source_map=working_set.source_map.relative_to(root).as_posix(),
        source_map_revision=working_set.source_map_revision,
    )
    return model_plan.build_scaffold_plan(source, table_id, fact)


def _staging_files(plan: model_plan.ScaffoldPlan, selector: str) -> dict[str, str]:
    base = f"dbt/models/staging/{plan.table_id}"
    document = yaml_render.render_models_document((plan.staging,), plan, selector)
    return {
        f"{base}/{plan.staging.name}.sql": sql_render.render_staging_sql(plan),
        f"{base}/_models.yml": _dump(document),
    }


def _mart_files(plan: model_plan.ScaffoldPlan, selector: str) -> dict[str, str]:
    base = f"dbt/models/marts/{plan.table_id}"
    marts = (*plan.dimensions, plan.fact_model)
    files: dict[str, str] = {
        f"{base}/_models.yml": _dump(
            yaml_render.render_models_document(marts, plan, selector)
        ),
        f"{base}/{plan.fact_model.name}.sql": sql_render.render_fact_sql(plan),
    }
    for dim in plan.dimensions:
        files[f"{base}/{dim.name}.sql"] = _dimension_sql(dim, plan)
    return files


def _dimension_sql(dim: model_plan.ModelSpec, plan: model_plan.ScaffoldPlan) -> str:
    if dim.columns and dim.columns[0].derivation == "date_spine":
        return sql_render.render_date_dimension_sql(dim)
    return sql_render.render_dimension_sql(dim, plan)


def _audit_files(plan: model_plan.ScaffoldPlan, selector: str) -> dict[str, str]:
    base = f"dbt/models/audit/{plan.table_id}"
    document = yaml_render.render_models_document((plan.audit,), plan, selector)
    return {
        f"{base}/{plan.audit.name}.sql": sql_render.render_audit_sql(plan),
        f"{base}/_models.yml": _dump(document),
    }


def _dump(document: dict) -> str:
    return yaml.safe_dump(document, sort_keys=False, default_flow_style=False)


def _model_files(plan: model_plan.ScaffoldPlan, selector: str) -> dict[str, str]:
    return {
        **_staging_files(plan, selector),
        **_mart_files(plan, selector),
        **_audit_files(plan, selector),
    }


def _notes(plan: model_plan.ScaffoldPlan) -> tuple[str, ...]:
    table = plan.table_id
    return (
        "the generated .sql files are SKELETONS: complete the joins, casts, and "
        "surrogate-key logic (the SELECT column list is the governed contract -- "
        f"do not change it), then run `seshat dbt validate --table {table}`",
        # scaffold is non-destructive (existing files are KEPT), so a plain
        # re-run does NOT refresh a stale citation -- state the real manual step.
        "after you re-commit an edited source map, the generated _models.yml "
        "source_map_revision goes stale: update it (to the new "
        f"`git rev-parse HEAD:{plan.source_map}`) in dbt/models/**/{table}/"
        "_models.yml, OR delete those _models.yml files and re-run scaffold to "
        "regenerate them (scaffold keeps existing files, so it will not overwrite "
        "a stale one in place)",
    )


def scaffold_models(repo_root: Path, table_id: str) -> ScaffoldReport:
    """Materialize the governed dbt model set for one approved table."""
    root = Path(repo_root).resolve()
    plan = _build_plan(root, table_id)
    selector = f"seshat_table_{table_id}"
    written: list[str] = []
    kept: list[str] = []
    for relative, text in sorted(_model_files(plan, selector).items()):
        (written if writer.write_model_file(root, relative, text) else kept).append(
            relative
        )
    merged: list[str] = []
    if writer.merge_selector(root, selector):
        merged.append("dbt/selectors.yml")
    if writer.merge_sources(root, plan):
        merged.append("dbt/models/sources/_sources.yml")
    return ScaffoldReport(
        table_id=table_id,
        written=tuple(written),
        kept=tuple(kept),
        merged=tuple(merged),
        notes=_notes(plan),
    )
