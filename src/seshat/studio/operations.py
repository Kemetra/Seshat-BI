"""Operations: component diagnostics and governed run history (spec 141).

Presentation over existing truth. `doctor.py` does the probing; this module maps its
findings into the component vocabulary spec 141 introduces, and assembles run summaries
from records that already exist.

Two things this module must never do, both encoded structurally rather than as advice:

- **No aggregate score** (FR-141-002). `ComponentDiagnostic` has no numeric field, so a
  roll-up is unrepresentable rather than merely discouraged.
- **No invented authority.** `durability` is derived from whether a committed source
  exists, never passed in, so the label and the fact cannot disagree (FR-141-010).

FR-141-004 forbids a second *probe set*, not a mapping layer. The mapping is new code:
`doctor.py` returns `list[Finding]` whose `severity` is only error/warning/info
(`core.py:44`), so the six component states below exist nowhere else in the tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from seshat import doctor
from seshat.core import Finding, Severity

#: Closed vocabulary (FR-141-003). `deferred` is NOT a failure: it means a boundary that
#: is legitimately unavailable -- no DSN configured, an optional extra absent -- and
#: colouring it as failure trains technicians to ignore failures.
COMPONENT_STATES: tuple[str, ...] = (
    "missing",
    "misconfigured",
    "incompatible",
    "deferred",
    "failed",
    "healthy",
)

#: The seven surfaces US1 names. One diagnostic each; never a roll-up.
COMPONENTS: tuple[str, ...] = (
    "studio_process",
    "package_extras",
    "codex_adapter",
    "bundle_capability",
    "static_gate",
    "live_boundary",
    "frontend_assets",
)

#: The marker the rest of Seshat already uses for "not verified against a live source".
PENDING_LIVE_MARKER = "[PENDING LIVE PROFILE]"

#: Severities that do not by themselves mean the component failed.
_TOLERABLE = frozenset({Severity.WARNING.value, Severity.INFO.value})


def _severity_value(finding: Finding) -> object:
    """The severity as a comparable string, tolerating a non-enum value.

    A `Finding` whose severity is not a recognized `Severity` is malformed input. This
    returns whatever it holds so `state_for` can fail closed rather than raising -- an
    unreadable component must report `failed`, not crash the view.
    """
    return getattr(finding.severity, "value", finding.severity)


def state_for(findings: list[Finding]) -> str:
    """The component state implied by its findings.

    Order matters. An unrecognized or error severity yields `failed` BEFORE the deferred
    check runs, so one pending-live finding cannot launder a real error beside it.
    """
    if not findings:
        return "healthy"
    if {_severity_value(f) for f in findings} - _TOLERABLE:
        return "failed"
    if all(PENDING_LIVE_MARKER in f.message for f in findings):
        return "deferred"
    return "misconfigured"


@dataclass(frozen=True, slots=True)
class ComponentDiagnostic:
    """One component's state, with the findings that justify it.

    `source_rule_ids` exists so a displayed diagnosis is traceable to the rule that
    produced it. Without it, Operations could show a state no rule supports and nobody
    could tell.

    There is deliberately NO numeric field (FR-141-002).
    """

    component: str
    state: str
    evidence: tuple[str, ...] = ()
    blocker: str | None = None
    recovery_action: str | None = None
    source_rule_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "component": self.component,
            "state": self.state,
            "evidence": list(self.evidence),
            "blocker": self.blocker,
            "recovery_action": self.recovery_action,
            "source_rule_ids": list(self.source_rule_ids),
        }


def diagnose(component: str, findings: list[Finding]) -> ComponentDiagnostic:
    """Map findings to one diagnostic, reusing doctor's own repair hints."""
    return ComponentDiagnostic(
        component=component,
        state=state_for(findings),
        evidence=tuple(f"{f.message} ({f.locator})" for f in findings),
        blocker=findings[0].message if findings else None,
        recovery_action=(doctor.repair_hint(findings[0].rule_id) if findings else None),
        source_rule_ids=tuple(f.rule_id for f in findings),
    )


def report(repo_root: Path | str) -> tuple[ComponentDiagnostic, ...]:
    """One diagnostic per component.

    Every component appears even when it has no findings, because a component missing
    from the report reads as "fine" to a technician scanning the list -- the same
    empty-success failure US1 exists to prevent.
    """
    grouped = _findings_by_component(repo_root)
    return tuple(
        diagnose(component, grouped.get(component, [])) for component in COMPONENTS
    )


#: Which component each doctor rule id reports on. `doctor`'s ids are A1, A3, SC1 and
#: DOCTOR (see its `_REPAIR_HINTS`); anything unmapped lands on `static_gate` rather
#: being dropped, because a dropped finding reads as health.
_RULE_COMPONENT: dict[str, str] = {
    "A1": "static_gate",
    "A3": "static_gate",
    "SC1": "bundle_capability",
    "DOCTOR": "studio_process",
}

_UNMAPPED_COMPONENT = "static_gate"


def _findings_by_component(repo_root: Path | str) -> dict[str, list[Finding]]:
    """Group doctor's findings under the component each belongs to.

    Fails CLOSED. If the engine cannot run at all -- git missing, an unreadable tree --
    this reports a `failed` finding against `studio_process` rather than returning
    nothing. Returning `{}` would render all seven components healthy, which is the
    empty-success state US1 exists to prevent.
    """
    from seshat import doctor as doctor_module
    from seshat.runner import build_context

    try:
        findings = doctor_module.collect_findings(build_context(Path(repo_root)))
    except (OSError, RuntimeError) as exc:
        return {
            "studio_process": [
                Finding(
                    rule_id="DOCTOR",
                    severity=Severity.ERROR,
                    message=f"diagnostics could not run: {exc}",
                    locator=str(repo_root),
                )
            ]
        }

    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        component = _RULE_COMPONENT.get(finding.rule_id, _UNMAPPED_COMPONENT)
        grouped.setdefault(component, []).append(finding)
    return grouped


@dataclass(frozen=True, slots=True)
class GovernedRunSummary:
    """One governed run, as history rather than as authority.

    `durability` is a PROPERTY, not a field: it is derived from whether a committed
    source exists, so a caller cannot label an uncitable record durable (FR-141-010).
    """

    run_id: str
    requested: str
    committed_source: str | None = None
    decision_state: str = "pending_commit"
    proposed_tools: tuple[str, ...] = ()
    decided_by: str | None = None
    gates_run: tuple[str, ...] = ()
    outcome: str = "recorded"

    @property
    def durability(self) -> str:
        return "durable" if self.committed_source else "ephemeral"

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "requested": self.requested,
            "committed_source": self.committed_source,
            "decision_state": self.decision_state,
            "proposed_tools": list(self.proposed_tools),
            "decided_by": self.decided_by,
            "gates_run": list(self.gates_run),
            "outcome": self.outcome,
            "durability": self.durability,
        }


def summarize_run(
    *,
    run_id: str,
    requested: str,
    committed_source: str | None,
    decision_state: str = "pending_commit",
    proposed_tools: tuple[str, ...] = (),
    decided_by: str | None = None,
    gates_run: tuple[str, ...] = (),
) -> GovernedRunSummary:
    """Build one run summary.

    `decision_state` defaults to the UNSETTLED value on purpose: a caller that forgets
    it must not accidentally claim authority (FR-141-021). There is no `durability`
    parameter -- it is derived.
    """
    return GovernedRunSummary(
        run_id=run_id,
        requested=requested,
        committed_source=committed_source,
        decision_state=decision_state,
        proposed_tools=proposed_tools,
        decided_by=decided_by,
        gates_run=gates_run,
    )
