"""`seshat dagster doctor|run|evidence` -- presentation + exit mapping.

Exit codes are stable API (specs/134-activate-dagster-mvp/contracts/dagster-cli.md):
0 success, 1 usage, 2 preflight/gate refusal, 3 run failed (the CI signal),
4 unexpected internal error (redacted). All adapter imports are LAZY (inside
the handler) so `seshat check` / CI never load this family.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def _print_findings(findings, as_json: bool) -> None:
    if as_json:
        payload = [
            {
                "id": finding.id,
                "severity": finding.severity,
                "message": finding.message,
                "remedy": finding.remedy,
            }
            for finding in findings
        ]
        print(json.dumps({"findings": payload}, indent=2))
        return
    for finding in findings:
        line = f"[{finding.severity}] {finding.id} {finding.message}"
        if finding.remedy and finding.remedy != "none":
            line += f" (remedy: {finding.remedy})"
        print(line)


def _run_doctor(args) -> int:
    from seshat.dagster_adapter import doctor

    findings = doctor.run_doctor(Path(args.repo))
    _print_findings(findings, args.as_json)
    return 2 if doctor.has_blockers(findings) else 0


def _refused_by_doctor(root: Path, args) -> bool:
    from seshat.dagster_adapter import doctor

    findings = doctor.run_doctor(root)
    if not doctor.has_blockers(findings):
        return False
    _print_findings(findings, args.as_json)
    print("refused: fix the blockers above, then re-run.", file=sys.stderr)
    return True


def _render_evidence(root: Path, run_id: str) -> Path | None:
    from seshat.dagster_adapter import evidence

    try:
        return evidence.write_run_evidence(root, run_id)
    except (ValueError, FileNotFoundError) as error:
        print(f"evidence rendering refused: {error}", file=sys.stderr)
        return None


def _print_run_outcome(args, result, summary: dict, rendered: Path | None) -> None:
    if args.as_json:
        payload = {
            "run_id": result.run_id,
            "run_status": summary["run_status"],
            "evidence": str(rendered) if rendered else None,
        }
        print(json.dumps(payload, indent=2))
        return
    print(f"run {result.run_id}: {summary['run_status']}")
    if rendered:
        print(f"evidence: {rendered}")
    if result.output and summary["run_status"] == "failed":
        print(result.output)


def _run_run(args) -> int:
    from seshat.dagster_adapter import evidence, runner
    from seshat.dagster_adapter.gate import list_mapped_tables

    root = Path(args.repo)
    if _refused_by_doctor(root, args):
        return 2
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        result = runner.execute_run(root, args.job, table=args.table)
    except runner.RunnerError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    tables = [args.table] if args.table else list_mapped_tables(root)
    summary = evidence.finalize_run(
        root,
        result.run_id,
        tables,
        evidence.RunMeta(started=started, child_exit_code=result.exit_code),
    )
    rendered = _render_evidence(root, result.run_id)
    _print_run_outcome(args, result, summary, rendered)
    return 0 if summary["run_status"] == "succeeded" else 3


def _print_run_list(runs: list[dict], as_json: bool) -> None:
    if as_json:
        print(json.dumps({"runs": runs}, indent=2))
        return
    for run in runs:
        print(
            f"{run['run_id']}  {run['run_status']}  started {run['started']}  "
            f"tables {', '.join(run['tables'])}"
        )


def _run_evidence(args) -> int:
    from seshat.dagster_adapter import evidence

    root = Path(args.repo)
    if not args.run_id:
        runs = evidence.list_runs(root)
        if not runs:
            print("no runs recorded under .seshat/dagster/runs/")
            return 0
        _print_run_list(runs, args.as_json)
        return 0
    try:
        rendered = evidence.write_run_evidence(root, args.run_id)
    except (FileNotFoundError, ValueError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps({"run_id": args.run_id, "evidence": str(rendered)}, indent=2))
    else:
        print(f"evidence: {rendered}")
    return 0


def _run_init(args) -> int:
    """Materialize the governed orchestration project (issue #325)."""
    from seshat.governed_projects import dagster_init

    report = dagster_init(Path(args.repo))
    if args.as_json:
        print(
            json.dumps(
                {
                    "written": list(report.written),
                    "kept": list(report.kept),
                    "notes": list(report.notes),
                },
                indent=2,
            )
        )
        return 0
    print(
        f"materialized {len(report.written)} governed orchestration files "
        f"(kept {len(report.kept)} existing)"
    )
    for note in report.notes:
        print(note)
    return 0


# The DB-touching verbs resolve the DSN (doctor's DAG-DSN check, the runner's
# child env) from ``os.environ``. Wrap ONLY these in the workspace ``.env``
# overlay so the documented ``ANALYTICS_DB_*`` / ``DATABASE_URL`` values resolve
# consistently with `retail validate` (#340/#348). ``evidence`` / ``init`` touch
# no DB and are left unwrapped.
_DB_TOUCHING_VERBS = frozenset({"doctor", "run"})


def _run_guarded(handler, args) -> int:
    """Run one handler, mapping any unexpected exception to the redacted exit 4.

    CRITICAL: this runs INSIDE the ``applied_dotenv`` overlay for DB-touching
    verbs, so ``redact_text`` -- which discovers literal secrets from the CURRENT
    ``os.environ`` -- still sees the `.env`-loaded credentials and redacts them.
    Redacting after the overlay is torn down would print a `.env`-only secret
    unredacted, violating the all-output-redacted contract (Codex P1, #348).
    """
    from seshat.safe_write import SafeWriteError

    try:
        return handler(args)
    except SafeWriteError as error:
        # `dagster init` refused a path-safety violation (symlinked orchestration/
        # parent or output path). That is a preflight/gate refusal (exit 2), not
        # an unexpected internal error -- mirror the dbt boundary (#351). Caught
        # before the generic handler since SafeWriteError is a ValueError.
        print(f"refused: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # the contract forbids raw tracebacks
        from seshat.dagster_adapter.redaction import redact_text

        print(f"internal error: {redact_text(str(error))}", file=sys.stderr)
        return 4


def _dispatch(args, handler) -> int:
    """Run one dagster verb, applying the workspace `.env` for DB-touching verbs.

    A single wrap around ``run`` covers BOTH its doctor preflight and the runner
    child env (both read ``os.environ`` inside this body); ``doctor`` reads it
    for its own DSN finding. The redaction guard (``_run_guarded``) is nested
    INSIDE the overlay so exception redaction sees the `.env` secrets before
    ``applied_dotenv`` restores ``os.environ`` on exit.
    """
    from pathlib import Path

    from seshat.connection_env import applied_dotenv

    if getattr(args, "dagster_cmd", None) not in _DB_TOUCHING_VERBS:
        return _run_guarded(handler, args)
    with applied_dotenv(Path(args.repo)):
        return _run_guarded(handler, args)


def dagster_main(args) -> int:
    # Local import keeps module load lazy (the family imports nothing eagerly);
    # `seshat.dbt.redaction` does not pull in the dagster adapter.
    from seshat.dbt.redaction import EnvironmentConfigError

    handlers = {
        "doctor": _run_doctor,
        "run": _run_run,
        "evidence": _run_evidence,
        "init": _run_init,
    }
    handler = handlers.get(getattr(args, "dagster_cmd", None))
    if handler is None:
        return 1
    try:
        return _dispatch(args, handler)
    except EnvironmentConfigError as error:
        # A malformed workspace `.env` is refused at context ENTRY (before any
        # secret is applied), so this is safe to report outside the overlay: a
        # preflight refusal (exit 2), NOT the redacted exit-4 path.
        print(f"refused: could not read the workspace .env: {error}", file=sys.stderr)
        return 2
