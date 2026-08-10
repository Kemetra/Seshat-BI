"""`seshat pbi-mcp doctor|generate-config|preflight` -- presentation + exits.

Exit codes mirror the dagster family: 0 success/advisory (including the
graceful runtime-absent skip), 1 usage, 2 refusal (blocked recommendation,
blocked preflight, secret-scan refusal, overwrite refusal). All pbi_mcp
imports are LAZY so `seshat check` / CI never load this family.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
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
            "target": facts.target,
            "semantic_model_ready": facts.semantic_model_ready,
            "semantic_ready_tables": list(facts.semantic_ready_tables),
            "target_semantic_model_ready": facts.target_semantic_model_ready,
            "dashboard_ready": facts.dashboard_ready,
            "dashboard_ready_tables": list(facts.dashboard_ready_tables),
            "dashboard_design_approval": facts.dashboard_design_approval,
            "publish_ready_approval": facts.publish_ready_approval,
            "official_report_skills": list(facts.official_report_skills),
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
        f"target={facts.target or 'none'} "
        f"target_semantic_model_ready={facts.target_semantic_model_ready} "
        f"dashboard_ready={facts.dashboard_ready} "
        f"dashboard_design_approval={facts.dashboard_design_approval} "
        f"publish_ready_approval={facts.publish_ready_approval}"
    )
    print(
        "(advisory -- grants no approval, advances no stage, authorizes no "
        "MCP call; F016 stays parked)"
    )


def _run_doctor(args) -> int:
    from seshat.integrations.catalog import component
    from seshat.integrations.discovery import inspect_locked_component
    from seshat.pbi_mcp.detect import detect_facts
    from seshat.pbi_mcp.recommend import AdvisoryWriteError, recommend, write_advisory

    root = Path(args.repo)
    facts = detect_facts(root, target=args.target)
    discovery_blockers: tuple[str, ...] = ()
    harness = getattr(args, "harness", None)
    if harness:
        discovery = inspect_locked_component(root, "fabric-skills", harness)
        if discovery.discoverable is True:
            item = component("fabric-skills")
            activation = next(
                entry for entry in item.skill_activations if entry.harness == harness
            )
            report_skills = tuple(
                target.name
                for target in activation.targets
                if target.name.startswith("powerbi-report-")
            )
            facts = replace(facts, official_report_skills=report_skills)
        else:
            discovery_blockers = tuple(discovery.blockers)
    rec = recommend(args.intent, facts)
    if discovery_blockers:
        rec = replace(
            rec,
            missing_prerequisites=rec.missing_prerequisites
            + tuple(f"official discovery: {item}" for item in discovery_blockers),
            blocked=True,
        )
    if args.as_json:
        print(json.dumps(_doctor_payload(facts, rec), indent=2, sort_keys=True))
    else:
        _print_doctor_text(_prog(args), facts, rec)
    if getattr(args, "write_advisory", False):
        try:
            written = write_advisory(root, facts, rec)
        except AdvisoryWriteError as refusal:
            print(f"{refusal}", file=sys.stderr)
            return 2
        print(f"advisory written: {written.as_posix()}")
    return 2 if rec.blocked or rec.missing_prerequisites else 0


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
    else:
        # Never let an uncontacted server read as verified success (#477).
        print(
            "  discovery: not-performed -- no read-only transport is wired "
            "into the shipped verb, so no capability was verified "
            "(capabilities_verified=false)"
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
