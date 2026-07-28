"""Outcome-safe orchestration for governed statistical evidence."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Mapping
from uuid import uuid4

from . import ENGINE_VERSION
from .contracts import (
    AnalysisEvidence,
    AnalysisSpec,
    AnalysisWithheld,
    Blocker,
    MethodContext,
    MethodResult,
    Outcome,
)
from .evidence import (
    EvidenceFindings,
    EvidenceReferences,
    EvidenceRun,
    build_evidence,
)
from .policy import PolicyContext, evaluate_policy
from .providers.base import (
    DataProvider,
    ProviderUnavailable,
    RectangularData,
    build_data_request,
)
from .registry import METHODS, RegistryRefused, get_descriptor, load_runner
from .schema import SpecRefused

_NO_INPUT_DIGEST = hashlib.sha256(b"no-input-acquired").hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path, missing_marker: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return hashlib.sha256(missing_marker.encode("utf-8")).hexdigest()


def _analysis_reference(spec: AnalysisSpec) -> Mapping[str, object]:
    path = spec.source_path or PurePosixPath(
        f"mappings/{spec.subject}/analyses/{spec.analysis_id}.yaml"
    )
    digest = (
        spec.source_sha256
        or hashlib.sha256(
            json.dumps(
                [
                    spec.analysis_id,
                    spec.revision,
                    spec.subject,
                    spec.method.method_id,
                    spec.method.version,
                ],
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
    )
    return {"path": path.as_posix(), "revision": spec.revision, "sha256": digest}


def _positive_revision(value: object, fallback: int) -> int:
    try:
        revision = int(str(value))
    except (TypeError, ValueError):
        return fallback
    return revision if revision >= 1 else fallback


def _governance_reference(
    repo_root: Path,
    path: PurePosixPath,
    revision: int,
    observed_state: str,
) -> Mapping[str, object]:
    relative = path.as_posix()
    resolved = repo_root / Path(*path.parts)
    return {
        "path": relative,
        "revision": revision,
        "sha256": _sha256_file(resolved, f"unavailable:{relative}"),
        "observed_state": observed_state,
    }


def _governance(
    repo_root: Path,
    spec: AnalysisSpec,
    context: PolicyContext | None,
) -> Mapping[str, object]:
    approved = context is not None
    readiness_revision = _positive_revision(
        context.readiness_revision if context else None, spec.revision
    )
    return {
        "readiness": (
            _governance_reference(
                repo_root,
                spec.readiness_status,
                readiness_revision,
                "policy-approved" if approved else "cited",
            ),
        ),
        "metric_contracts": tuple(
            _governance_reference(
                repo_root,
                path,
                spec.revision,
                "owner-approved" if approved else "cited",
            )
            for path in spec.metric_contracts
        ),
    }


def _input(spec: AnalysisSpec, data: RectangularData | None) -> Mapping[str, object]:
    if data is None:
        provider_kind = spec.provider.get("kind")
        if provider_kind not in {"local_csv", "gold"}:
            provider_kind = "local_csv"
        return {
            "provider_kind": provider_kind,
            "source_digest": _NO_INPUT_DIGEST,
            "observation_grain": str(spec.population.get("grain", "unavailable")),
            "input_count": 0,
            "excluded_count": 0,
            "exclusion_reasons": (),
        }
    return {
        "provider_kind": data.provenance.kind,
        "source_digest": data.provenance.data_digest,
        "observation_grain": str(spec.population.get("grain", "unavailable")),
        "input_count": data.total_count,
        "excluded_count": data.excluded_count,
        "exclusion_reasons": data.exclusion_reasons,
    }


def _method(spec: AnalysisSpec) -> Mapping[str, object]:
    descriptor = METHODS.get(spec.method.method_id)
    libraries = (
        tuple(
            {
                "name": name,
                "version": _library_version(name),
            }
            for name in descriptor.libraries
        )
        if descriptor is not None
        else ()
    )
    return {
        "id": spec.method.method_id,
        "version": spec.method.version,
        "libraries": libraries,
        "parameters": spec.method.parameters,
        "random_seed": spec.random_seed,
    }


def _library_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


@dataclass(frozen=True, slots=True)
class _Invocation:
    """The identity of one run: which repository, spec, id, and start time."""

    repo_root: Path
    spec: AnalysisSpec
    invocation_id: str
    started_at: str


@dataclass(frozen=True, slots=True)
class _Observed:
    """Whatever the run had actually established when it produced evidence."""

    context: PolicyContext | None = None
    data: RectangularData | None = None
    result: MethodResult | None = None
    blockers: tuple[Blocker, ...] = ()


def _evidence(
    invocation: _Invocation, outcome: Outcome, observed: _Observed = _Observed()
) -> AnalysisEvidence:
    spec = invocation.spec
    return build_evidence(
        EvidenceRun(
            ENGINE_VERSION, invocation.invocation_id, invocation.started_at, _now()
        ),
        EvidenceReferences(
            analysis=_analysis_reference(spec),
            governance=_governance(invocation.repo_root, spec, observed.context),
            input_provenance=_input(spec, observed.data),
            method=_method(spec),
        ),
        EvidenceFindings(outcome, observed.result or MethodResult(), observed.blockers),
    )


def _single_blocker(code: str, message: str, recovery: str) -> tuple[Blocker, ...]:
    return (Blocker(code=code, message=message, recovery=recovery),)


def _refused(invocation: _Invocation, observed: _Observed) -> AnalysisEvidence:
    return _evidence(invocation, Outcome.REFUSED, observed)


def _blocked(
    invocation: _Invocation,
    observed: _Observed,
    outcome: Outcome,
    blocker: Blocker,
) -> AnalysisEvidence:
    """Report one categorical outcome carrying exactly one blocker."""

    return _evidence(invocation, outcome, replace(observed, blockers=(blocker,)))


def _runtime_failure(message: str, recovery: str) -> Blocker:
    return Blocker("STAT_RUNTIME_FAILED", message, recovery)


def _missing_dependency(message: str, recovery: str) -> Blocker:
    return Blocker("STAT_DEPENDENCY_UNAVAILABLE", message, recovery)


def _policy_decision(invocation: _Invocation):
    """Evaluate policy into (decision, evidence): exactly one is not None."""

    try:
        return evaluate_policy(invocation.repo_root, invocation.spec), None
    except SpecRefused as exc:
        blockers = tuple(
            Blocker(
                "STAT_SPEC_REFUSED",
                error,
                "Correct and revalidate the governed analysis specification.",
            )
            for error in exc.errors
        )
        return None, _refused(invocation, _Observed(blockers=blockers))
    except Exception:
        return None, _blocked(
            invocation,
            _Observed(),
            Outcome.FAILED,
            _runtime_failure(
                "Statistical policy evaluation failed safely.",
                "Inspect the local logs and retry after correcting the runtime.",
            ),
        )


def _method_descriptor(invocation: _Invocation, observed: _Observed):
    """Resolve the governed method descriptor, or the evidence that refuses it."""

    spec = invocation.spec
    try:
        descriptor = get_descriptor(spec.method.method_id)
    except RegistryRefused:
        return None, _refused(
            invocation,
            replace(
                observed,
                blockers=_single_blocker(
                    "STAT_METHOD_REFUSED",
                    "The requested statistical method is outside the governed catalog.",
                    "Choose a method defined by the analysis schema.",
                ),
            ),
        )
    if spec.method.version != descriptor.version:
        # The registry ships exactly one implementation per method id. Running it
        # for another declared version would file this computation as evidence
        # for a version that was never executed.
        return None, _refused(
            invocation,
            replace(
                observed,
                blockers=_single_blocker(
                    "STAT_METHOD_VERSION_UNKNOWN",
                    "The requested method version is not the governed implementation "
                    f"version {descriptor.version}.",
                    "Declare the governed method version recorded by the registry.",
                ),
            ),
        )
    missing_roles = descriptor.required_roles - set(spec.roles)
    if missing_roles:
        return None, _refused(
            invocation,
            replace(
                observed,
                blockers=_single_blocker(
                    "STAT_METHOD_ROLE_MISSING",
                    "The method lacks required governed roles: "
                    + ", ".join(sorted(missing_roles))
                    + ".",
                    "Bind every required role to an approved column.",
                ),
            ),
        )
    return descriptor, None


def _acquired_data(
    invocation: _Invocation, observed: _Observed, provider: DataProvider
):
    """Acquire provider data, or the evidence that reports why it is unavailable."""

    try:
        request = build_data_request(invocation.spec, observed.context)
        return provider.fetch(request), None
    except ProviderUnavailable as exc:
        return None, _blocked(invocation, observed, Outcome.UNAVAILABLE, exc.blocker)
    except ImportError:
        return None, _blocked(
            invocation,
            observed,
            Outcome.UNAVAILABLE,
            _missing_dependency(
                "A provider dependency is unavailable.",
                "Install the required Seshat BI optional dependency.",
            ),
        )
    except Exception:
        return None, _blocked(
            invocation,
            observed,
            Outcome.FAILED,
            _runtime_failure(
                "Statistical data acquisition failed safely.",
                "Inspect the local logs and retry after correcting the provider.",
            ),
        )


def _method_result(invocation: _Invocation, observed: _Observed, descriptor):
    """Run the loaded method, or the evidence that withholds or reports failure."""

    try:
        runner = load_runner(descriptor)
        result = runner(
            MethodContext(
                spec=invocation.spec, policy=observed.context, data=observed.data
            )
        )
        if not isinstance(result, MethodResult):
            raise TypeError("method returned an invalid result contract")
        return result, None
    except AnalysisWithheld as exc:
        return None, _evidence(
            invocation,
            Outcome.WITHHELD,
            replace(observed, blockers=exc.blockers),
        )
    except ImportError:
        return None, _blocked(
            invocation,
            observed,
            Outcome.UNAVAILABLE,
            _missing_dependency(
                "A numerical method dependency is unavailable.",
                f'Install the "{descriptor.optional_dependency}" optional extra.',
            ),
        )
    except Exception:
        return None, _blocked(
            invocation,
            observed,
            Outcome.FAILED,
            _runtime_failure(
                "Statistical method execution failed safely.",
                "Inspect the local logs and retry after correcting the method input.",
            ),
        )


def run_analysis(
    repo_root: Path, spec: AnalysisSpec, provider: DataProvider
) -> AnalysisEvidence:
    """Run policy, acquisition, and one closed method into categorical evidence."""

    invocation = _Invocation(repo_root.resolve(), spec, f"stat-{uuid4().hex}", _now())
    decision, evidence = _policy_decision(invocation)
    if evidence is not None:
        return evidence
    if not decision.allowed or decision.context is None:
        return _refused(invocation, _Observed(blockers=decision.blockers))
    observed = _Observed(context=decision.context)
    descriptor, evidence = _method_descriptor(invocation, observed)
    if evidence is not None:
        return evidence
    data, evidence = _acquired_data(invocation, observed, provider)
    if evidence is not None:
        return evidence
    observed = replace(observed, data=data)
    result, evidence = _method_result(invocation, observed, descriptor)
    if evidence is not None:
        return evidence
    return _evidence(invocation, Outcome.COMPUTED, replace(observed, result=result))
