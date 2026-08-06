"""The compatibility policy -- one place that decides what may install together.

Resolving each component to its own latest release is not enough: `dbt-core` and
`dbt-postgres` must agree, and Dagster must stay compatible with the running
Python and with Seshat's own adapter. Those rules live HERE rather than inside
each resolver, so there is one place to read when a bump is refused.

The posture, which the repo already ratified once:

* The CURRENT exact pins are the known compatibility baseline.
* Newer is not a reason. A component is not bumped merely because a newer
  release exists.
* When the absolute latest is incompatible, the newest KNOWN COMPATIBLE version
  is retained and the rejection is explained.
* One component is never silently downgraded to satisfy another. When spec 135
  met exactly this case -- no released `dagster-dbt` accepted `dbt-core` 1.12 --
  the owner's ruling (Ahmed Shaaban, 2026-07-17) was to DROP the unused library,
  not to downgrade the dbt pins. A refusal that names the conflict is the
  correct output; a quiet downgrade is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from seshat.integrations.catalog import Component
from seshat.integrations.resolvers import CONFLICT, INCOMPATIBLE, Resolution
from seshat.integrations.versions import parse_version

# The known compatibility baseline: the exact pins this repository already
# declares and tests. Sourced from `pyproject.toml`'s `[dbt]` extra and
# `orchestration/dagster/pyproject.toml`. A resolved version below its baseline
# is a downgrade and is refused.
BASELINE_PINS: dict[str, str] = {
    "dbt-core": "1.12.0",
    "dbt-postgres": "1.10.2",
    "dagster": "1.13.15",
}

# The minimum Python the kit itself declares (`requires-python = ">=3.13"`).
MINIMUM_PYTHON: tuple[int, ...] = (3, 13)

# Components whose MAJOR.MINOR must agree, by compat group. dbt adapters track
# their core release line, so a 1.12 core with a 1.10 adapter is a real
# mismatch rather than a cosmetic one.
_AGREE_ON_MINOR: dict[str, tuple[str, ...]] = {}

# dbt's adapter versioning does NOT track core's minor (dbt-core 1.12 pairs with
# dbt-postgres 1.10), so the pair is validated against the recorded baseline
# rather than by comparing their numbers to each other.
_PAIRED_GROUPS = ("dbt",)


@dataclass(frozen=True)
class Verdict:
    """The outcome of the cross-component policy pass."""

    resolutions: tuple[Resolution, ...]
    ok: bool
    reasons: tuple[str, ...] = ()


def _baseline_regression(item: Component, resolved: Resolution) -> str | None:
    """A resolved version older than the recorded baseline, if any."""
    baseline = BASELINE_PINS.get(item.id)
    if not baseline or not resolved.version:
        return None
    got = parse_version(resolved.version)
    known = parse_version(baseline)
    if got is None or known is None:
        return None
    if got < known:
        return (
            f"{item.id} resolved to {resolved.version}, which is older than the "
            f"known compatible baseline {baseline}; a component is never "
            f"silently downgraded to satisfy another"
        )
    return None


def _pair_reason(group: str, members: list[tuple[Component, Resolution]]) -> str | None:
    """Whether a paired group resolved coherently.

    A pair is coherent when every member resolved. When one member cannot
    resolve, the pair is a CONFLICT rather than a per-component failure: the
    operator's action is about the pair, and installing half a pair is worse
    than installing neither.
    """
    unresolved = [item.id for item, res in members if not res.ok]
    if unresolved and len(unresolved) != len(members):
        resolved = [
            f"{item.id}=={res.version}"
            for item, res in members
            if res.ok and res.version
        ]
        return (
            f"the {group} components must be installed as a compatible set, but "
            f"{', '.join(unresolved)} did not resolve while "
            f"{', '.join(resolved) or 'the rest'} did; refusing a partial set "
            f"rather than downgrading either side"
        )
    return None


@dataclass(frozen=True)
class _Pass:
    """What one policy pass found: reasons to report, components to reject."""

    reasons: tuple[str, ...] = ()
    rejected: dict[str, tuple[str, str]] = field(default_factory=dict)


def _python_floor_pass(
    pairs: list[tuple[Component, Resolution]],
    python_version: tuple[int, ...] | None,
) -> _Pass:
    """An interpreter below the kit's floor rejects the whole set at once."""
    if python_version is None or python_version >= MINIMUM_PYTHON:
        return _Pass()
    need = ".".join(str(part) for part in MINIMUM_PYTHON)
    have = ".".join(str(part) for part in python_version)
    reason = f"Seshat requires Python >= {need}; this interpreter is {have}"
    return _Pass(
        reasons=(reason,),
        rejected={item.id: (INCOMPATIBLE, reason) for item, _res in pairs},
    )


def _baseline_pass(pairs: list[tuple[Component, Resolution]]) -> _Pass:
    """Each component resolving below its recorded compatibility baseline."""
    reasons: list[str] = []
    rejected: dict[str, tuple[str, str]] = {}
    for item, resolved in pairs:
        regression = _baseline_regression(item, resolved)
        if regression:
            reasons.append(regression)
            rejected[item.id] = (INCOMPATIBLE, regression)
    return _Pass(reasons=tuple(reasons), rejected=rejected)


def _compat_groups(
    pairs: list[tuple[Component, Resolution]],
) -> dict[str, list[tuple[Component, Resolution]]]:
    groups: dict[str, list[tuple[Component, Resolution]]] = {}
    for item, resolved in pairs:
        if item.compat_group:
            groups.setdefault(item.compat_group, []).append((item, resolved))
    return groups


def _paired_group_pass(
    groups: dict[str, list[tuple[Component, Resolution]]],
) -> _Pass:
    """A group that must install as a set but only half resolved."""
    reasons: list[str] = []
    rejected: dict[str, tuple[str, str]] = {}
    for group in _PAIRED_GROUPS:
        members = groups.get(group)
        if not members:
            continue
        reason = _pair_reason(group, members)
        if reason:
            reasons.append(reason)
            for item, _res in members:
                rejected.setdefault(item.id, (CONFLICT, reason))
    return _Pass(reasons=tuple(reasons), rejected=rejected)


def _minor_agreement_pass(
    groups: dict[str, list[tuple[Component, Resolution]]],
) -> _Pass:  # pragma: no cover - reserved; _AGREE_ON_MINOR is empty
    """A group whose members must share a MAJOR.MINOR but do not."""
    reasons: list[str] = []
    rejected: dict[str, tuple[str, str]] = {}
    for group, expected in _AGREE_ON_MINOR.items():
        members = [pair for pair in groups.get(group, []) if pair[0].id in expected]
        minors = {
            (parse_version(res.version) or ())[:2]
            for _item, res in members
            if res.version
        }
        if len(minors) > 1:
            reason = f"the {group} components resolved to disagreeing minor versions"
            reasons.append(reason)
            for item, _res in members:
                rejected.setdefault(item.id, (CONFLICT, reason))
    return _Pass(reasons=tuple(reasons), rejected=rejected)


def apply_policy(
    pairs: list[tuple[Component, Resolution]],
    *,
    python_version: tuple[int, ...] | None = None,
) -> Verdict:
    """Validate resolved components against each other and the baseline.

    Returns every resolution -- rewritten to `incompatible`/`conflict` where the
    policy refuses -- plus the reasons. Nothing is mutated in place, so a caller
    can render both what was resolved and why it was refused.
    """
    groups = _compat_groups(pairs)
    interpreter = _python_floor_pass(pairs, python_version)
    baseline = _baseline_pass(pairs)
    paired = _paired_group_pass(groups)
    minor = _minor_agreement_pass(groups)

    # Reasons read in policy order: the interpreter, then the baseline, then the
    # group rules.
    reasons = [
        reason
        for policy_pass in (interpreter, baseline, paired, minor)
        for reason in policy_pass.reasons
    ]

    # Rejections resolve in PRECEDENCE order, which is not the same order. A
    # baseline regression names one component and its exact versions, so it
    # outranks the blanket interpreter rejection covering every component; the
    # group rules only claim components nothing more specific already did.
    rejected: dict[str, tuple[str, str]] = {}
    for policy_pass in (baseline, interpreter, paired, minor):
        for component_id, verdict in policy_pass.rejected.items():
            rejected.setdefault(component_id, verdict)

    final = tuple(
        replace(
            resolved,
            ok=False,
            status=rejected[item.id][0],
            reason=rejected[item.id][1],
        )
        if item.id in rejected
        else resolved
        for item, resolved in pairs
    )
    return Verdict(resolutions=final, ok=not reasons, reasons=tuple(reasons))
