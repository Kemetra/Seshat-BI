"""Governed CLI boundary for statistical specification, execution, and review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

_EXIT_CODES = {
    "computed": 0,
    "withheld": 1,
    "refused": 2,
    "failed": 3,
    "unavailable": 4,
}


def _exit_code(outcome: str) -> int:
    """Return the stable process code for a categorical analysis outcome."""

    return _EXIT_CODES[outcome]


def _blocker(code: str, message: str, recovery: str) -> dict[str, str]:
    return {"code": code, "message": message, "recovery": recovery}


def _response(
    *,
    analysis_id: str | None,
    outcome: str,
    evidence_path: str | None = None,
    review_path: str | None = None,
    blockers: tuple[object, ...] = (),
) -> dict[str, object]:
    return {
        "analysis_id": analysis_id,
        "outcome": outcome,
        "evidence_path": evidence_path,
        "review_path": review_path,
        "blockers": [
            {
                "code": str(getattr(item, "code")),
                "message": str(getattr(item, "message")),
                "recovery": str(getattr(item, "recovery")),
            }
            if not isinstance(item, Mapping)
            else {
                "code": str(item["code"]),
                "message": str(item["message"]),
                "recovery": str(item["recovery"]),
            }
            for item in blockers
        ],
    }


def _emit(payload: Mapping[str, object], output_format: str) -> None:
    if output_format == "json":
        print(
            json.dumps(
                dict(payload),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return
    print(f"Analysis: {payload['analysis_id'] or 'unavailable'}")
    print(f"Outcome: {payload['outcome']}")
    if payload.get("evidence_path"):
        print(f"Evidence: {payload['evidence_path']}")
    if payload.get("review_path"):
        print(f"Review: {payload['review_path']}")
    blockers = payload.get("blockers")
    if isinstance(blockers, list) and blockers:
        for item in blockers:
            if isinstance(item, Mapping):
                print(f"Blocker {item['code']}: {item['message']}")
                print(f"Recovery: {item['recovery']}")
    else:
        print("Recovery: none")


def _contained_path(root: Path, raw: str, *, must_exist: bool) -> Path:
    candidate = Path(raw)
    resolved = (
        candidate.resolve(strict=False)
        if candidate.is_absolute()
        else (root / candidate).resolve(strict=False)
    )
    if not resolved.is_relative_to(root):
        raise ValueError("path must resolve under the repository")
    if must_exist and not resolved.is_file():
        raise ValueError("file does not exist under the repository")
    return resolved


def _display_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _load_spec(root: Path, raw: str):
    from seshat.statistical.schema import load_analysis_spec

    path = _contained_path(root, raw, must_exist=True)
    return load_analysis_spec(path, root)


def _spec_failure(errors: tuple[str, ...]) -> dict[str, object]:
    blockers = tuple(
        _blocker(
            "STAT_SPEC_REFUSED",
            error,
            "Correct and revalidate the governed analysis specification.",
        )
        for error in errors
    )
    return _response(
        analysis_id=None,
        outcome="refused",
        blockers=blockers,
    )


def _validate_command(root: Path, args: argparse.Namespace) -> dict[str, object]:
    from seshat.statistical.policy import evaluate_policy
    from seshat.statistical.schema import SpecRefused

    try:
        spec = _load_spec(root, args.spec)
        decision = evaluate_policy(root, spec)
    except SpecRefused as exc:
        return _spec_failure(exc.errors)
    except ValueError as exc:
        return _spec_failure((str(exc),))
    except Exception:
        return _response(
            analysis_id=None,
            outcome="failed",
            blockers=(
                _blocker(
                    "STAT_RUNTIME_FAILED",
                    "Statistical specification validation failed safely.",
                    "Inspect local logs, correct the workspace, and retry.",
                ),
            ),
        )
    outcome = "computed" if decision.allowed else "refused"
    return _response(
        analysis_id=spec.analysis_id,
        outcome=outcome,
        blockers=decision.blockers,
    )


def _unavailable_provider(code: str, message: str, recovery: str):
    from seshat.statistical.contracts import Blocker
    from seshat.statistical.providers.base import ProviderUnavailable

    class UnavailableProvider:
        def fetch(self, request):
            del request
            raise ProviderUnavailable(Blocker(code, message, recovery))

    return UnavailableProvider()


def _gold_provider():
    import os

    from seshat import cli
    from seshat.connection_env import as_connection_config
    from seshat.dialect import get_dialect
    from seshat.statistical.providers.base import ResourceLimits
    from seshat.statistical.providers.gold import GoldProvider

    try:
        engine = cli._current_engine()
        dialect = as_connection_config(lambda: get_dialect(engine))
        config = as_connection_config(lambda: dialect.resolve_config(dict(os.environ)))
    except ValueError:
        return _unavailable_provider(
            "STAT_PROVIDER_UNAVAILABLE",
            "The Gold database connection setting is invalid.",
            "Correct the gitignored .env database settings and retry.",
        )
    if config is None:
        return _unavailable_provider(
            "STAT_PROVIDER_UNAVAILABLE",
            "No Gold database connection is configured.",
            "Set DATABASE_URL or ANALYTICS_DB_* in the gitignored .env.",
        )
    if not cli._ensure_driver():
        return _unavailable_provider(
            "STAT_DEPENDENCY_UNAVAILABLE",
            "The optional Gold database driver is unavailable.",
            cli._extra_install_hint("db"),
        )
    limits = ResourceLimits()
    if not getattr(dialect, "supports_statement_timeout", False):
        # The provider advertises an enforceable query ceiling. An engine that
        # cannot cap a statement server-side would run unbounded under that
        # claim, so refuse instead of pretending the limit exists.
        return _unavailable_provider(
            "STAT_PROVIDER_UNAVAILABLE",
            "The configured Gold engine cannot enforce the governed query timeout.",
            "Point the analysis at the documented PostgreSQL Gold connection.",
        )
    try:
        runner = cli._make_runner(
            config, statement_timeout_ms=limits.timeout_seconds * 1000
        )
        return GoldProvider(runner, dialect, limits=limits)
    except Exception:
        return _unavailable_provider(
            "STAT_PROVIDER_UNAVAILABLE",
            "The read-only Gold database connection could not be opened.",
            "Verify the gitignored .env, network access, and database availability.",
        )


def _validated_evidence_payload(root: Path, evidence) -> dict[str, object]:
    from seshat.ecosystem_contracts import validate_json_contract
    from seshat.statistical.evidence import evidence_payload
    from seshat.statistical.schema import resolve_statistical_schema

    payload = evidence_payload(evidence)
    schema_path = resolve_statistical_schema(
        root, "statistical-analysis-evidence.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = validate_json_contract(payload, schema)
    if errors:
        raise ValueError("runtime evidence did not satisfy its JSON contract")
    return payload


def _write_artifacts(root: Path, spec, evidence) -> tuple[str, str]:
    from seshat.statistical.evidence import write_evidence
    from seshat.statistical.render import write_review

    _validated_evidence_payload(root, evidence)
    evidence_path = root / Path(*spec.outputs["evidence"].parts)
    review_path = root / Path(*spec.outputs["review"].parts)
    written_evidence = write_evidence(evidence_path, evidence, repo_root=root)
    written_review = write_review(review_path, evidence, repo_root=root)
    return (
        _display_path(root, written_evidence),
        _display_path(root, written_review),
    )


def _run_command(root: Path, args: argparse.Namespace) -> dict[str, object]:
    from seshat.connection_env import applied_dotenv
    from seshat.dbt.redaction import EnvironmentConfigError
    from seshat.statistical.providers.local_csv import LocalCsvProvider
    from seshat.statistical.runtime import run_analysis
    from seshat.statistical.schema import SpecRefused

    try:
        spec = _load_spec(root, args.spec)
    except SpecRefused as exc:
        return _spec_failure(exc.errors)
    except ValueError as exc:
        return _spec_failure((str(exc),))
    except Exception:
        return _response(
            analysis_id=None,
            outcome="failed",
            blockers=(
                _blocker(
                    "STAT_RUNTIME_FAILED",
                    "The analysis specification could not be loaded safely.",
                    "Inspect local logs, correct the workspace, and retry.",
                ),
            ),
        )

    declared_provider = spec.provider.get("kind")
    if declared_provider != args.provider:
        return _response(
            analysis_id=spec.analysis_id,
            outcome="refused",
            blockers=(
                _blocker(
                    "STAT_PROVIDER_REQUEST_REFUSED",
                    "The selected provider differs from the governed specification.",
                    f"Use the declared {declared_provider!s} provider.",
                ),
            ),
        )

    try:
        if args.provider == "local_csv":
            if not args.input:
                raise ValueError("--input is required for local_csv")
            provider = LocalCsvProvider(
                _contained_path(root, args.input, must_exist=True)
            )
            evidence = run_analysis(root, spec, provider)
        else:
            try:
                with applied_dotenv(root):
                    evidence = run_analysis(root, spec, _gold_provider())
            except EnvironmentConfigError:
                evidence = run_analysis(
                    root,
                    spec,
                    _unavailable_provider(
                        "STAT_PROVIDER_UNAVAILABLE",
                        "The workspace .env could not be read safely.",
                        "Correct the gitignored .env syntax and retry.",
                    ),
                )
    except ValueError as exc:
        return _response(
            analysis_id=spec.analysis_id,
            outcome="refused",
            blockers=(
                _blocker(
                    "STAT_PROVIDER_REQUEST_REFUSED",
                    str(exc),
                    "Provide a repo-contained input accepted by the governed provider.",
                ),
            ),
        )
    except Exception:
        return _response(
            analysis_id=spec.analysis_id,
            outcome="failed",
            blockers=(
                _blocker(
                    "STAT_RUNTIME_FAILED",
                    "Statistical execution failed safely.",
                    "Inspect local logs and retry after correcting the runtime.",
                ),
            ),
        )

    try:
        evidence_path, review_path = _write_artifacts(root, spec, evidence)
    except Exception:
        return _response(
            analysis_id=spec.analysis_id,
            outcome="failed",
            blockers=(
                _blocker(
                    "STAT_ARTIFACT_WRITE_FAILED",
                    "Schema-valid statistical artifacts could not be written.",
                    "Correct the evidence contract or workspace permissions and retry.",
                ),
            ),
        )
    return _response(
        analysis_id=spec.analysis_id,
        outcome=evidence.outcome.value,
        evidence_path=evidence_path,
        review_path=review_path,
        blockers=evidence.blockers,
    )


def _evidence_from_payload(payload: Mapping[str, object]):
    from seshat.statistical.contracts import (
        Blocker,
        Diagnostic,
        Estimate,
        Interval,
        Outcome,
        TestStatistic,
    )
    from seshat.statistical.evidence import build_evidence

    def records(name: str, record_type):
        values = payload.get(name, [])
        return tuple(record_type(**item) for item in values)

    return build_evidence(
        engine_version=str(payload["engine_version"]),
        invocation_id=str(payload["invocation_id"]),
        started_at=str(payload["started_at"]),
        completed_at=str(payload["completed_at"]),
        analysis=payload["analysis"],
        governance=payload["governance"],
        input_provenance=payload["input"],
        method=payload["method"],
        outcome=Outcome(str(payload["outcome"])),
        estimates=records("estimates", Estimate),
        effect_sizes=records("effect_sizes", Estimate),
        intervals=records("intervals", Interval),
        tests=records("tests", TestStatistic),
        diagnostics=records("diagnostics", Diagnostic),
        warnings=tuple(str(item) for item in payload["warnings"]),
        blockers=records("blockers", Blocker),
        cautions=tuple(str(item) for item in payload["cautions"]),
    )


def _load_evidence(root: Path, raw: str):
    from seshat.ecosystem_contracts import validate_json_contract
    from seshat.statistical.schema import resolve_statistical_schema

    path = _contained_path(root, raw, must_exist=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("evidence must be a JSON object")
    schema_path = resolve_statistical_schema(
        root, "statistical-analysis-evidence.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = validate_json_contract(payload, schema)
    if errors:
        raise ValueError("evidence does not satisfy its JSON contract")
    return path, payload, _evidence_from_payload(payload)


def _render_command(root: Path, args: argparse.Namespace) -> dict[str, object]:
    from seshat.statistical.render import write_review

    try:
        evidence_path, payload, evidence = _load_evidence(root, args.evidence)
        analysis = payload["analysis"]
        if not isinstance(analysis, Mapping):
            raise ValueError("evidence analysis reference is invalid")
        spec = _load_spec(root, str(analysis["path"]))
        review_path = root / Path(*spec.outputs["review"].parts)
        written = write_review(review_path, evidence, repo_root=root)
    except (
        OSError,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ):
        return _response(
            analysis_id=None,
            outcome="refused",
            blockers=(
                _blocker(
                    "STAT_EVIDENCE_REFUSED",
                    "The evidence artifact or its governed analysis is invalid.",
                    "Provide schema-valid repo-contained evidence and retry.",
                ),
            ),
        )
    except Exception:
        return _response(
            analysis_id=None,
            outcome="failed",
            blockers=(
                _blocker(
                    "STAT_RUNTIME_FAILED",
                    "Human review rendering failed safely.",
                    "Inspect local logs, correct the workspace, and retry.",
                ),
            ),
        )
    return _response(
        analysis_id=spec.analysis_id,
        outcome=evidence.outcome.value,
        evidence_path=_display_path(root, evidence_path),
        review_path=_display_path(root, written),
        blockers=evidence.blockers,
    )


def analyze_main(args: argparse.Namespace) -> int:
    """Dispatch one closed analysis command and emit one stable response."""

    root = Path(args.repo).resolve()
    if not root.is_dir():
        payload = _response(
            analysis_id=None,
            outcome="refused",
            blockers=(
                _blocker(
                    "STAT_REPOSITORY_REFUSED",
                    "The repository root is not an existing directory.",
                    "Pass --repo with an existing workspace root.",
                ),
            ),
        )
    elif args.analysis_command == "validate":
        payload = _validate_command(root, args)
    elif args.analysis_command == "run":
        payload = _run_command(root, args)
    else:
        payload = _render_command(root, args)
    _emit(payload, args.output_format)
    return _exit_code(str(payload["outcome"]))
