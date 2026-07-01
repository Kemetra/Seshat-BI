"""RS1 -- readiness-status contradiction linter.

The readiness spine is useful only if its recorded state is internally
consistent. RS1 checks filled per-table readiness status files
(``mappings/<table>/readiness-status.yaml``) for structural contradictions:

* every stage status is one of the four readiness words;
* ``pass`` carries evidence;
* ``blocked`` carries blocking reasons;
* non-blocked stages do not carry ``blocking_reasons[]``;
* approval-required stages cannot pass without a matching ``approvals[]`` entry;
* ``current_stage`` cannot point past an earlier blocked stage;
* a blocked current stage mirrors blockers at the top level.

It is a static text/YAML read. It never opens a DB, never runs Power BI, never
grants an approval, and never advances a stage.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

_INSTANCE_RE = re.compile(r"^mappings/[^/]+/readiness-status\.yaml$")
_STAGE_ORDER: tuple[str, ...] = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)
_STATUS_VALUES: frozenset[str] = frozenset(
    {"not_started", "blocked", "warning", "pass"}
)
_APPROVAL_REQUIRED: frozenset[str] = frozenset(
    {"mapping_ready", "semantic_model_ready", "dashboard_ready", "publish_ready"}
)


def _finding(message: str, locator: str) -> Finding:
    return Finding(
        rule_id="RS1",
        severity=Severity.ERROR,
        message=message,
        locator=locator,
    )


def _iter_status_files(ctx: RuleContext) -> list[str]:
    return [
        p for p in ctx.tracked_files if _INSTANCE_RE.match(p) and not is_test_path(p)
    ]


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _stage_status(stage_block) -> str | None:
    if isinstance(stage_block, dict):
        status = stage_block.get("status")
        if isinstance(status, str):
            return status
    return None


@register("RS1", "Readiness status files are internally consistent")
def check_readiness_status_consistency(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []

    for rel in sorted(_iter_status_files(ctx)):
        try:
            raw = (ctx.repo_root / rel).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(_finding(f"could not read readiness status: {exc}", rel))
            continue

        import yaml  # lazy: keep retail check import path stdlib-light

        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            findings.append(_finding(f"readiness status is not valid YAML: {exc}", rel))
            continue

        if not isinstance(data, dict):
            findings.append(_finding("readiness status must be a mapping", rel))
            continue

        stages = data.get("stages")
        if not isinstance(stages, dict):
            findings.append(
                _finding("readiness status must contain a 'stages' mapping", rel)
            )
            continue

        current_stage = data.get("current_stage")
        if current_stage not in _STAGE_ORDER:
            findings.append(
                _finding(
                    f"current_stage {current_stage!r} is not one of "
                    f"{list(_STAGE_ORDER)}",
                    rel,
                )
            )

        approvals = _as_list(data.get("approvals"))
        approved_stages = {
            a.get("stage")
            for a in approvals
            if isinstance(a, dict) and isinstance(a.get("stage"), str)
        }

        earliest_blocked_index: int | None = None
        for index, stage_name in enumerate(_STAGE_ORDER):
            block = stages.get(stage_name)
            loc = f"{rel}:stages.{stage_name}"
            if block is None:
                findings.append(_finding(f"stage {stage_name!r} is missing", loc))
                continue
            if not isinstance(block, dict):
                findings.append(
                    _finding(f"stage {stage_name!r} must be a mapping", loc)
                )
                continue

            status = _stage_status(block)
            evidence = _as_list(block.get("evidence"))
            blockers = _as_list(block.get("blocking_reasons"))

            if status not in _STATUS_VALUES:
                findings.append(
                    _finding(
                        f"stage {stage_name!r} has invalid status {status!r} "
                        f"(must be one of {sorted(_STATUS_VALUES)})",
                        loc,
                    )
                )
                continue

            if status == "pass" and not evidence:
                findings.append(
                    _finding(
                        f"stage {stage_name!r} is pass but has no evidence[]",
                        loc,
                    )
                )

            if status == "blocked":
                if earliest_blocked_index is None:
                    earliest_blocked_index = index
                if not blockers:
                    findings.append(
                        _finding(
                            f"stage {stage_name!r} is blocked but has no "
                            "blocking_reasons[]",
                            loc,
                        )
                    )
            elif blockers:
                findings.append(
                    _finding(
                        f"stage {stage_name!r} is {status!r} but carries "
                        "blocking_reasons[]; blockers belong on blocked stages",
                        loc,
                    )
                )

            if (
                status == "pass"
                and stage_name in _APPROVAL_REQUIRED
                and stage_name not in approved_stages
            ):
                findings.append(
                    _finding(
                        f"stage {stage_name!r} is pass but no matching "
                        "approvals[] entry is recorded",
                        loc,
                    )
                )

        if current_stage in _STAGE_ORDER and earliest_blocked_index is not None:
            current_index = _STAGE_ORDER.index(current_stage)
            if current_index > earliest_blocked_index:
                blocked_stage = _STAGE_ORDER[earliest_blocked_index]
                findings.append(
                    _finding(
                        f"current_stage {current_stage!r} skips past earlier "
                        f"blocked stage {blocked_stage!r}",
                        rel,
                    )
                )

        if current_stage in _STAGE_ORDER:
            current_block = stages.get(current_stage)
            current_status = _stage_status(current_block)
            top_blockers = _as_list(data.get("blocking_reasons"))
            if current_status == "blocked" and not top_blockers:
                findings.append(
                    _finding(
                        "current_stage is blocked but top-level "
                        "blocking_reasons[] is empty",
                        rel,
                    )
                )

    return findings
