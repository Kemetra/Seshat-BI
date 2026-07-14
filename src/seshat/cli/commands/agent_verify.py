"""`seshat agent verify --target claude|codex` handler (spec 129).

Produces categorical PASS/BLOCKED/UNAVAILABLE evidence that a shipped agent
integration installs correctly and ships the governance contract intact --
never a score, rank, pass-rate, grade, or rolled-up "certified"/"verified"
result (FR-003). Static-first: inspects the installed bundle and the
committed governance contract; never launches a live agent, never opens a
database, never reaches the network, never requires a running IDE
(FR-006/FR-007/FR-008). Grants no approval and advances no readiness stage
(FR-004).

Exit codes (stable):
  0  every required check is PASS
  1  at least one required check is BLOCKED
  2  input defect: unknown --target, or an uncontained --output/publish path
  3  at least one required check is UNAVAILABLE and none is BLOCKED (a
     truthful "not fully verifiable" result -- distinct from 0 so an
     UNAVAILABLE-only run never reads as a pass)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from seshat.agent_verify.model import PerCheckResult


def _print_check(result: PerCheckResult) -> None:
    print(f"[{result.verdict}] {result.check_id} ({result.evidence_class})")
    if result.verdict == "PASS":
        for item in result.evidence:
            print(f"    evidence: {item}")
    elif result.verdict == "BLOCKED":
        for reason in result.blocking_reasons:
            print(f"    blocked: {reason}")
    else:
        print(f"    unavailable: {result.unavailable_reason}")


def _print_report(target: str, results: Sequence[PerCheckResult]) -> None:
    print(f"agent verify --target {target}")
    for result in results:
        _print_check(result)
    blocked = [item.check_id for item in results if item.verdict == "BLOCKED"]
    unavailable = [item.check_id for item in results if item.verdict == "UNAVAILABLE"]
    if not blocked and not unavailable:
        print(
            "summary: every required check is PASS (evidence only; grants no approval)"
        )
    else:
        parts = []
        if blocked:
            parts.append(f"BLOCKED: {', '.join(blocked)}")
        if unavailable:
            parts.append(f"UNAVAILABLE: {', '.join(unavailable)}")
        print("summary: " + "; ".join(parts))


def _run_verify(args: argparse.Namespace) -> int:
    from seshat.agent_verify.checks import run_all_checks
    from seshat.agent_verify.record import build_record, publish_record, write_record
    from seshat.agent_verify.targets import UnknownVerifyTargetError, resolve_target

    repo_root = Path(args.repo).resolve()
    try:
        target_spec = resolve_target(args.target)
    except UnknownVerifyTargetError as exc:
        print(f"error: {exc}")
        return 2

    results = run_all_checks(target_spec, repo_root)
    record = build_record(args.target, results, repo_root=repo_root)

    try:
        written = write_record(record, repo_root=repo_root, output=args.output)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    if args.output_format == "json":
        print(json.dumps(record.to_document(), indent=2))
    else:
        _print_report(args.target, results)
    print(f"written: {written.relative_to(repo_root).as_posix()}")

    if args.publish:
        try:
            outcome = publish_record(record, requested=True)
        except ValueError as exc:
            print(f"publish refused: {exc}")
            return 2
        disclosure_status = outcome["disclosure"]["status"]
        print(f"publish: {outcome['status']} (disclosure={disclosure_status})")

    if any(item.verdict == "BLOCKED" for item in results):
        return 1
    if any(item.verdict == "UNAVAILABLE" for item in results):
        return 3
    return 0


def agent_verify_main(args: argparse.Namespace) -> int:
    if args.agent_command == "verify":
        return _run_verify(args)
    print(f"error: unsupported agent subcommand {args.agent_command!r}")
    return 2
