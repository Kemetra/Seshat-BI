"""`seshat pbi-mcp doctor|generate-config|preflight` -- presentation + exits.

Exit codes mirror the dagster family: 0 success/advisory (including the
graceful runtime-absent skip), 1 usage, 2 refusal (blocked recommendation,
blocked preflight, secret-scan refusal, overwrite refusal). All pbi_mcp
imports are LAZY so `seshat check` / CI never load this family.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _prog(args: object) -> str:
    from seshat import cli

    return cli._prog(args)


def _doctor_payload(facts, rec) -> dict:
    return {
        "detected": {
            "node_runtime": facts.node_runtime,
            "vendored_runtime": facts.vendored_runtime,
            "mcp_config": facts.mcp_config,
            "pbip_project": facts.pbip_project,
            "semantic_model_ready": facts.semantic_model_ready,
            "semantic_ready_tables": list(facts.semantic_ready_tables),
            "publish_ready_approval": facts.publish_ready_approval,
        },
        "recommendation": {
            "intent": rec.intent,
            "surface": rec.surface,
            "why": rec.why,
            "missing_prerequisites": list(rec.missing_prerequisites),
            "next_human_step": rec.next_human_step,
            "blocked": rec.blocked,
        },
    }


def _print_doctor_text(prog: str, facts, rec) -> None:
    verdict = "BLOCKED" if rec.blocked else "recommended"
    print(f"{prog} pbi-mcp doctor: intent '{rec.intent}' -> {rec.surface} ({verdict})")
    print(f"  why: {rec.why}")
    for prereq in rec.missing_prerequisites:
        print(f"  missing prerequisite: {prereq}")
    print(f"  next human step: {rec.next_human_step}")
    print(
        "  detected: "
        f"node={facts.node_runtime} vendored={facts.vendored_runtime} "
        f"config={facts.mcp_config} pbip={facts.pbip_project} "
        f"semantic_model_ready={facts.semantic_model_ready} "
        f"publish_ready_approval={facts.publish_ready_approval}"
    )
    print(
        "(advisory -- grants no approval, advances no stage, authorizes no "
        "MCP call; F016 stays parked)"
    )


def _run_doctor(args) -> int:
    from seshat.pbi_mcp.detect import detect_facts
    from seshat.pbi_mcp.recommend import AdvisoryWriteError, recommend, write_advisory

    facts = detect_facts(Path(args.repo))
    rec = recommend(args.intent, facts)
    if args.as_json:
        print(json.dumps(_doctor_payload(facts, rec), indent=2, sort_keys=True))
    else:
        _print_doctor_text(_prog(args), facts, rec)
    if getattr(args, "write_advisory", False):
        try:
            written = write_advisory(Path(args.repo), facts, rec)
        except AdvisoryWriteError as refusal:
            print(f"{refusal}", file=sys.stderr)
            return 2
        print(f"advisory written: {written.as_posix()}")
    return 2 if rec.blocked else 0


def _run_generate_config(args) -> int:
    from seshat.pbi_mcp.generate import (
        GenerateRefusal,
        render_mcp_template,
        render_setup_doc,
        write_generated,
    )
    from seshat.pbi_mcp.scan import GeneratedSecretError

    try:
        text = (
            render_setup_doc()
            if args.setup_doc
            else (render_mcp_template(args.transport))
        )
        if args.out is None:
            print(text, end="")
            return 0
        written = write_generated(Path(args.out), text)
    except (GenerateRefusal, GeneratedSecretError) as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 2
    print(f"generated: {written.as_posix()}")
    return 0


def _print_preflight_text(prog: str, result) -> None:
    print(f"{prog} pbi-mcp preflight: {result.status} (mode: {result.mode})")
    if result.server is not None:
        print(
            f"  server: {result.server.name} {result.server.version} "
            f"(protocol {result.server.protocol_version}, "
            f"{len(result.server.tools)} tool(s))"
        )
    if result.target is not None:
        print(f"  target: {result.target} allowlisted={result.target_allowlisted}")
    for blocker in result.blockers:
        print(f"  [blocker] {blocker.id} {blocker.detail}")
    for note in result.notes:
        print(f"  note: {note}")


def _run_preflight(args) -> int:
    from seshat.pbi_mcp.preflight import (
        MissingRuntimeTransport,
        PreflightRequest,
        render_result_json,
        run_preflight,
        write_artifact,
    )
    from seshat.pbi_mcp.scan import GeneratedSecretError

    result = run_preflight(
        PreflightRequest(
            repo_root=Path(args.repo),
            transport=MissingRuntimeTransport(),
            target=args.target,
            target_allowlist=tuple(args.allow),
            required_tools=tuple(args.require_tool),
        )
    )
    if args.as_json:
        print(render_result_json(result, generated_at="(not written)"), end="")
    else:
        _print_preflight_text(_prog(args), result)
    if getattr(args, "write_artifact", False):
        try:
            written = write_artifact(Path(args.repo), result)
        except GeneratedSecretError as refusal:
            print(f"refused: {refusal}", file=sys.stderr)
            return 2
        print(f"artifact written: {written.as_posix()}")
    return 2 if result.status == "blocked" else 0


def pbi_mcp_main(args) -> int:
    handlers = {
        "doctor": _run_doctor,
        "generate-config": _run_generate_config,
        "preflight": _run_preflight,
    }
    handler = handlers.get(getattr(args, "pbi_mcp_cmd", None))
    if handler is None:
        return 1
    return handler(args)
