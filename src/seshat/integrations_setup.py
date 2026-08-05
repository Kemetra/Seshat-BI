"""Opt-in installer and validator for Fabric, Power BI, dbt, and Dagster.

Integrations are installed only after explicit human approval.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SKILLS_REPO = "https://github.com/microsoft/skills-for-fabric.git"
SKILLS_DIR = Path(".seshat/integrations/skills-for-fabric")
DBT_SKILLS_REPO = "https://github.com/dbt-labs/dbt-agent-skills.git"
DBT_SKILLS_DIR = Path(".seshat/integrations/dbt-agent-skills")
MCP_CONFIG = Path(".seshat/integrations/mcp.json")
AUTO_MARKER = Path(".seshat/integrations/.auto-offered")


@dataclass(frozen=True)
class IntegrationResult:
    name: str
    status: str
    detail: str


def _skills(root: Path, apply: bool) -> IntegrationResult:
    target = root / SKILLS_DIR
    required = (
        target / "skills/semantic-model-consumption/SKILL.md",
        target / "skills/semantic-model-authoring/SKILL.md",
        target / "plugins/powerbi-authoring/skills/powerbi-report-authoring/SKILL.md",
    )
    if all(path.is_file() for path in required):
        return IntegrationResult("fabric-skills", "present", str(target))
    if not apply:
        return IntegrationResult(
            "fabric-skills", "planned", f"git clone {SKILLS_REPO} {target}"
        )
    if shutil.which("git") is None:
        return IntegrationResult("fabric-skills", "unavailable", "git is not on PATH")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return IntegrationResult(
            "fabric-skills", "failed", f"incomplete existing directory: {target}"
        )
    result = subprocess.run(
        ["git", "clone", "--depth", "1", SKILLS_REPO, str(target)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return IntegrationResult(
            "fabric-skills",
            "failed",
            (result.stderr or result.stdout).strip() or "git clone failed",
        )
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    return IntegrationResult(
        "fabric-skills",
        "installed" if not missing else "failed",
        str(target)
        if not missing
        else f"missing required skills: {', '.join(missing)}",
    )


def _powerbi_mcp(root: Path, apply: bool) -> IntegrationResult:
    if shutil.which("npx") is None:
        return IntegrationResult(
            "powerbi-modeling-mcp", "unavailable", "Node.js/npx is not on PATH"
        )
    if not apply:
        return IntegrationResult(
            "powerbi-modeling-mcp",
            "planned",
            "register @microsoft/powerbi-modeling-mcp in project MCP config",
        )
    config_path = root / MCP_CONFIG
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return IntegrationResult(
                "powerbi-modeling-mcp", "failed", f"unparseable config: {config_path}"
            )
    else:
        config = {"mcpServers": {}}
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return IntegrationResult(
            "powerbi-modeling-mcp", "failed", "mcpServers must be an object"
        )
    servers["powerbi-modeling-mcp"] = {
        "type": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "@microsoft/powerbi-modeling-mcp@latest",
            "--start",
            "--readonly",
        ],
    }
    try:
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return IntegrationResult("powerbi-modeling-mcp", "failed", str(exc))
    return IntegrationResult("powerbi-modeling-mcp", "installed", str(config_path))


def _dbt_skills(root: Path, apply: bool) -> IntegrationResult:
    target = root / DBT_SKILLS_DIR
    required = (
        target / "skills/dbt/using-dbt-for-analytics-engineering/SKILL.md",
        target / "skills/dbt/configuring-dbt-mcp-server/SKILL.md",
    )
    if all(path.is_file() for path in required):
        return IntegrationResult("dbt-skills", "present", str(target))
    if not apply:
        return IntegrationResult(
            "dbt-skills", "planned", f"git clone {DBT_SKILLS_REPO} {target}"
        )
    if shutil.which("git") is None:
        return IntegrationResult("dbt-skills", "unavailable", "git is not on PATH")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return IntegrationResult(
            "dbt-skills", "failed", f"incomplete existing directory: {target}"
        )
    result = subprocess.run(
        ["git", "clone", "--depth", "1", DBT_SKILLS_REPO, str(target)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return IntegrationResult(
            "dbt-skills",
            "failed",
            (result.stderr or result.stdout).strip() or "git clone failed",
        )
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    return IntegrationResult(
        "dbt-skills",
        "installed" if not missing else "failed",
        str(target)
        if not missing
        else f"missing required skills: {', '.join(missing)}",
    )


def _dbt_mcp(root: Path, apply: bool) -> IntegrationResult:
    if shutil.which("uvx") is None:
        return IntegrationResult("dbt-mcp", "unavailable", "uvx is not on PATH")
    if not apply:
        return IntegrationResult(
            "dbt-mcp",
            "planned",
            "register dbt-labs/dbt-mcp via uvx in project MCP config",
        )
    config_path = root / MCP_CONFIG
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        config = (
            json.loads(config_path.read_text(encoding="utf-8"))
            if config_path.exists()
            else {"mcpServers": {}}
        )
    except (OSError, ValueError):
        return IntegrationResult(
            "dbt-mcp", "failed", f"unparseable config: {config_path}"
        )
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return IntegrationResult("dbt-mcp", "failed", "mcpServers must be an object")
    servers["dbt-mcp"] = {"type": "stdio", "command": "uvx", "args": ["dbt-mcp"]}
    try:
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return IntegrationResult("dbt-mcp", "failed", str(exc))
    return IntegrationResult("dbt-mcp", "installed", str(config_path))


def _dbt_runtime(root: Path, apply: bool) -> IntegrationResult:
    if shutil.which("dbt"):
        return IntegrationResult(
            "dbt-runtime", "present", "dbt executable is available"
        )
    if not apply:
        return IntegrationResult(
            "dbt-runtime",
            "planned",
            "install pinned dbt-core 1.12.0 and dbt-postgres 1.10.2",
        )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "dbt-core==1.12.0",
            "dbt-postgres==1.10.2",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return IntegrationResult(
            "dbt-runtime",
            "failed",
            (result.stderr or result.stdout).strip() or "dbt installation failed",
        )
    return IntegrationResult(
        "dbt-runtime", "installed", "dbt-core 1.12.0 and dbt-postgres 1.10.2"
    )


def _dagster_skills(root: Path, apply: bool) -> IntegrationResult:
    skill = (
        root / "integrations/claude-code/seshat-bi/skills/dagster-workflows/SKILL.md"
    )
    if skill.is_file():
        return IntegrationResult("dagster-skills", "present", str(skill))
    return IntegrationResult(
        "dagster-skills", "unavailable", "bundled Dagster workflow skill is absent"
    )


def _dagster_runtime(root: Path, apply: bool) -> IntegrationResult:
    project = root / "orchestration" / "dagster"
    if not (project / "pyproject.toml").is_file():
        return IntegrationResult(
            "dagster-runtime",
            "unavailable",
            "orchestration/dagster/pyproject.toml is absent",
        )
    interpreter = project / (
        ".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python"
    )
    if interpreter.is_file():
        return IntegrationResult("dagster-runtime", "present", str(interpreter))
    if not apply:
        return IntegrationResult(
            "dagster-runtime",
            "planned",
            "create orchestration/dagster/.venv and install pinned Dagster",
        )
    if shutil.which("uv") is None:
        return IntegrationResult("dagster-runtime", "unavailable", "uv is not on PATH")
    for command in (
        ["uv", "venv", ".venv"],
        ["uv", "pip", "install", "-p", ".venv", "-e", "../..[dbt]", "-e", ".[dev]"],
    ):
        result = subprocess.run(
            command, cwd=project, text=True, capture_output=True, check=False
        )
        if result.returncode:
            return IntegrationResult(
                "dagster-runtime",
                "failed",
                (result.stderr or result.stdout).strip()
                or "Dagster installation failed",
            )
    return IntegrationResult(
        "dagster-runtime", "installed", "Dagster 1.13.15 orchestration environment"
    )


def setup_integrations(root: Path, *, apply: bool = False) -> list[IntegrationResult]:
    root = Path(root).resolve()
    return [
        _skills(root, apply),
        _powerbi_mcp(root, apply),
        _dbt_skills(root, apply),
        _dbt_mcp(root, apply),
        _dbt_runtime(root, apply),
        _dagster_skills(root, apply),
        _dagster_runtime(root, apply),
    ]


def render_results(results: list[IntegrationResult], *, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(
            [asdict(result) for result in results], indent=2, sort_keys=True
        )
    lines = ["seshat integration setup"]
    lines.extend(
        f"[{item.status.upper()}] {item.name}: {item.detail}" for item in results
    )
    if any(item.status == "planned" for item in results):
        lines.append(
            "Dry run only. Re-run the client or use explicit approval to install."
        )
    elif any(item.status in {"failed", "unavailable"} for item in results):
        lines.append(
            "Some integrations need operator action; no readiness stage is changed."
        )
    else:
        lines.append("Integration runtimes and configuration are present.")
    return "\n".join(lines)


def offer_first_run(root: Path) -> bool:
    """Offer integration setup transparently on the first interactive launch."""
    import os

    if os.environ.get("SESHAT_NO_AUTO_INTEGRATIONS") == "1":
        return False
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    root = Path(root).resolve()
    marker = root / AUTO_MARKER
    if marker.exists():
        return False
    planned = setup_integrations(root, apply=False)
    if not any(item.status == "planned" for item in planned):
        return False
    print(render_results(planned))
    try:
        answer = (
            input("Set up Fabric/Power BI/dbt/Dagster integrations now? [y/N]: ")
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        answer = ""
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("offered\n", encoding="utf-8")
    if answer not in {"y", "yes"}:
        print("Integration setup skipped; Seshat will continue normally.")
        return False
    results = setup_integrations(root, apply=True)
    print(render_results(results))
    return not any(item.status in {"failed", "unavailable"} for item in results)
