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


def _official_discovery(root: Path, facts, harness: str | None):
    from seshat.integrations.catalog import component
    from seshat.integrations.discovery import inspect_locked_component

    if not harness:
        return facts, ()
    discovery = inspect_locked_component(root, "fabric-skills", harness)
    if discovery.discoverable is not True:
        return facts, tuple(discovery.blockers)
    activation = next(
        entry
        for entry in component("fabric-skills").skill_activations
        if entry.harness == harness
    )
    report_skills = tuple(
        target.name
        for target in activation.targets
        if target.name.startswith("powerbi-report-")
    )
    return replace(facts, official_report_skills=report_skills), ()


def _doctor_recommendation(args, root: Path):
    from seshat.pbi_mcp.detect import detect_facts
    from seshat.pbi_mcp.recommend import recommend

    facts = detect_facts(root, target=args.target)
    facts, discovery_blockers = _official_discovery(
        root, facts, getattr(args, "harness", None)
    )
    rec = recommend(args.intent, facts)
    return facts, _with_discovery_blockers(rec, discovery_blockers)


def _with_discovery_blockers(rec, blockers: tuple[str, ...]):
    if not blockers:
        return rec
    prerequisites = tuple(f"official discovery: {item}" for item in blockers)
    return replace(
        rec,
        missing_prerequisites=rec.missing_prerequisites + prerequisites,
        blocked=True,
    )


def _render_doctor(args, facts, rec) -> None:
    if args.as_json:
        print(json.dumps(_doctor_payload(facts, rec), indent=2, sort_keys=True))
    else:
        _print_doctor_text(_prog(args), facts, rec)


def _write_doctor_advisory(root: Path, facts, rec) -> bool:
    from seshat.pbi_mcp.recommend import AdvisoryWriteError, write_advisory

    try:
        written = write_advisory(root, facts, rec)
    except AdvisoryWriteError as refusal:
        print(f"{refusal}", file=sys.stderr)
        return False
    print(f"advisory written: {written.as_posix()}")
    return True


def _run_doctor(args) -> int:
    root = Path(args.repo)
    facts, rec = _doctor_recommendation(args, root)
    _render_doctor(args, facts, rec)
    if getattr(args, "write_advisory", False) and not _write_doctor_advisory(
        root, facts, rec
    ):
        return 2
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


def _utc_stamp() -> str:
    """The run timestamp. Isolated so tests can pin it."""
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _probe_tree_clean(repo_root: Path) -> bool | None:
    """Whether the working tree is clean, or None when it could not be probed.

    None -- not True -- on any failure: an unprobeable git state must refuse
    rather than pass the git-safety precondition by omission.

    The adapter's OWN evidence artifact is excluded. Every run writes it, so
    counting it would make ``plan-write`` dirty the tree it then reports as
    clean: a second invocation would be refused for git-safety and the operator
    pushed toward ``--backup-ref`` on a self-inflicted dirty state. Excluding it
    here rather than relying on ``.gitignore`` is deliberate -- a user's own
    project will not carry this repo's ignore rules.
    """
    from seshat.gitstate import run_git
    from seshat.pbi_mcp_adapter.evidence import ARTIFACT_RELPATH, HISTORY_RELPATH

    try:
        # `--untracked-files=all` is required: the default collapses untracked
        # files into their directory (`?? .seshat/`), so an exact-path exclusion
        # would never match and every run would read as dirty.
        status = run_git(repo_root, "status", "--porcelain", "--untracked-files=all")
    except (OSError, RuntimeError):
        return None
    if status.returncode != 0:
        return None
    # BOTH of the adapter's own artifacts (issue #657). Excluding only the
    # latest-run file made the append-only history read as a foreign untracked
    # file, so a second `plan-write` was refused for git-safety on a dirty state
    # this adapter created itself -- caught by
    # `test_plan_write_twice_still_sees_a_clean_tree`.
    ours = {
        ARTIFACT_RELPATH.replace("\\", "/"),
        HISTORY_RELPATH.replace("\\", "/"),
    }
    for line in status.stdout.splitlines():
        entry = line[3:].strip().strip('"').replace("\\", "/")
        if entry and entry not in ours:
            return False
    return True


def _write_leg_payload(report) -> dict[str, object]:
    """The ``--json`` body. Every string field goes through ``redact``."""
    from seshat.pbi_mcp_adapter.evidence import (
        ARTIFACT_RELPATH,
        AUTHORITY,
        redact,
        scrub_secret_shaped,
    )

    def clean(text: str) -> str:
        """Both layers, in order, on one string.

        ``redact`` derives DSN/URI components; ``scrub_secret_shaped`` covers what
        derive-then-replace cannot see -- tenant GUIDs, user paths, credential
        assignments. Applying only the first leaked an allowlisted target whose id
        is a workspace GUID straight to stdout (PR #667).
        """
        scrubbed, _ = scrub_secret_shaped(redact(text))
        return scrubbed

    return {
        # Every key `contracts/cli-contract.md` documents. `target` and `mode`
        # let a consumer associate the verdict with the governed run it came
        # from; `validation` shows what was actually verified (issue #662).
        "target": clean(report.target_id),
        "mode": report.mode,
        "authority": AUTHORITY,
        "validation": {
            "checks_run": [clean(c) for c in report.checks_run],
            "failed": [clean(f) for f in report.validation_failed],
        },
        "outcome": report.outcome,
        "exit_code": report.exit_code,
        "mutation_attempted": report.mutation_attempted,
        "blockers": [clean(b) for b in report.blockers],
        "rollback_guidance": [clean(line) for line in report.rollback_guidance],
        # The FIXED repo-relative path, never `evidence_path.as_posix()`: that is
        # absolute whenever `--repo` is, so it leaked the operator's home-directory
        # path (the shape `inspect_release_artifacts` calls a "user path") into
        # stdout and bypassed the output scanner, against the contract guarantee
        # that no output carries a user path (Codex review, PR #659).
        "evidence": (ARTIFACT_RELPATH if report.evidence_path is not None else None),
        # WHICH build ran. `npx` resolves a floating tag, so a verdict that does
        # not name the runtime cannot be reproduced (issue #658). None, never a
        # placeholder: a run that never handshook measured nothing.
        "runtime_version": (
            clean(report.runtime_version)
            if getattr(report, "runtime_version", None)
            else None
        ),
    }


def _report_write_leg(args, report) -> int:
    """Print one write leg's outcome and return its exit code.

    Split from :func:`_run_write_leg` so the guard-and-invoke half stays free of
    presentation branching. This function decides nothing: the exit code comes
    from the report it was handed.
    """
    from seshat.pbi_mcp_adapter.evidence import (
        ARTIFACT_RELPATH,
        redact,
        scrub_secret_shaped,
    )

    def clean(text: str) -> str:
        """Both redaction layers -- see :func:`_write_leg_payload`."""
        scrubbed, _ = scrub_secret_shaped(redact(text))
        return scrubbed

    if getattr(args, "as_json", False):
        print(json.dumps(_write_leg_payload(report), indent=2, sort_keys=True))
        return report.exit_code

    prog = _prog(args)
    print(
        f"{prog}: [{report.outcome}] "
        f"target={clean(str(args.target))} op={clean(str(args.operation))}"
    )
    for blocker in report.blockers:
        print(f"{prog}:   blocker {clean(blocker)}", file=sys.stderr)
    if report.rollback_guidance:
        print(f"{prog}: rollback:", file=sys.stderr)
        for line in report.rollback_guidance:
            print(f"{prog}:   {clean(line)}", file=sys.stderr)
    if report.evidence_path is not None:
        # Repo-relative here too -- the human line leaked the same absolute path.
        print(f"{prog}: evidence {ARTIFACT_RELPATH}")
    return report.exit_code


def _run_write_leg(args, *, dry_run: bool) -> int:
    """Shared body for ``plan-write`` and ``apply``.

    One implementation, so the dry run cannot drift from the real thing.
    """
    from seshat.pbi_mcp.detect import BypassFlagRefused, classify_mcp_config
    from seshat.pbi_mcp.scan import GeneratedSecretError
    from seshat.pbi_mcp_adapter import orchestrate

    repo_root = Path(args.repo)
    # The config half of the bypass guard was dead on this path: orchestrate
    # accepted config_state but nothing supplied it, so a machine-local .mcp.json
    # carrying --skipconfirmation was never detected on a write. The verdict is
    # already computed for the read-only legs; wire it in rather than trust argv
    # alone (FR-002 covers BOTH arrival routes).
    config_state = classify_mcp_config(repo_root / ".mcp.json")
    try:
        report = orchestrate.apply_write(
            repo_root,
            target_id=args.target,
            operation_id=args.operation,
            timestamp=_utc_stamp(),
            tree_clean=_probe_tree_clean(repo_root),
            backup_ref=getattr(args, "backup_ref", None),
            argv=tuple(sys.argv[1:]),
            config_state=config_state,
            dry_run=dry_run,
        )
    except BypassFlagRefused as refusal:
        print(f"{_prog(args)}: {refusal}", file=sys.stderr)
        return 1
    except GeneratedSecretError as refusal:
        print(f"{_prog(args)}: refused -- {refusal}", file=sys.stderr)
        return 1

    return _report_write_leg(args, report)


def _run_plan_write(args) -> int:
    return _run_write_leg(args, dry_run=True)


def _run_apply(args) -> int:
    return _run_write_leg(args, dry_run=False)


def pbi_mcp_main(args) -> int:
    handlers = {
        "doctor": _run_doctor,
        "generate-config": _run_generate_config,
        "preflight": _run_preflight,
        "plan-write": _run_plan_write,
        "apply": _run_apply,
    }
    handler = handlers.get(getattr(args, "pbi_mcp_cmd", None))
    if handler is None:
        return 1
    return handler(args)
