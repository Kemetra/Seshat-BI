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
        root, result.run_id, tables, evidence.RunMeta(started=started)
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


def dagster_main(args) -> int:
    handlers = {"doctor": _run_doctor, "run": _run_run, "evidence": _run_evidence}
    handler = handlers.get(getattr(args, "dagster_cmd", None))
    if handler is None:
        return 1
    try:
        return handler(args)
    except Exception as error:  # the contract forbids raw tracebacks
        from seshat.dagster_adapter.redaction import redact_text

        print(f"internal error: {redact_text(str(error))}", file=sys.stderr)
        return 4
