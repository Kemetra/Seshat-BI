"""Guided setup execution: derived capability need -> approved provisioning (spec 155).

Three shipped things did not touch each other before this module existed:

* the DERIVED capability plan (spec 153) -- what this project actually needs, in
  capability language, from committed evidence;
* the committed named-human provisioning approval (spec 154, issue #671) -- the
  only thing that may authorize installing external software;
* the integration control plane (spec 144) -- catalog, resolver, compatibility
  policy, installer, lock, discovery.

This module is the seam between them, and nothing more. It owns no component,
coordinate, version, provider, capability, or approval of its own: every one of
those is read from the surface that already owns it.

**Why this is a separate module, and not part of ``derivation.py``.** Two shipped
spec-153 tests read that file as source text and assert it contains no
``apply_profile(``, ``write_lock(``, ``install(``, ``approved``, or ``authorize``
call site. Those assertions are the mechanical proof of spec 153's FR-017/FR-018
boundaries -- derivation derives and nothing else. This module legitimately calls
the installer and consults the approval gate, so it lives here; derivation stays
pure and both boundaries stay testable.

**Eligibility is spec 153's own definition.** A capability contributes components
only when the derived plan reports it as needing action -- ``required`` or
``recommended``, not satisfied, not declined -- and its evidence is not
undetermined. ``optional`` capabilities are presented and never proposed: any
opt-in path would need a recorded want-signal, and inventing one would be a
second approval-authoring path (spec 155 owner decision 2).
"""

from __future__ import annotations

from dataclasses import dataclass

from seshat.integrations.derivation import SetupPlan, SetupPlanRow

# Why a capability contributed nothing. Categorical so a caller can branch and a
# test can assert without matching prose -- and so "excluded" is never silent.
NOT_REQUIRED = "not-required"
DECLINED = "declined"
SATISFIED = "satisfied"
OPTIONAL = "optional"
UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class Exclusion:
    """One capability that contributed no component, and the reason it did not."""

    capability_id: str
    reason: str


@dataclass(frozen=True)
class Contribution:
    """One capability and the components it put into the scope.

    Kept alongside the flattened `component_ids` because readiness is answered
    per CAPABILITY while installation happens per component: without this the
    join back from a failed component to the capability it belongs to would have
    to be guessed.
    """

    capability_id: str
    component_ids: tuple[str, ...]


@dataclass(frozen=True)
class DerivedScope:
    """The exact existing catalog components a project's derived need calls for.

    ``component_ids`` is the object an approval binds to (spec 154), so it is
    deliberately a function of committed evidence, the shipped projection,
    discovery state, and committed declines -- and of nothing a caller supplies.
    """

    plan: SetupPlan
    component_ids: tuple[str, ...]
    contributing: tuple[SetupPlanRow, ...]
    excluded: tuple[Exclusion, ...]
    contributions: tuple[Contribution, ...] = ()
    unsupported: tuple[str, ...] = ()
    outside_need: tuple[str, ...] = ()

    @property
    def blockers(self) -> tuple[str, ...]:
        return self.plan.blockers

    @property
    def blocked(self) -> bool:
        """True when the plan MUST NOT execute, whatever an approval says.

        A declined `required` capability lands here. No approval clears it: the
        blocker is about the project's own evidence, not about authority.
        """
        return self.plan.blocked

    @property
    def proposes_change(self) -> bool:
        return bool(self.component_ids)


def _exclusion_reason(row: SetupPlanRow) -> str | None:
    """Why this row contributes nothing, or None when it contributes.

    Order is meaning, not convenience. Unreadable evidence is reported before a
    strength, because a strength derived from evidence nobody could read would be
    a guess wearing a category. A human's decline is reported before satisfaction,
    because the decline is the fact they will look for.
    """
    if row.undetermined_evidence:
        return UNDETERMINED
    if row.declined:
        return DECLINED
    if row.satisfied:
        return SATISFIED
    if row.needs_action:
        return None
    return NOT_REQUIRED if row.strength == NOT_REQUIRED else OPTIONAL


def _catalog_components(component_ids: tuple[str, ...]) -> tuple[str, ...]:
    """The subset of `component_ids` the catalog actually knows.

    An id the catalog does not carry is dropped here rather than passed to the
    installer, so a stale projection entry surfaces as an unsupported capability
    instead of a resolution failure three layers down.
    """
    from seshat.integrations.catalog import component

    known = []
    for component_id in component_ids:
        try:
            component(component_id)
        except KeyError:
            continue
        known.append(component_id)
    return tuple(known)


@dataclass
class _Sorted:
    """Rows split into what contributes, what does not, and what cannot."""

    contributing: list[SetupPlanRow]
    contributions: list[Contribution]
    excluded: list[Exclusion]
    unsupported: list[str]

    @property
    def component_ids(self) -> tuple[str, ...]:
        """Every contributed id once, in capability order then projection order."""
        ordered: list[str] = []
        for contribution in self.contributions:
            ordered.extend(
                cid for cid in contribution.component_ids if cid not in ordered
            )
        return tuple(ordered)


def _sort_rows(plan: SetupPlan, projection: dict) -> _Sorted:
    """Decide, per capability, whether it contributes components and why not."""
    sorted_rows = _Sorted([], [], [], [])
    for row in plan.rows:
        reason = _exclusion_reason(row)
        if reason is not None:
            sorted_rows.excluded.append(Exclusion(row.capability.id, reason))
            continue
        known = _catalog_components(tuple(projection.get(row.capability.id, ())))
        if not known:
            # Needed, but nothing in the catalog satisfies it. Reported, never
            # dropped and never reported satisfied (FR-023).
            sorted_rows.unsupported.append(row.capability.id)
            continue
        sorted_rows.contributing.append(row)
        sorted_rows.contributions.append(Contribution(row.capability.id, known))
    return sorted_rows


def derive_scope(root, *, requested: tuple[str, ...] = ()) -> DerivedScope:
    """The proposed change set for this project, from committed evidence only.

    Reads. Never writes, never resolves a coordinate, never contacts a network,
    and never installs -- so it is safe to run before anyone has approved
    anything, which is the point: the human reviews THIS before authorizing it.

    ``requested`` is reported back as `outside_need` and is deliberately absent
    from every calculation that produces `component_ids`. A caller asking for a
    capability does not make the project need it (FR-007).
    """
    from seshat.integrations import derivation

    plan = derivation.derive(root)
    rows = _sort_rows(plan, derivation.CAPABILITY_COMPONENTS)
    return DerivedScope(
        plan=plan,
        component_ids=rows.component_ids,
        contributing=tuple(rows.contributing),
        excluded=tuple(rows.excluded),
        contributions=tuple(rows.contributions),
        unsupported=tuple(rows.unsupported),
        outside_need=derivation.requested_outside_need(plan, tuple(requested)),
    )


# --------------------------------------------------------------------------- #
# Capability status: the agent-facing view (FR-011).
# --------------------------------------------------------------------------- #

# What this feature would DO about one capability. Categorical, so an agent never
# has to infer intent from prose.
SET_UP = "set-up"
ALREADY_SATISFIED = "already-satisfied"
NO_ACTION = "no-action"
BLOCKED = "blocked"

# Post-execution readiness. `not-attempted` is the honest value before an apply:
# an unattempted capability is neither ready nor failed, and collapsing it into
# either would be the "installation success is readiness" mistake in reverse.
NOT_ATTEMPTED = "not-attempted"
READY = "ready"
NOT_READY = "not-ready"
FAILED = "failed"


@dataclass(frozen=True)
class CapabilityStatus:
    """One capability's full state, plan through post-execution.

    Carries the eight facts FR-011 requires so an agent can drive the journey
    without reasoning about packages: the capability, its strength, whether it is
    satisfied, whether it needs setup, the proposed action, any blocker, whether
    approval is required and met, and the post-execution status.
    """

    capability_id: str
    name: str
    strength: str
    reason: str
    satisfied: bool
    declined: bool
    needs_setup: bool
    proposed_action: str
    blocker: str | None
    approval_required: bool
    approval_met: bool
    post_execution_status: str
    next_action: str = ""


def _proposed_action(row: SetupPlanRow, contributing: bool) -> str:
    if row.blocker:
        return BLOCKED
    if row.satisfied:
        return ALREADY_SATISFIED
    return SET_UP if contributing else NO_ACTION


def capability_statuses(
    scope: DerivedScope,
    *,
    approval_met: bool = False,
    readiness: dict[str, str] | None = None,
    next_actions: dict[str, str] | None = None,
) -> tuple[CapabilityStatus, ...]:
    """One status row per derived capability, in the derived plan's own order.

    `readiness` is supplied by the caller AFTER an apply, from the control
    plane's verification and discovery results -- never computed here from an
    install return code (FR-016).
    """
    contributing = {row.capability.id for row in scope.contributing}
    readiness = readiness or {}
    next_actions = next_actions or {}
    rows = []
    for row in scope.plan.rows:
        needs = row.capability.id in contributing
        rows.append(
            CapabilityStatus(
                capability_id=row.capability.id,
                name=row.capability.name,
                strength=row.strength,
                reason=row.reason,
                satisfied=row.satisfied,
                declined=row.declined,
                needs_setup=needs,
                proposed_action=_proposed_action(row, needs),
                blocker=row.blocker,
                approval_required=needs,
                approval_met=bool(approval_met) if needs else False,
                post_execution_status=readiness.get(row.capability.id, NOT_ATTEMPTED),
                next_action=next_actions.get(row.capability.id, ""),
            )
        )
    return tuple(rows)


# --------------------------------------------------------------------------- #
# Presentation: capability language for humans (FR-009), detail on request
# (FR-010), and one JSON document for machines (FR-011).
# --------------------------------------------------------------------------- #

_MARK = {SET_UP: "o", ALREADY_SATISFIED: "+", NO_ACTION: "-", BLOCKED: "x"}

_LABEL = {
    ALREADY_SATISFIED: "Ready",
    BLOCKED: "Blocked",
}


def _status_label(status: CapabilityStatus) -> str:
    if status.proposed_action in _LABEL:
        return _LABEL[status.proposed_action]
    label = status.strength.replace("-", " ").title()
    return f"{label} -- needs setup" if status.needs_setup else label


def render_text(scope: DerivedScope, statuses: tuple[CapabilityStatus, ...]) -> str:
    """The normal presentation: capability names, reasons, and a change count.

    Deliberately ASCII, matching the spec-153 renderer: the Windows console
    charmap codec cannot encode the tick/cross glyphs. No package, MCP server,
    npm package, runtime name, or install command appears here -- that is the
    advanced path, and a test asserts the absence against the catalog's own
    coordinates rather than a hardcoded list.
    """
    width = max(len(status.name) for status in statuses)
    lines = ["Project Setup", ""]
    for status in statuses:
        mark = _MARK[status.proposed_action]
        lines.append(f"  {mark} {status.name:<{width}}  {_status_label(status)}")
    lines.append("")
    for status in statuses:
        lines.append(f"  {status.name}: {status.reason}")
        if status.blocker:
            lines.append(f"    blocked -- {status.blocker}")
        if status.next_action:
            lines.append(f"    next -- {status.next_action}")
    lines.append("")
    count = sum(1 for status in statuses if status.needs_setup)
    noun = "capability" if count == 1 else "capabilities"
    lines.append(
        f"Proposed changes: {count} {noun}"
        if count
        else "Proposed changes: none -- nothing to do"
    )
    for capability_id in scope.unsupported:
        lines.append(
            f"  unsupported: {capability_id} is needed but no catalog component "
            "satisfies it"
        )
    for capability_id in scope.outside_need:
        lines.append(
            f"  outside derived need: {capability_id} was requested but this "
            "project's evidence does not need it"
        )
    return "\n".join(lines)


def render_json(scope: DerivedScope, statuses: tuple[CapabilityStatus, ...]) -> str:
    """One JSON document and nothing else, for a machine consumer."""
    import json

    payload = {
        "proposed_changes": sum(1 for status in statuses if status.needs_setup),
        "blocked": scope.blocked,
        "blockers": list(scope.blockers),
        "unsupported": list(scope.unsupported),
        "outside_derived_need": list(scope.outside_need),
        "capabilities": [
            {
                "id": status.capability_id,
                "name": status.name,
                "strength": status.strength,
                "reason": status.reason,
                "satisfied": status.satisfied,
                "declined": status.declined,
                "needs_setup": status.needs_setup,
                "proposed_action": status.proposed_action,
                "blocker": status.blocker,
                "approval_required": status.approval_required,
                "approval_met": status.approval_met,
                "post_execution_status": status.post_execution_status,
                "next_action": status.next_action,
            }
            for status in statuses
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


@dataclass(frozen=True)
class TechnicalEvidence:
    """The provider detail behind one component -- on explicit request only.

    Every field is read from a surface that already owns it: identity, channel
    and role from the catalog, the resolved version from the lock, the
    verification basis from spec 153's catalog-sourced detail. Nothing here is
    recomputed (FR-010).
    """

    capability_id: str
    component_id: str
    channel: str
    role: str
    coordinate: str
    resolved_version: str
    verification_basis: str


def _locked_versions(root) -> dict[str, str]:
    """Resolved versions the lock records, or {} when there is no usable lock.

    A lock this cannot read is reported as no versions rather than raised: the
    advanced VIEW must not be the thing that fails a run. The installer's own
    fail-closed handling of a corrupt lock is unchanged and still authoritative.
    """
    from seshat.integrations.lockfile import LockError, read_lock

    try:
        lock = read_lock(root)
    except LockError:
        return {}
    if lock is None:
        return {}
    return {
        component_id: str(record.get("version") or "")
        for component_id, record in lock.components.items()
        if isinstance(record, dict)
    }


def technical_evidence(root, scope: DerivedScope) -> tuple[TechnicalEvidence, ...]:
    """Provider, component, resolved coordinate and verification basis.

    The ADVANCED path. The normal presentation never shows any of this, which is
    what lets a user who cannot name a package still review and approve a plan.
    """
    from seshat.integrations.catalog import component
    from seshat.integrations.derivation import technical_detail

    versions = _locked_versions(root)
    wanted = set(scope.component_ids)
    rows = []
    for detail in technical_detail(scope.plan):
        for provider in detail.providers:
            if provider.component_id not in wanted:
                continue
            rows.append(
                TechnicalEvidence(
                    capability_id=detail.capability_id,
                    component_id=provider.component_id,
                    channel=provider.channel,
                    role=provider.role,
                    coordinate=component(provider.component_id).coordinate,
                    resolved_version=versions.get(provider.component_id, ""),
                    verification_basis=provider.verification_basis,
                )
            )
    return tuple(rows)


# --------------------------------------------------------------------------- #
# Post-execution readiness (FR-016, FR-017).
# --------------------------------------------------------------------------- #


def _component_verdicts(root, outcome) -> dict[str, str]:
    """Per component: `ready`, `failed`, or `not-ready`, after a run.

    Three distinct outcomes, deliberately not two. `failed` is the control
    plane's own action set -- unavailable, conflict, incompatible, failed.
    `not-ready` is the quieter and more dangerous case: the install reported
    success but the control plane's presence check does not confirm it, which is
    precisely the state a "the install worked, so it is ready" reading would
    mislabel.
    """
    from seshat.integrations.catalog import component
    from seshat.integrations.installer import NEEDS_ACTION, verified_present

    unverified = {
        result.component for result in outcome.discovery if result.needs_action
    }
    verdicts: dict[str, str] = {}
    for row in outcome.rows:
        if row.status in NEEDS_ACTION:
            verdicts[row.component] = FAILED
            continue
        try:
            item = component(row.component)
        except KeyError:  # pragma: no cover - rows come from the catalog
            verdicts[row.component] = NOT_READY
            continue
        confirmed = verified_present(root, item) and row.component not in unverified
        verdicts[row.component] = READY if confirmed else NOT_READY
    return verdicts


def _next_action_for(state: str, component_ids: tuple[str, ...], outcome) -> str:
    """The one safe next action for a capability that is not ready.

    Taken from the owning surface's own wording where it has one -- a discovery
    result's `next_action`, or the failing row's detail -- rather than invented
    here, so the advice a user acts on is the advice the control plane gives.
    """
    if state == READY:
        return ""
    for result in outcome.discovery:
        if result.component in component_ids and result.needs_action:
            return result.next_action or "; ".join(result.blockers)
    for row in outcome.rows:
        if row.component in component_ids and row.needs_action:
            return row.detail
    return (
        "the install reported success but verification does not confirm it; "
        "re-run setup and inspect the component's technical evidence"
    )


def readiness_from(root, scope: DerivedScope, outcome) -> tuple[dict, dict]:
    """`(readiness, next_actions)` per capability, from verification only.

    A capability is `ready` only when EVERY component it contributed is
    confirmed by the control plane's presence check; one failed component makes
    the capability `failed` while leaving the other capabilities' verdicts
    untouched (FR-017). Installation success alone never reaches `ready`
    (FR-016).
    """
    verdicts = _component_verdicts(root, outcome)
    readiness: dict[str, str] = {}
    next_actions: dict[str, str] = {}
    for contribution in scope.contributions:
        states = {
            verdicts.get(component_id, NOT_READY)
            for component_id in contribution.component_ids
        }
        if FAILED in states:
            state = FAILED
        elif states == {READY}:
            state = READY
        else:
            state = NOT_READY
        readiness[contribution.capability_id] = state
        action = _next_action_for(state, contribution.component_ids, outcome)
        if action:
            next_actions[contribution.capability_id] = action
    return readiness, next_actions
