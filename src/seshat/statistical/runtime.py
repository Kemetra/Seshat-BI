"""Outcome-safe orchestration for governed statistical evidence."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
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
from .evidence import build_evidence
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


def _evidence(
    *,
    repo_root: Path,
    spec: AnalysisSpec,
    invocation_id: str,
    started_at: str,
    outcome: Outcome,
    context: PolicyContext | None = None,
    data: RectangularData | None = None,
    result: MethodResult | None = None,
    blockers: tuple[Blocker, ...] = (),
) -> AnalysisEvidence:
    result = result or MethodResult()
    return build_evidence(
        engine_version=ENGINE_VERSION,
        invocation_id=invocation_id,
        started_at=started_at,
        completed_at=_now(),
        analysis=_analysis_reference(spec),
        governance=_governance(repo_root, spec, context),
        input_provenance=_input(spec, data),
        method=_method(spec),
        outcome=outcome,
        estimates=result.estimates,
        effect_sizes=result.effect_sizes,
        intervals=result.intervals,
        tests=result.tests,
        diagnostics=result.diagnostics,
        warnings=result.warnings,
        blockers=blockers,
        cautions=result.interpretation_cautions,
    )


def _single_blocker(code: str, message: str, recovery: str) -> tuple[Blocker, ...]:
    return (Blocker(code=code, message=message, recovery=recovery),)


def run_analysis(
    repo_root: Path, spec: AnalysisSpec, provider: DataProvider
) -> AnalysisEvidence:
    """Run policy, acquisition, and one closed method into categorical evidence."""

    root = repo_root.resolve()
    invocation_id = f"stat-{uuid4().hex}"
    started_at = _now()
    try:
        decision = evaluate_policy(root, spec)
    except SpecRefused as exc:
        blockers = tuple(
            Blocker(
                "STAT_SPEC_REFUSED",
                error,
                "Correct and revalidate the governed analysis specification.",
            )
            for error in exc.errors
        )
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.REFUSED,
            blockers=blockers,
        )
    except Exception:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.FAILED,
            blockers=_single_blocker(
                "STAT_RUNTIME_FAILED",
                "Statistical policy evaluation failed safely.",
                "Inspect the local logs and retry after correcting the runtime.",
            ),
        )

    if not decision.allowed or decision.context is None:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.REFUSED,
            blockers=decision.blockers,
        )
    context = decision.context
    try:
        descriptor = get_descriptor(spec.method.method_id)
    except RegistryRefused:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.REFUSED,
            context=context,
            blockers=_single_blocker(
                "STAT_METHOD_REFUSED",
                "The requested statistical method is outside the governed catalog.",
                "Choose a method defined by the analysis schema.",
            ),
        )

    if spec.method.version != descriptor.version:
        # The registry ships exactly one implementation per method id. Running it
        # for another declared version would file this computation as evidence
        # for a version that was never executed.
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.REFUSED,
            context=context,
            blockers=_single_blocker(
                "STAT_METHOD_VERSION_UNKNOWN",
                "The requested method version is not the governed implementation "
                f"version {descriptor.version}.",
                "Declare the governed method version recorded by the registry.",
            ),
        )

    missing_roles = descriptor.required_roles - set(spec.roles)
    if missing_roles:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.REFUSED,
            context=context,
            blockers=_single_blocker(
                "STAT_METHOD_ROLE_MISSING",
                "The method lacks required governed roles: "
                + ", ".join(sorted(missing_roles))
                + ".",
                "Bind every required role to an approved column.",
            ),
        )

    try:
        data = provider.fetch(build_data_request(spec, context))
    except ProviderUnavailable as exc:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.UNAVAILABLE,
            context=context,
            blockers=(exc.blocker,),
        )
    except ImportError:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.UNAVAILABLE,
            context=context,
            blockers=_single_blocker(
                "STAT_DEPENDENCY_UNAVAILABLE",
                "A provider dependency is unavailable.",
                "Install the required Seshat BI optional dependency.",
            ),
        )
    except Exception:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.FAILED,
            context=context,
            blockers=_single_blocker(
                "STAT_RUNTIME_FAILED",
                "Statistical data acquisition failed safely.",
                "Inspect the local logs and retry after correcting the provider.",
            ),
        )

    try:
        runner = load_runner(descriptor)
        result = runner(MethodContext(spec=spec, policy=context, data=data))
        if not isinstance(result, MethodResult):
            raise TypeError("method returned an invalid result contract")
    except AnalysisWithheld as exc:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.WITHHELD,
            context=context,
            data=data,
            blockers=exc.blockers,
        )
    except ImportError:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.UNAVAILABLE,
            context=context,
            data=data,
            blockers=_single_blocker(
                "STAT_DEPENDENCY_UNAVAILABLE",
                "A numerical method dependency is unavailable.",
                f'Install the "{descriptor.optional_dependency}" optional extra.',
            ),
        )
    except Exception:
        return _evidence(
            repo_root=root,
            spec=spec,
            invocation_id=invocation_id,
            started_at=started_at,
            outcome=Outcome.FAILED,
            context=context,
            data=data,
            blockers=_single_blocker(
                "STAT_RUNTIME_FAILED",
                "Statistical method execution failed safely.",
                "Inspect the local logs and retry after correcting the method input.",
            ),
        )
    return _evidence(
        repo_root=root,
        spec=spec,
        invocation_id=invocation_id,
        started_at=started_at,
        outcome=Outcome.COMPUTED,
        context=context,
        data=data,
        result=result,
    )
