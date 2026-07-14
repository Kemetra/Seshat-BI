"""Composition of the shipped governance, readiness, and next-step seams.

These helpers reuse the existing rule runner and readiness projection rather
than re-deriving them, degrading honestly to an ``unavailable`` fact when a
seam cannot be evaluated.  ``_next_step`` is expressed as an ordered list of
small guards so the earliest unresolved concern wins deterministically.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._facts import _Fact
from ._safety import _safe_detail

_STAGE_ORDER = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


@dataclass(frozen=True)
class _NextStepInputs:
    target_kind: str
    version_control: str
    facts: list[dict[str, Any]]
    readiness: list[dict[str, Any]]
    blockers: list[dict[str, Any]]


def _governance_findings(
    root: Any,
) -> tuple[list[dict[str, Any]], list[_Fact]]:
    """Compose the shipped rule runner, degrading honestly when it is unavailable."""
    try:
        import seshat.rules  # noqa: F401

        from ..kit_lint import is_bootstrapped
        from ..registry import all_rules
        from ..runner import build_context, collect_findings

        context = build_context(root)
        findings = collect_findings(
            all_rules(), context, bootstrapped=is_bootstrapped(root)
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return [], [
            _Fact(
                id="unavailable:governance-runner",
                classification="unavailable_with_reason",
                category="governance",
                subject="existing governance findings",
                detail="Existing static governance findings could not be evaluated.",
                reason=_safe_detail(type(exc).__name__, fallback="runner unavailable"),
            )
        ]

    normalized: list[dict[str, Any]] = []
    facts: list[_Fact] = []
    for finding in findings:
        locator = str(finding.locator).replace("\\", "/")
        if locator.startswith("../") or Path(locator).is_absolute():
            continue
        severity = finding.severity.value.upper()
        classification = "blocked" if severity == "ERROR" else "observed"
        normalized.append(
            {
                "rule_id": finding.rule_id,
                "severity": severity,
                "message": _safe_detail(
                    finding.message, fallback="Existing rule finding."
                ),
                "locator": locator or ".",
                "classification": classification,
            }
        )
        if severity == "ERROR":
            facts.append(
                _Fact(
                    id=f"blocked:rule:{finding.rule_id}:{locator}",
                    classification="blocked",
                    category="governance",
                    subject=f"governance rule {finding.rule_id}",
                    detail="An existing governance rule reported a blocking finding.",
                    artifact=locator or None,
                    rule_id=finding.rule_id,
                    required_authority="governance",
                )
            )
    normalized.sort(
        key=lambda item: (item["rule_id"], item["locator"], item["message"])
    )
    return normalized, facts


def _readiness(root: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from ..blocker_explainer import build_blocker_explanations
        from ..readiness_projection import build_readiness_projection
        from ..run_next import build_run_next_response

        projection = build_readiness_projection(root)
        tables = projection.get("tables", [])
        readiness: list[dict[str, Any]] = []
        for table in tables if isinstance(tables, list) else []:
            entry = _readiness_entry(root, table, build_run_next_response)
            if entry is not None:
                readiness.append(entry)
        readiness.sort(key=lambda item: str(item["projection"].get("source_path")))
        blockers = build_blocker_explanations(root).get("items", [])
        return readiness, blockers if isinstance(blockers, list) else []
    except (OSError, ValueError, KeyError):
        return [], []


def _readiness_entry(
    root: Any, table: Any, build_run_next_response: Any
) -> dict[str, Any] | None:
    if not isinstance(table, dict):
        return None
    table_id = table.get("table_id")
    source_path = table.get("source_path")
    if not isinstance(table_id, str) or not isinstance(source_path, str):
        return None
    table_dir = source_path.rsplit("/", 2)[-2]
    return {
        "projection": table,
        "run_next": build_run_next_response(root, table_dir),
    }


def _default_next_step() -> dict[str, Any]:
    return {
        "kind": "action",
        "stage": "source_ready",
        "action": "No readiness file found; start onboarding at Source Ready.",
        "blocking_reasons": [],
        "required_authority": "data_owner",
    }


def _next_step(inputs: _NextStepInputs) -> dict[str, Any]:
    guards = (
        _pbix_step,
        _absent_vc_step,
        _unclean_vc_step,
        _ambiguity_step,
        _blocked_fact_step,
        _readiness_step,
        _blocker_step,
    )
    for guard in guards:
        step = guard(inputs)
        if step is not None:
            return step
    return _default_next_step()


def _pbix_step(inputs: _NextStepInputs) -> dict[str, Any] | None:
    if inputs.target_kind != "pbix_unsupported":
        return None
    return {
        "kind": "terminal_stop",
        "stage": None,
        "action": (
            "Open the PBIX in Power BI Desktop, save it as a Power BI Project "
            "(PBIP), then assess the saved project directory."
        ),
        "blocking_reasons": [
            "PBIX binaries are not parsed or modified by PBIP adoption."
        ],
        "required_authority": "analyst",
    }


def _absent_vc_step(inputs: _NextStepInputs) -> dict[str, Any] | None:
    if inputs.version_control != "absent":
        return None
    return {
        "kind": "action",
        "stage": "source_ready",
        "action": (
            "Initialize version control yourself, review the project files, "
            "and reassess before creating an adoption baseline."
        ),
        "blocking_reasons": [
            "The selected project is not in a Git worktree, so committed "
            "evidence cannot be evaluated."
        ],
        "required_authority": "analyst",
    }


def _unclean_vc_step(inputs: _NextStepInputs) -> dict[str, Any] | None:
    if inputs.version_control not in {"dirty", "untracked"}:
        return None
    return {
        "kind": "action",
        "stage": "source_ready",
        "action": (
            "Review and commit or intentionally discard the changed project "
            "inputs, then reassess."
        ),
        "blocking_reasons": ["Project inputs are not clean committed evidence."],
        "required_authority": "analyst",
    }


def _ambiguity_step(inputs: _NextStepInputs) -> dict[str, Any] | None:
    ambiguity = [
        fact
        for fact in inputs.facts
        if fact["id"]
        in {"blocked:multiple-semantic-models", "blocked:multiple-reports"}
    ]
    if not ambiguity:
        return None
    return {
        "kind": "action",
        "stage": "source_ready",
        "action": (
            "Resolve the intended PBIP model and report scope with an analyst, "
            "then reassess."
        ),
        "blocking_reasons": [fact["detail"] for fact in ambiguity],
        "required_authority": "analyst",
    }


def _blocked_fact_step(inputs: _NextStepInputs) -> dict[str, Any] | None:
    unsafe = [fact for fact in inputs.facts if fact["classification"] == "blocked"]
    if not unsafe:
        return None
    first = unsafe[0]
    return {
        "kind": "action",
        "stage": "source_ready",
        "action": (
            "Resolve the earliest recorded governance or containment blocker, "
            "then reassess."
        ),
        "blocking_reasons": [first["detail"]],
        "required_authority": first["required_authority"] or "governance",
    }


def _readiness_step(inputs: _NextStepInputs) -> dict[str, Any] | None:
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for item in inputs.readiness:
        response = item.get("run_next")
        if not isinstance(response, dict):
            continue
        stage = response.get("stage")
        index = (
            _STAGE_ORDER.index(stage) if stage in _STAGE_ORDER else len(_STAGE_ORDER)
        )
        candidates.append((index, str(item["projection"].get("table_id")), response))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    earliest = candidates[0]
    tied = [candidate for candidate in candidates if candidate[0] == earliest[0]]
    if len(tied) > 1:
        return {
            "kind": "action",
            "stage": _STAGE_ORDER[earliest[0]],
            "action": (
                "Resolve which equally urgent readiness table is in scope "
                "before proceeding."
            ),
            "blocking_reasons": [
                "Multiple readiness tables share the earliest unresolved stage."
            ],
            "required_authority": "analyst",
        }
    return _readiness_response_step(earliest[2])


def _readiness_response_step(response: dict[str, Any]) -> dict[str, Any]:
    outcome = response.get("outcome")
    authority = response.get("required_authority")
    return {
        "kind": "terminal_stop" if outcome == "terminal_pass" else "action",
        "stage": response.get("stage"),
        "action": _safe_detail(
            response.get("action_text")
            or "Review the existing readiness response before proceeding.",
            fallback="Review the existing readiness response before proceeding.",
        ),
        "blocking_reasons": [
            str(reason)
            for reason in response.get("blocking_reasons", [])
            if isinstance(reason, str)
        ],
        "required_authority": authority if isinstance(authority, str) else None,
    }


def _blocker_step(inputs: _NextStepInputs) -> dict[str, Any] | None:
    if not inputs.blockers:
        return None
    first = inputs.blockers[0]
    authority = first.get("required_authority")
    return {
        "kind": "action",
        "stage": "source_ready",
        "action": "Resolve the earliest recorded readiness blocker, then reassess.",
        "blocking_reasons": [
            _safe_detail(first.get("reason"), fallback="A readiness blocker remains.")
        ],
        "required_authority": authority if isinstance(authority, str) else "data_owner",
    }
