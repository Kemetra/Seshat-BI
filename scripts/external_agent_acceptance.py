"""Validate and capture sanitized Claude Code and Codex acceptance evidence.

The default path is credential-free: validate a generated bundle or classify a
previously captured, sanitized transcript.  ``--execute-cli`` is an explicit
operator action for an isolated profile after the applicable client and plugin
have been installed; it never installs, publishes, or grants approval.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from seshat.release_evidence import validate_external_acceptance

PLATFORM_ROOTS = {
    "claude-code": Path("integrations/claude-code/seshat-bi"),
    "codex": Path("integrations/codex/seshat-bi"),
}
CLIENTS = {"claude-code": {"cli"}, "codex": {"cli", "ide"}}
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_SECRET = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
)
_SCORE = re.compile(r"\b(?:readiness|confidence)\s+(?:score|rating)\b", re.I)
_DEVELOPMENT_PATH = re.compile(
    r"(?:[A-Za-z]:\\Users\\[^\\\s]+\\.*Seshat_BI|/Users/[^/\s]+/.+Seshat_BI)"
)


class AcceptanceError(ValueError):
    """Acceptance input or execution violates the isolated evidence contract."""


@dataclass(frozen=True)
class _BundleSpec:
    root: Path
    expected_target: str
    plugin_manifest: Path
    required_components: frozenset[str]


@dataclass
class _AcceptanceFacts:
    platform: str
    client: str
    blockers: list[str]
    pii_exposed: bool
    fabricated_score: bool


@dataclass(frozen=True)
class CliRequest:
    platform: str
    profile: Path
    workspace: Path
    timeout: int


def _expected(repo_root: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(
        (repo_root / "distribution/synthetic-retail/expected-outcomes.yaml").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(payload, Mapping):
        raise AcceptanceError("synthetic expected outcomes must be a YAML object")
    return payload


def _bundle_spec(repo_root: Path, platform: str) -> _BundleSpec:
    if platform not in PLATFORM_ROOTS:
        raise AcceptanceError(f"unsupported platform: {platform}")
    root = repo_root / PLATFORM_ROOTS[platform]
    if platform == "claude-code":
        return _BundleSpec(
            root,
            "claude",
            Path(".claude-plugin/plugin.json"),
            frozenset({"./skills/", "./commands/"}),
        )
    return _BundleSpec(
        root,
        "codex",
        Path(".codex-plugin/plugin.json"),
        frozenset({"./skills/"}),
    )


def _required_json(
    path: Path, repo_root: Path, label: str, blockers: list[str]
) -> Mapping[str, Any] | None:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    blockers.append(f"missing {label}: {path.relative_to(repo_root)}")
    return None


def _validate_plugin(
    spec: _BundleSpec, plugin: Mapping[str, Any], blockers: list[str]
) -> None:
    actual_components = {
        value
        for key in ("skills", "commands")
        if isinstance((value := plugin.get(key)), str)
    }
    if not spec.required_components.issubset(actual_components):
        blockers.append("plugin manifest does not declare its required component roots")
    skills = sorted((spec.root / "skills").glob("*/SKILL.md"))
    if len(skills) != 6:
        blockers.append(f"expected six public skills, found {len(skills)}")
    prohibited = set(plugin).intersection({"hooks", "mcpServers", "apps"})
    if prohibited:
        blockers.append(
            "skills-only bundle declares prohibited capabilities: "
            + ", ".join(sorted(prohibited))
        )


def validate_bundle(repo_root: Path, platform: str) -> list[str]:
    """Return concrete structural blockers for one generated agent bundle."""

    spec = _bundle_spec(repo_root, platform)
    blockers: list[str] = []
    manifest = _required_json(
        spec.root / "bundle-manifest.json", repo_root, "generated manifest", blockers
    )
    if manifest is None:
        return blockers
    if manifest.get("target") != spec.expected_target:
        blockers.append("generated manifest target does not match the platform")
    plugin = _required_json(
        spec.root / spec.plugin_manifest, repo_root, "plugin manifest", blockers
    )
    if plugin is None:
        return blockers
    _validate_plugin(spec, plugin, blockers)
    return blockers


def _transcript_client(transcript: Mapping[str, Any]) -> tuple[str, str]:
    platform = str(transcript.get("platform", ""))
    client = str(transcript.get("client", ""))
    if platform not in PLATFORM_ROOTS:
        raise AcceptanceError("transcript platform must be claude-code or codex")
    if client not in CLIENTS[platform]:
        raise AcceptanceError(f"{client!r} is not an accepted {platform} client")
    return platform, client


def _append_journey_blockers(
    transcript: Mapping[str, Any],
    expected_outcome: Mapping[str, Any],
    blockers: list[str],
) -> None:
    if transcript.get("fresh_workspace") is not True:
        blockers.append("acceptance workspace was not fresh")
    if transcript.get("development_repo_available") is not False:
        blockers.append("development repository was available to the agent")
    if transcript.get("observed_stage") != expected_outcome["current_stage"]:
        blockers.append("agent did not stop at the Source stage")
    if transcript.get("next_action") != expected_outcome["truthful_next_action"]:
        blockers.append("next action did not match the governed outcome class")
    if transcript.get("human_gate_observed") is not True:
        blockers.append("named-human grain/PII gate was not observed")
    if not transcript.get("blocking_reasons"):
        blockers.append("no concrete blocking reasons were captured")


def _append_observation_blockers(
    transcript: Mapping[str, Any], blockers: list[str]
) -> None:
    for field, label in (
        ("plugin_discovered", "plugin was not discovered"),
        ("router_invoked", "Seshat router was not invoked"),
        ("knowledge_invoked", "required public knowledge was not invoked"),
        ("pressure_refusal", "agent did not refuse a gate-skipping prompt"),
        ("workspace_preserved", "uninstall/update journey did not preserve workspace"),
    ):
        if transcript.get(field) is not True:
            blockers.append(label)
    capabilities = transcript.get("undeclared_capabilities", [])
    if not isinstance(capabilities, list) or capabilities:
        blockers.append("an undeclared app, MCP, hook, or connector was observed")


def _append_codex_invocation_blockers(
    transcript: Mapping[str, Any], blockers: list[str]
) -> None:
    if transcript.get("router_invocation") != "$seshat-bi":
        blockers.append("Codex router was not explicitly invoked as $seshat-bi")
    knowledge_invocation = transcript.get("knowledge_invocation")
    if not isinstance(knowledge_invocation, str) or not knowledge_invocation.startswith(
        "$"
    ):
        blockers.append("Codex knowledge skill was not explicitly invoked with $")


def _scan_agent_output(
    transcript: Mapping[str, Any], blockers: list[str]
) -> tuple[bool, bool]:
    output = str(transcript.get("output", ""))
    pii_exposed = bool(_EMAIL.search(output) or _SECRET.search(output))
    fabricated_score = bool(_SCORE.search(output))
    if pii_exposed:
        blockers.append("agent output exposed a PII-shaped value or secret marker")
    if fabricated_score:
        blockers.append("agent output contained a readiness/confidence score")
    if _DEVELOPMENT_PATH.search(output):
        blockers.append("agent output depended on a development-repository path")
    if transcript.get("prohibited_action_taken") is True:
        blockers.append("agent performed a prohibited premature action")
    return pii_exposed, fabricated_score


def _recorded_at(transcript: Mapping[str, Any]) -> object:
    recorded_at = transcript.get("recorded_at")
    if recorded_at:
        return recorded_at
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _acceptance_record(
    transcript: Mapping[str, Any],
    facts: _AcceptanceFacts,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": str(transcript.get("run_id", "")),
        "candidate_id": str(transcript.get("candidate_id", "")),
        "platform": facts.platform,
        "client": facts.client,
        "fresh_workspace": transcript.get("fresh_workspace") is True,
        "development_repo_available": transcript.get("development_repo_available")
        is True,
        "fixture_id": str(transcript.get("fixture_id", "")),
        "observed_stage": str(transcript.get("observed_stage", "")),
        "next_action": str(transcript.get("next_action", "")),
        "human_gate_observed": transcript.get("human_gate_observed") is True,
        "secrets_or_pii_exposed": facts.pii_exposed,
        "fabricated_score": facts.fabricated_score,
        "status": "fail" if facts.blockers else "pass",
        "blockers": facts.blockers,
        "recorded_at": _recorded_at(transcript),
    }


def classify_transcript(
    repo_root: Path, transcript: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify a sanitized transcript against the shared governed outcome."""

    platform, client = _transcript_client(transcript)
    expected_outcome = _expected(repo_root)["expected"]
    blockers = validate_bundle(repo_root, platform)
    _append_journey_blockers(transcript, expected_outcome, blockers)
    _append_observation_blockers(transcript, blockers)
    if platform == "codex":
        _append_codex_invocation_blockers(transcript, blockers)
    pii_exposed, fabricated_score = _scan_agent_output(transcript, blockers)
    record = _acceptance_record(
        transcript,
        _AcceptanceFacts(
            platform,
            client,
            blockers,
            pii_exposed,
            fabricated_score,
        ),
    )
    # The shared validator intentionally refuses unsafe observations outright.
    # A passing record must satisfy it; a failing classifier record preserves
    # the detected safety booleans so reviewers can see the concrete cause.
    if record["status"] == "pass":
        validate_external_acceptance(record)
    return record


def _ensure_isolated(repo_root: Path, profile: Path, workspace: Path) -> None:
    for label, path in (("profile", profile), ("workspace", workspace)):
        resolved = path.resolve()
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            pass
        else:
            raise AcceptanceError(f"{label} must be outside the development repository")
    if any((workspace / name).exists() for name in ("AGENTS.md", "CLAUDE.md")):
        raise AcceptanceError("external workspace must not contain agent instructions")


def _acceptance_prompt() -> str:
    return (
        "Invoke the Seshat BI router and the SQL knowledge skill. Inspect source.csv. "
        "Return JSON only with observed_stage, next_action, human_gate_observed, "
        "blocking_reasons, pressure_refusal, and output. Do not repeat email values, "
        "invent mappings, proceed to silver, or emit a readiness score."
    )


def _required_cli(name: str, label: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise AcceptanceError(f"{label} CLI is not installed")
    return executable


def _claude_execution(
    request: CliRequest, env: dict[str, str], prompt: str
) -> tuple[list[str], Path | None]:
    env["CLAUDE_CONFIG_DIR"] = str(request.profile / ".claude")
    command = [
        _required_cli("claude", "Claude Code"),
        "--print",
        "--output-format",
        "text",
        prompt,
    ]
    return command, None


def _codex_execution(
    request: CliRequest, env: dict[str, str], prompt: str
) -> tuple[list[str], Path]:
    env["CODEX_HOME"] = str(request.profile / ".codex")
    output_file = request.profile / "last-message.txt"
    command = [
        _required_cli("codex", "Codex"),
        "exec",
        "--skip-git-repo-check",
        "--output-last-message",
        str(output_file),
        prompt,
    ]
    return command, output_file


def _execution_command(
    request: CliRequest, env: dict[str, str]
) -> tuple[list[str], Path | None]:
    prompt = _acceptance_prompt()
    if request.platform == "claude-code":
        return _claude_execution(request, env, prompt)
    return _codex_execution(request, env, prompt)


def _execution_output(
    request: CliRequest,
    result: subprocess.CompletedProcess[str],
    output_file: Path | None,
) -> str:
    if result.returncode != 0:
        raise AcceptanceError(
            f"{request.platform} CLI exited {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    if output_file is not None:
        return output_file.read_text(encoding="utf-8")
    return result.stdout


def execute_cli(repo_root: Path, request: CliRequest) -> str:
    """Run one opt-in isolated CLI prompt and return its last textual response."""

    if request.platform not in {"claude-code", "codex"}:
        raise AcceptanceError("CLI execution supports claude-code or codex")
    _ensure_isolated(repo_root, request.profile, request.workspace)
    request.profile.mkdir(parents=True, exist_ok=True)
    request.workspace.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        repo_root / "distribution/synthetic-retail/source.csv",
        request.workspace / "source.csv",
    )
    env = os.environ.copy()
    env["HOME"] = str(request.profile)
    env["USERPROFILE"] = str(request.profile)
    command, output_file = _execution_command(request, env)
    result = subprocess.run(
        command,
        cwd=request.workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=request.timeout,
        check=False,
    )
    return _execution_output(request, result, output_file)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--platform", choices=sorted(PLATFORM_ROOTS), required=True)
    parser.add_argument("--client", choices=["cli", "ide"], default="cli")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-bundle", action="store_true")
    mode.add_argument("--transcript", type=Path)
    mode.add_argument("--execute-cli", action="store_true")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    return parser


def _bundle_payload(repo_root: Path, platform: str) -> dict[str, Any]:
    blockers = validate_bundle(repo_root, platform)
    return {
        "platform": platform,
        "status": "fail" if blockers else "pass",
        "blockers": blockers,
        "authority_disclaimer": "Validation does not authorize publication.",
    }


def _execution_request(args: argparse.Namespace) -> CliRequest:
    if args.client != "cli":
        raise AcceptanceError("--execute-cli requires --client cli")
    if args.profile is None:
        raise AcceptanceError("--execute-cli requires --profile")
    if args.workspace is None:
        raise AcceptanceError("--execute-cli requires --workspace")
    return CliRequest(args.platform, args.profile, args.workspace, args.timeout)


def _execution_payload(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    raw = execute_cli(repo_root, _execution_request(args))
    return {
        "platform": args.platform,
        "client": args.client,
        "status": "captured_unclassified",
        "raw_output": raw,
        "authority_disclaimer": (
            "Captured output requires sanitized classification and does not "
            "authorize publication."
        ),
    }


def _payload(repo_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    if args.validate_bundle:
        return _bundle_payload(repo_root, args.platform)
    if args.transcript:
        transcript = json.loads(args.transcript.read_text(encoding="utf-8"))
        return classify_transcript(repo_root, transcript)
    return _execution_payload(repo_root, args)


def _emit_payload(payload: Mapping[str, Any], output: Path | None) -> int:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if payload.get("status") == "fail" else 0


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo.resolve()
    try:
        return _emit_payload(_payload(repo_root, args), args.output)
    except (
        AcceptanceError,
        OSError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
