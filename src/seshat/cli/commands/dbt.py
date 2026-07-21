"""Lazy handler for the governed ``seshat dbt`` helper workflow."""

from __future__ import annotations

import importlib.metadata
import json
import re
import subprocess
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_hex
from types import SimpleNamespace
from typing import Any

import yaml

from seshat.dbt import (
    DBT_CORE_VERSION,
    DBT_POSTGRES_VERSION,
)
from seshat.dbt.artifacts import (
    ArtifactIntegrityError,
    cross_check_execution,
    load_manifest,
    load_run_results,
)
from seshat.dbt.contracts import (
    ArtifactSet,
    Blocker,
    GovernanceError,
    InvocationResult,
    Operation,
    PlanEnvelope,
    RunContext,
)
from seshat.dbt.evidence import (
    build_evidence,
    parse_parity_rows,
    write_evidence,
)
from seshat.dbt.fact_semantics import load_fact_semantics
from seshat.dbt.gate import evaluate_mapping_gate, resolve_working_set
from seshat.dbt.planning import (
    PlanDrift,
    create_plan,
    load_plan,
    require_accepted_plan,
    save_plan,
)
from seshat.dbt.project import validate_project
from seshat.dbt.redaction import (
    DBT_ENVIRONMENT_KEYS,
    EnvironmentConfigError,
    load_child_environment,
    sanitize,
    secret_values,
)
from seshat.dbt.runner import (
    DbtUnavailable,
    LockUnavailable,
    build_dbt_argv,
    invoke_dbt,
    resolve_dbt_executable,
    target_lock,
)

_CONNECTION_FIELDS = (
    "host",
    "port",
    "user",
    "password",
    "dbname",
    "schema",
    "sslmode",
)
_TABLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class HandledDbtFailure(RuntimeError):
    """A dbt command completed with an expected model/test process failure."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Stable non-plan CLI result shape."""

    command: str
    table_id: str | None
    outcome: str
    exit_code: int
    message: str
    evidence_path: str | None = None
    blocking_reasons: tuple[dict[str, str], ...] = ()


def _root(args: Any) -> Path:
    return Path(args.repo).resolve()


def _pass(command: str, table_id: str | None, message: str) -> CommandResult:
    return CommandResult(command, table_id, "pass", 0, message)


def _governance_error(code: str, message: str) -> GovernanceError:
    return GovernanceError(code, message)


def _pending(message: str) -> DbtUnavailable:
    return DbtUnavailable(f"[PENDING LIVE PROFILE]: {message}")


def _verify_runtime_versions() -> None:
    expected_versions = {
        "dbt-core": DBT_CORE_VERSION,
        "dbt-postgres": DBT_POSTGRES_VERSION,
    }
    for package, expected in expected_versions.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise _pending(
                f"{package} is unavailable; install `seshat-bi[dbt]` "
                f"(or pin it directly: "
                f'pipx inject seshat-bi --force "{package}=={expected}")'
            ) from exc
        if actual != expected:
            # State the remedy, not just the expected version. The natural
            # `pipx inject seshat-bi dbt-core dbt-postgres` pulls the LATEST
            # release, so a fresh customer install lands on an unsupported
            # version with no obvious next step; `--force` is required because a
            # plain re-inject of an already-injected package is refused (#407).
            raise _pending(
                f"{package} version {actual} is unsupported; expected {expected}. "
                f'run: pipx inject seshat-bi --force "{package}=={expected}" '
                f'(pipx install), or pip install "{package}=={expected}" '
                f"(plain venv)"
            )
    resolve_dbt_executable()


def _verify_required_paths(root: Path) -> None:
    paths = (
        root / "dbt",
        root / "dbt" / "dbt_project.yml",
        root / "dbt" / "selectors.yml",
        root / "profiles.example.yml",
        root / "schemas" / "dbt-run-evidence.schema.json",
    )
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise _pending("required dbt files are missing: " + ", ".join(missing))


def _verify_ignore_rules(root: Path) -> None:
    ignore_lines = set((root / ".gitignore").read_text(encoding="utf-8").splitlines())
    required_ignores = {
        "/profiles.yml",
        "/.user.yml",
        "/dbt/target/",
        "/dbt/logs/",
        "/.seshat/dbt/",
    }
    if not required_ignores <= ignore_lines:
        raise _pending("dbt local-output ignore rules are incomplete")


def _profile_document(path: Path, label: str) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise _pending(f"{label} is missing or invalid") from exc
    if not isinstance(document, dict):
        raise _pending(f"{label} must be a YAML mapping")
    return document


def _verify_local_profile(root: Path) -> None:
    local_profile = root / "profiles.yml"
    if not local_profile.is_file():
        raise _pending("copy profiles.example.yml to the gitignored profiles.yml")
    local = _profile_document(local_profile, "profiles.yml")
    governed = _profile_document(root / "profiles.example.yml", "profiles.example.yml")
    if local != governed:
        raise _pending("profiles.yml must match the exact governed template")


def _profile_git_result(root: Path, *args: str) -> int:
    completed = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", *args, "--", "profiles.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    return completed.returncode


def _verify_profile_git_boundary(root: Path) -> None:
    ignored = _profile_git_result(root, "check-ignore", "--quiet")
    tracked = _profile_git_result(root, "ls-files", "--error-unmatch")
    if (ignored, tracked) != (0, 1):
        raise _pending("profiles.yml must remain untracked and gitignored")


def _verify_environment(root: Path) -> None:
    environment = load_child_environment(root)
    missing_keys = [key for key in DBT_ENVIRONMENT_KEYS if not environment.get(key)]
    if missing_keys:
        raise _pending(
            "required dbt environment keys are missing: " + ", ".join(missing_keys)
        )


def _doctor(args: Any) -> CommandResult:
    root = _root(args)
    _verify_runtime_versions()
    _verify_required_paths(root)
    _verify_ignore_rules(root)
    _verify_local_profile(root)
    _verify_profile_git_boundary(root)
    _verify_environment(root)
    return _pass("doctor", None, "dbt prerequisites are available")


def _validated_project(root: Path, table_id: str):
    working_set = resolve_working_set(root, table_id)
    gate = evaluate_mapping_gate(working_set)
    if not gate.allowed:
        details = "; ".join(
            f"{blocker.code}: {blocker.message}" for blocker in gate.blocking_reasons
        )
        raise _governance_error("DBT_MAPPING_GATE_BLOCKED", details)
    # Surface missing/invalid gold_star.fact parity tags at validate time, not
    # first at plan time -- the same fail-closed loader create_plan uses.
    load_fact_semantics(working_set.source_map)
    environment = load_child_environment(root)
    project = validate_project(
        root,
        working_set,
        target_schema=environment.get("SESHAT_DBT_SCHEMA") or None,
    )
    if not project.valid:
        details = "; ".join(
            f"{blocker.code}: {blocker.message}" for blocker in project.blocking_reasons
        )
        raise _governance_error("DBT_PROJECT_BLOCKED", details)
    return project


def _validate(args: Any) -> CommandResult:
    _validated_project(_root(args), args.table)
    return _pass("validate", args.table, "static dbt validation completed")


def _plan(args: Any) -> PlanEnvelope:
    root = _root(args)
    plan = create_plan(root, args.table, invoke_dbt)
    save_plan(root, plan)
    return PlanEnvelope(digest=_plan_digest(plan), plan=plan)


def _plan_digest(plan) -> str:
    from seshat.dbt.planning import plan_digest

    return plan_digest(plan)


def _invocation_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + token_hex(4)


def _context(
    root: Path, plan, operation: Operation, environment: dict[str, str]
) -> RunContext:
    return RunContext(
        repo_root=root,
        project_dir=root / "dbt",
        profiles_dir=root,
        operation=operation,
        table_id=plan.table_id,
        selector=plan.runtime.selector,
        target=plan.runtime.target,
        run_dir=root / ".seshat" / "dbt" / "runs" / _invocation_id(),
        environment=environment,
    )


def _snapshot(path: Path, target: Path) -> None:
    try:
        target.write_bytes(path.read_bytes())
    except OSError as exc:
        raise ArtifactIntegrityError(
            f"local dbt artifact could not be preserved: {path.name}"
        ) from exc


def _invocation_payload(
    invocation: InvocationResult,
    manifest_sha256: str,
    run_results_sha256: str,
) -> dict[str, Any]:
    return {
        "invocation_id": invocation.invocation_id,
        "operation": invocation.operation.value,
        "argv_summary": list(invocation.argv_summary),
        "return_code": invocation.return_code,
        "started_at": invocation.started_at,
        "completed_at": invocation.completed_at,
        "manifest_sha256": manifest_sha256,
        "run_results_sha256": run_results_sha256,
    }


def _execute(args: Any, operation: Operation) -> CommandResult:
    root = _root(args)
    plan = create_plan(root, args.table, invoke_dbt)
    require_accepted_plan(args.accept_plan, plan)
    environment = load_child_environment(root)
    context = _context(root, plan, operation, environment)
    with target_lock(root, plan.table_id, plan.runtime.target):
        invocation = invoke_dbt(context, build_dbt_argv(operation, context))
        manifest = load_manifest(invocation.target_dir / "manifest.json")
        main_results = load_run_results(invocation.target_dir / "run_results.json")
        snapshot_dir = context.run_dir / "artifacts"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        _snapshot(
            invocation.target_dir / "manifest.json",
            snapshot_dir / "manifest.json",
        )
        _snapshot(
            invocation.target_dir / "run_results.json",
            snapshot_dir / "run_results.json",
        )

        show_context = replace(context, operation=Operation.SHOW)
        show = invoke_dbt(show_context, build_dbt_argv(Operation.SHOW, show_context))
        if show.return_code != 0:
            raise HandledDbtFailure("dbt parity audit could not be inspected")
        parity = parse_parity_rows(show.stdout)
        parity_results = load_run_results(show.target_dir / "run_results.json")
        _snapshot(
            show.target_dir / "run_results.json",
            snapshot_dir / "parity_run_results.json",
        )
        (snapshot_dir / "show-parity.jsonl").write_text(
            show.stdout, encoding="utf-8", newline="\n"
        )
        (snapshot_dir / "invocation.json").write_text(
            json.dumps(
                _invocation_payload(
                    invocation,
                    manifest.sha256,
                    main_results.sha256,
                ),
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

    evidence = build_evidence(
        plan,
        invocation,
        ArtifactSet(manifest, (main_results, parity_results)),
        parity,
    )
    evidence_path = write_evidence(root, evidence)
    blockers = tuple(_blocker_dict(blocker) for blocker in evidence.blocking_reasons)
    return CommandResult(
        command=operation.value,
        table_id=plan.table_id,
        outcome=evidence.outcome,
        exit_code=evidence.seshat_exit_code,
        message=(
            "derived dbt evidence completed; named-human approval is still required"
        ),
        evidence_path=evidence_path.relative_to(root).as_posix(),
        blocking_reasons=blockers,
    )


def _build(args: Any) -> CommandResult:
    return _execute(args, Operation.BUILD)


def _test(args: Any) -> CommandResult:
    return _execute(args, Operation.TEST)


def run_governed_build(
    root: Path, table: str, operation: Operation = Operation.BUILD
) -> CommandResult:
    """Run the FULL governed dbt build for one table, self-accepting the plan.

    The unattended caller (the spec-135 dagster dbt-engine bridge) has no human
    to review the plan, so it recomputes the plan and passes ITS OWN digest as
    the acceptance token (FR-014 self-accept-by-recompute; plan-review R1). The
    digest still functions as a DRIFT-GUARD: ``_execute`` INDEPENDENTLY recomputes
    the plan and ``require_accepted_plan`` refuses if the working set drifted
    between the two computes -- so this must NOT be short-circuited into a single
    compute (that would make the acceptance check tautological). The governed
    selector is table-wide by governance (spec 133 FR-023); the caller supplies
    no selector, target, profile, or dbt argument. On any governed failure this
    RAISES the same typed error the CLI raises (the caller maps it to a dagster
    outcome); on a completed governed run it returns the CommandResult carrying
    the sanitized evidence path.
    """
    root = Path(root).resolve()
    plan = create_plan(root, table, invoke_dbt)
    args = SimpleNamespace(
        repo=str(root),
        table=table,
        accept_plan=_plan_digest(plan),
    )
    return _execute(args, operation)


def _inside_runs(root: Path, supplied: str) -> Path:
    runs = (root / ".seshat" / "dbt" / "runs").resolve(strict=False)
    candidate = (root / supplied).resolve(strict=False)
    try:
        candidate.relative_to(runs)
    except ValueError as exc:
        raise ArtifactIntegrityError(
            "inspect-run artifacts must stay under .seshat/dbt/runs"
        ) from exc
    if not candidate.is_dir():
        raise ArtifactIntegrityError("inspect-run artifact directory is missing")
    nested = candidate / "artifacts"
    return nested if nested.is_dir() else candidate


def _invocation_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.joinpath("invocation.json").read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise TypeError("invocation metadata must be an object")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise ArtifactIntegrityError(
            "inspect-run invocation metadata is invalid"
        ) from exc


def _verify_snapshot_hashes(
    value: dict[str, Any], manifest: Any, main_results: Any
) -> None:
    recorded = (value.get("manifest_sha256"), value.get("run_results_sha256"))
    actual = (manifest.sha256, main_results.sha256)
    if recorded != actual:
        raise ArtifactIntegrityError(
            "inspect-run snapshot hashes do not match invocation metadata"
        )


def _load_invocation(path: Path, manifest: Any, main_results: Any) -> InvocationResult:
    value = _invocation_document(path)
    _verify_snapshot_hashes(value, manifest, main_results)
    try:
        operation = Operation(value["operation"])
        return InvocationResult(
            invocation_id=value["invocation_id"],
            operation=operation,
            argv_summary=tuple(value["argv_summary"]),
            return_code=value["return_code"],
            started_at=value["started_at"],
            completed_at=value["completed_at"],
            stdout="",
            stderr="",
            target_dir=path,
            log_dir=path,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ArtifactIntegrityError(
            "inspect-run invocation metadata is invalid"
        ) from exc


def _inspect(args: Any) -> CommandResult:
    root = _root(args)
    artifact_dir = _inside_runs(root, args.artifacts)
    envelope = load_plan(root, args.table)
    manifest = load_manifest(artifact_dir / "manifest.json")
    main = load_run_results(artifact_dir / "run_results.json")
    parity_results = load_run_results(artifact_dir / "parity_run_results.json")
    cross_check_execution(envelope.plan, main)
    invocation = _load_invocation(artifact_dir, manifest, main)
    parity = parse_parity_rows(
        artifact_dir.joinpath("show-parity.jsonl").read_text(encoding="utf-8")
    )
    evidence = build_evidence(
        envelope.plan,
        invocation,
        ArtifactSet(manifest, (main, parity_results)),
        parity,
    )
    path = write_evidence(root, evidence)
    return CommandResult(
        command="inspect-run",
        table_id=args.table,
        outcome=evidence.outcome,
        exit_code=evidence.seshat_exit_code,
        message="local dbt run artifacts were validated as derived evidence",
        evidence_path=path.relative_to(root).as_posix(),
        blocking_reasons=tuple(
            _blocker_dict(blocker) for blocker in evidence.blocking_reasons
        ),
    )


def _init(args: Any) -> CommandResult:
    """Materialize the generic governed dbt working set (issue #325)."""
    from seshat.governed_projects import dbt_init

    report = dbt_init(_root(args))
    message = "; ".join(
        (
            f"materialized {len(report.written)} governed dbt files "
            f"(kept {len(report.kept)} existing)",
            *report.notes,
        )
    )
    return _pass("init", None, message)


def _scaffold(args: Any) -> CommandResult:
    """Materialize the governed dbt model set from an approved map (issue #406)."""
    from seshat.dbt.scaffold import scaffold_models

    report = scaffold_models(_root(args), args.table)
    message = "; ".join(
        (
            f"scaffolded {len(report.written)} governed dbt files "
            f"(kept {len(report.kept)} existing, merged {len(report.merged)})",
            *report.notes,
        )
    )
    return _pass("scaffold", args.table, message)


_COMMANDS = {
    "doctor": _doctor,
    "validate": _validate,
    "scaffold": _scaffold,
    "plan": _plan,
    "build": _build,
    "test": _test,
    "inspect-run": _inspect,
    "init": _init,
}


def _blocker_dict(blocker: Blocker) -> dict[str, str]:
    value = {"code": blocker.code, "message": blocker.message}
    if blocker.assertion_id is not None:
        value["assertion_id"] = blocker.assertion_id
    return value


def _clean_message(args: Any, error: Exception) -> str:
    root = _root(args)
    try:
        environment = load_child_environment(root)
    except EnvironmentConfigError:
        environment = {}
    cleaned = sanitize(str(error), secret_values(environment), root)
    return str(cleaned)


def _error_result(args: Any, error: Exception, exit_code: int) -> CommandResult:
    outcomes = {1: "failed", 2: "unavailable", 3: "blocked", 4: "failed"}
    codes = {
        1: "DBT_EXECUTION_FAILED",
        2: "DBT_UNAVAILABLE",
        3: "DBT_GOVERNANCE_REFUSAL",
        4: "DBT_ARTIFACT_INTEGRITY",
    }
    code = error.code if isinstance(error, GovernanceError) else codes[exit_code]
    message = _clean_message(args, error)
    return CommandResult(
        command=args.dbt_command,
        table_id=getattr(args, "table", None),
        outcome=outcomes[exit_code],
        exit_code=exit_code,
        message=message,
        blocking_reasons=({"code": code, "message": message},),
    )


def _emit_plan(args: Any, envelope: PlanEnvelope) -> None:
    if args.output_format == "json":
        print(
            json.dumps(
                asdict(envelope),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
        return
    print("dbt plan: pass")
    print(f"table_id: {envelope.plan.table_id}")
    print(f"accept_plan: {envelope.digest}")
    print(
        "next: seshat dbt build --table "
        f"{envelope.plan.table_id} --accept-plan {envelope.digest}"
    )


def _emit_result(args: Any, result: CommandResult) -> None:
    payload = asdict(result)
    payload["blocking_reasons"] = list(result.blocking_reasons)
    if args.output_format == "json":
        print(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
        )
        return
    print(f"dbt {result.command}: {result.outcome}")
    print(result.message)
    if result.evidence_path:
        print(f"evidence: {result.evidence_path}")
    for blocker in result.blocking_reasons:
        print(f"blocker: {blocker['code']}: {blocker['message']}")


def dbt_main(args: Any) -> int:
    """Dispatch one governed dbt helper and normalize expected failures."""
    from seshat.safe_write import SafeWriteError

    handler = _COMMANDS[args.dbt_command]
    try:
        result = handler(args)
    except HandledDbtFailure as exc:
        result = _error_result(args, exc, 1)
    except DbtUnavailable as exc:
        result = _error_result(args, exc, 2)
    except (GovernanceError, PlanDrift, LockUnavailable, SafeWriteError) as exc:
        # SafeWriteError: `dbt init` refused a path-safety violation (symlinked
        # component, non-file collision) -- a clean refusal (exit 3), never an
        # uncaught traceback at the dbt boundary (Codex P2, #351).
        result = _error_result(args, exc, 3)
    except (ArtifactIntegrityError, EnvironmentConfigError) as exc:
        result = _error_result(args, exc, 4)
    if isinstance(result, PlanEnvelope):
        _emit_plan(args, result)
        return 0
    _emit_result(args, result)
    return result.exit_code


__all__ = [
    "ArtifactIntegrityError",
    "CommandResult",
    "DbtUnavailable",
    "GovernanceError",
    "HandledDbtFailure",
    "LockUnavailable",
    "Operation",
    "PlanDrift",
    "dbt_main",
    "run_governed_build",
]
