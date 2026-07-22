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


_CONFORMED_MAP = "docs/quality/conformed-dimension-map.yaml"


def _committed_map_text(root: Path) -> str | None:
    """The conformed-dimension map as committed at ``HEAD`` (or None).

    The map is now an OWNERSHIP AUTHORITY that changes which dimension models get
    emitted, so -- exactly like the source map, which resolves to its committed
    blob (``source_map_revision``) -- reuse must be driven by COMMITTED governance
    state, never an uncommitted worktree edit that could suppress models from
    unreviewed content (#419 review). Reads ``git show HEAD:<map>``. Any failure
    (git absent, file not committed, non-zero exit) returns None -> no reuse.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{_CONFORMED_MAP}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    return result.stdout if result.returncode == 0 else None


def _load_conformed_map(root: Path) -> dict | None:
    """The COMMITTED conformed-dimension map (or None), so a CONFORMED dim owned by
    another star is referenced, not re-emitted (#418-P1).

    Read from ``HEAD`` (``_committed_map_text``), NOT the worktree: the map is an
    ownership authority, and an uncommitted edit must not silently suppress
    dimension models. Fail-SAFE, never fail-closed: an absent/uncommitted or
    unreadable/malformed map disables reuse (every dim is owned) -- HR1 is the gate
    that fails closed on a bad declaration, not scaffold. Returns the parsed
    mapping, else None.
    """
    text = _committed_map_text(root)
    if text is None:
        return None
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    return document if isinstance(document, dict) else None


def _build_plan(root: Path, table_id: str) -> model_plan.ScaffoldPlan:
    working_set = _approved_working_set(root, table_id)
    fact = load_fact_semantics(working_set.source_map)
    source = model_plan.MapSource(
        document=_load_map_document(working_set.source_map),
        source_map=working_set.source_map.relative_to(root).as_posix(),
        source_map_revision=working_set.source_map_revision,
        conformed_map=_load_conformed_map(root),
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
    reuse_notes: tuple[str, ...] = ()
    if plan.reused_dimensions:
        owners = plan.reused_dimension_owners
        dims = ", ".join(
            f"{name} (owned by {owners[name]})" if name in owners else name
            for name in plan.reused_dimensions
        )
        reuse_notes = (
            f"conformed dimension(s) {dims} are owned by another star (per "
            f"{_CONFORMED_MAP}), so this table does NOT emit their model files -- "
            "its fact FKs reference the owning star's model via `ref()`. Build the "
            "owning star(s) first so dbt can resolve those refs.",
            # scaffold is write-if-absent, so a dim that BECOMES reused (declared
            # conformed after this table was already scaffolded) is not
            # auto-removed: DELETE any stale dbt/models/marts/<table>/<dim>.sql +
            # its _models.yml row for a now-reused dim, or dbt parse still fails on
            # the duplicate model name.
            "if a dimension became conformed/reused AFTER this table was first "
            "scaffolded, delete its now-stale dbt/models/marts/"
            f"{table}/<dim>.sql and _models.yml row by hand -- scaffold keeps "
            "existing files and will not remove the superseded model.",
        )
    return (
        *reuse_notes,
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
