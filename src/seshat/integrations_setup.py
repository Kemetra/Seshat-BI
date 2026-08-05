"""Opt-in installer and validator for Fabric, Power BI, dbt, and Dagster.

Nothing here acts without explicit human approval: `setup_integrations` defaults
to a **network-free plan**, and only `apply=True` -- reached via `--apply`,
`--yes`, or an interactive "yes" -- clones, writes, or provisions anything.

Two boundaries are deliberate:

* **The ambient interpreter is never modified.** A missing `dbt` is reported with
  the versions to install; Seshat does not `pip install` over whatever
  environment the operator happened to activate.
* **The workspace root is resolved, never assumed.** The first-run offer takes a
  starting point and discovers the workspace upward from it, so a launch inside
  `warehouse/migrations/` still writes the one true `.seshat/integrations/`
  instead of seeding a second one where the client happened to start -- the same
  fail-closed posture `workspace_root` gives `seshat mcp`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from seshat.workspace_root import WorkspaceRootError, resolve_workspace_root

INTEGRATIONS_DIR = Path(".seshat/integrations")
MCP_CONFIG = INTEGRATIONS_DIR / "mcp.json"
AUTO_MARKER = INTEGRATIONS_DIR / ".auto-offered"
DAGSTER_PROJECT = Path("orchestration/dagster")

DBT_CORE_PIN = "dbt-core==1.12.0"
DBT_POSTGRES_PIN = "dbt-postgres==1.10.2"

# `failed` and `unavailable` both mean "a human has something to do"; `present`,
# `planned`, and `installed` do not. One definition, used by the summary line and
# the CLI exit code alike.
NEEDS_ACTION = frozenset({"failed", "unavailable"})


@dataclass(frozen=True)
class IntegrationResult:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class SkillBundle:
    """A third-party skill bundle installed by shallow-cloning its repository."""

    name: str
    repo: str
    directory: Path
    required: tuple[str, ...]


@dataclass(frozen=True)
class McpServer:
    """An MCP server registration written into the project MCP config."""

    name: str
    executable: str
    requirement: str
    entry: dict[str, object]


FABRIC_SKILLS = SkillBundle(
    name="fabric-skills",
    repo="https://github.com/microsoft/skills-for-fabric.git",
    directory=INTEGRATIONS_DIR / "skills-for-fabric",
    required=(
        "skills/semantic-model-consumption/SKILL.md",
        "skills/semantic-model-authoring/SKILL.md",
        "plugins/powerbi-authoring/skills/powerbi-report-authoring/SKILL.md",
    ),
)

DBT_SKILLS = SkillBundle(
    name="dbt-skills",
    repo="https://github.com/dbt-labs/dbt-agent-skills.git",
    directory=INTEGRATIONS_DIR / "dbt-agent-skills",
    required=(
        "skills/dbt/using-dbt-for-analytics-engineering/SKILL.md",
        "skills/dbt/configuring-dbt-mcp-server/SKILL.md",
    ),
)

POWERBI_MCP = McpServer(
    name="powerbi-modeling-mcp",
    executable="npx",
    requirement="Node.js/npx is not on PATH",
    entry={
        "type": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "@microsoft/powerbi-modeling-mcp@latest",
            "--start",
            "--readonly",
        ],
    },
)

DBT_MCP = McpServer(
    name="dbt-mcp",
    executable="uvx",
    requirement="uvx is not on PATH",
    entry={"type": "stdio", "command": "uvx", "args": ["dbt-mcp"]},
)


def _failed(name: str, detail: str) -> IntegrationResult:
    return IntegrationResult(name, "failed", detail)


def _process_detail(result: subprocess.CompletedProcess, fallback: str) -> str:
    return (result.stderr or result.stdout or "").strip() or fallback


# --------------------------------------------------------------------------- #
# Skill bundles
# --------------------------------------------------------------------------- #


def _absent(root: Path, bundle: SkillBundle) -> list[str]:
    """The bundle's required skills that are not on disk."""
    target = root / bundle.directory
    return [name for name in bundle.required if not (target / name).is_file()]


def _clone(root: Path, bundle: SkillBundle) -> IntegrationResult:
    target = root / bundle.directory
    if target.exists():
        return _failed(bundle.name, f"incomplete existing directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", bundle.repo, str(target)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return _failed(bundle.name, _process_detail(result, "git clone failed"))
    missing = _absent(root, bundle)
    if missing:
        return _failed(bundle.name, f"missing required skills: {', '.join(missing)}")
    return IntegrationResult(bundle.name, "installed", str(target))


def _skill_bundle(root: Path, bundle: SkillBundle, apply: bool) -> IntegrationResult:
    target = root / bundle.directory
    if not _absent(root, bundle):
        return IntegrationResult(bundle.name, "present", str(target))
    if not apply:
        planned = f"git clone {bundle.repo} {target}"
        return IntegrationResult(bundle.name, "planned", planned)
    if shutil.which("git") is None:
        return IntegrationResult(bundle.name, "unavailable", "git is not on PATH")
    return _clone(root, bundle)


# --------------------------------------------------------------------------- #
# MCP registrations
# --------------------------------------------------------------------------- #


def _load_mcp_config(path: Path) -> dict | None:
    """The existing config, an empty one when absent, or None when unreadable.

    None is the refusal signal: an unparseable config is never overwritten,
    because the operator's hand-edits are worth more than this registration.
    """
    if not path.exists():
        return {"mcpServers": {}}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return config if isinstance(config, dict) else None


def _register(path: Path, server: McpServer) -> IntegrationResult:
    config = _load_mcp_config(path)
    if config is None:
        return _failed(server.name, f"unparseable config: {path}")
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return _failed(server.name, "mcpServers must be an object")
    servers[server.name] = dict(server.entry)
    try:
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return _failed(server.name, str(exc))
    return IntegrationResult(server.name, "installed", str(path))


def _mcp_server(root: Path, server: McpServer, apply: bool) -> IntegrationResult:
    if shutil.which(server.executable) is None:
        return IntegrationResult(server.name, "unavailable", server.requirement)
    if not apply:
        planned = f"register {server.name} in {MCP_CONFIG.as_posix()}"
        return IntegrationResult(server.name, "planned", planned)
    config_path = root / MCP_CONFIG
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return _register(config_path, server)


# --------------------------------------------------------------------------- #
# Runtimes
# --------------------------------------------------------------------------- #


def _dbt_runtime() -> IntegrationResult:
    """Report a missing dbt; never install one.

    Installing into `sys.executable` would mutate whichever environment the
    operator activated, and hard-fails outright on a PEP 668 managed
    interpreter. The dbt MCP server reaches dbt through `uvx`, so nothing here
    needs a dbt on the ambient PATH -- reporting is enough.
    """
    if shutil.which("dbt"):
        return IntegrationResult(
            "dbt-runtime", "present", "dbt executable is available"
        )
    return IntegrationResult(
        "dbt-runtime",
        "unavailable",
        f"install {DBT_CORE_PIN} and {DBT_POSTGRES_PIN} into a dedicated "
        "environment; Seshat does not modify the active interpreter",
    )


def _dagster_skills(root: Path) -> IntegrationResult:
    skill = (
        root / "integrations/claude-code/seshat-bi/skills/dagster-workflows/SKILL.md"
    )
    if skill.is_file():
        return IntegrationResult("dagster-skills", "present", str(skill))
    return IntegrationResult(
        "dagster-skills", "unavailable", "bundled Dagster workflow skill is absent"
    )


def _dagster_interpreter(project: Path) -> Path:
    if sys.platform == "win32":
        return project / ".venv/Scripts/python.exe"
    return project / ".venv/bin/python"


def _provision_dagster(project: Path) -> IntegrationResult:
    """Build the project's own `.venv` -- isolated, never the ambient one."""
    for command in (
        ["uv", "venv", ".venv"],
        ["uv", "pip", "install", "-p", ".venv", "-e", "../..[dbt]", "-e", ".[dev]"],
    ):
        result = subprocess.run(
            command, cwd=project, text=True, capture_output=True, check=False
        )
        if result.returncode:
            detail = _process_detail(result, "Dagster installation failed")
            return _failed("dagster-runtime", detail)
    return IntegrationResult(
        "dagster-runtime", "installed", "Dagster orchestration environment"
    )


def _dagster_runtime(root: Path, apply: bool) -> IntegrationResult:
    project = root / DAGSTER_PROJECT
    if not (project / "pyproject.toml").is_file():
        absent = f"{DAGSTER_PROJECT.as_posix()}/pyproject.toml is absent"
        return IntegrationResult("dagster-runtime", "unavailable", absent)
    interpreter = _dagster_interpreter(project)
    if interpreter.is_file():
        return IntegrationResult("dagster-runtime", "present", str(interpreter))
    if not apply:
        planned = f"create {DAGSTER_PROJECT.as_posix()}/.venv and install Dagster"
        return IntegrationResult("dagster-runtime", "planned", planned)
    if shutil.which("uv") is None:
        return IntegrationResult("dagster-runtime", "unavailable", "uv is not on PATH")
    return _provision_dagster(project)


# --------------------------------------------------------------------------- #
# Composition and rendering
# --------------------------------------------------------------------------- #


def setup_integrations(root: Path, *, apply: bool = False) -> list[IntegrationResult]:
    root = Path(root).resolve()
    return [
        _skill_bundle(root, FABRIC_SKILLS, apply),
        _mcp_server(root, POWERBI_MCP, apply),
        _skill_bundle(root, DBT_SKILLS, apply),
        _mcp_server(root, DBT_MCP, apply),
        _dbt_runtime(),
        _dagster_skills(root),
        _dagster_runtime(root, apply),
    ]


def needs_operator_action(results: list[IntegrationResult]) -> bool:
    """Whether any integration needs a human -- the CLI's exit-code rule."""
    return any(item.status in NEEDS_ACTION for item in results)


def _summary(results: list[IntegrationResult]) -> str:
    if any(item.status == "planned" for item in results):
        return "Dry run only. Approve explicitly (--apply/--yes) to install."
    if needs_operator_action(results):
        return "Some integrations need operator action; no readiness stage is changed."
    return "Integration runtimes and configuration are present."


def render_results(results: list[IntegrationResult], *, as_json: bool = False) -> str:
    if as_json:
        return json.dumps([asdict(item) for item in results], indent=2, sort_keys=True)
    lines = ["seshat integration setup"]
    lines.extend(
        f"[{item.status.upper()}] {item.name}: {item.detail}" for item in results
    )
    lines.append(_summary(results))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The first-run offer
# --------------------------------------------------------------------------- #


def confirm(question: str) -> bool:
    """A yes/no prompt that reads every non-answer -- including EOF -- as "no"."""
    try:
        answer = input(question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"y", "yes"}


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _offer_target(start: Path) -> Path | None:
    """The workspace to offer for, or None when no offer should be made.

    Discovery decides, not the working directory: a start outside any workspace
    yields None rather than seeding `.seshat/integrations/` wherever the client
    happened to be launched.
    """
    if os.environ.get("SESHAT_NO_AUTO_INTEGRATIONS") == "1":
        return None
    if not _interactive():
        return None
    try:
        root = resolve_workspace_root(start=Path(start))
    except WorkspaceRootError:
        return None
    if (root / AUTO_MARKER).exists():
        return None
    return root


def _mark_offered(root: Path) -> None:
    """Record that the offer was made, so it is made once and never nags."""
    marker = root / AUTO_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("offered\n", encoding="utf-8")


def offer_first_run(start: Path) -> bool:
    """Offer integration setup once, on a workspace's first interactive launch."""
    root = _offer_target(start)
    if root is None:
        return False
    planned = setup_integrations(root, apply=False)
    if not any(item.status == "planned" for item in planned):
        return False
    print(render_results(planned))
    approved = confirm("Set up Fabric/Power BI/dbt/Dagster integrations now? [y/N]: ")
    _mark_offered(root)
    if not approved:
        print("Integration setup skipped; Seshat will continue normally.")
        return False
    results = setup_integrations(root, apply=True)
    print(render_results(results))
    return not needs_operator_action(results)
