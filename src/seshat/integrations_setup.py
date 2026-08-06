"""Opt-in installer and validator for the curated analytics stack.

This module is the FACADE. The curated-stack implementation lives in
`seshat.integrations` -- `catalog` (profiles and version channels), `versions`
(stable-release semantics), `resolvers` (injectable PyPI/GitHub/npm lookups),
`compat` (the cross-component policy), `lockfile`, `mcp_config`, `installer`,
and `render`. The split keeps each file reviewable; this facade keeps the
already-shipped import surface working.

Nothing here acts without explicit human approval. The default is a
**network-free, write-free plan**; remote resolution needs `--refresh`; and only
an explicit `--apply` clones, writes, or provisions anything. `--yes` confirms an
apply that was already requested -- it never turns one on.

Two boundaries are deliberate:

* **The ambient interpreter is never modified.** A missing `dbt` is reported with
  the versions to install; Seshat does not `pip install` over whatever
  environment the operator happened to activate.
* **Nothing is offered unprompted.** This module is reached only through the
  `seshat integrations setup` verb, never as a side effect of another command. A
  read-only governance verb must stay read-only, so an unrelated `seshat check`
  cannot end in a third-party clone. Wiring a first-arrival offer belongs to
  `first-hour-compass`, whose contract is first arrival.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from seshat.integrations import mcp_config
from seshat.integrations.catalog import (
    DAGSTER_PROJECT,
    DEFAULT_PROFILE,
    INTEGRATIONS_DIR,
    LOCK_FILE,
    MCP_CONFIG,
    PROFILE_NAMES,
    Channel,
    UnknownProfile,
    profile_components,
)
from seshat.integrations.installer import apply as apply_profile
from seshat.integrations.installer import plan as plan_profile
from seshat.integrations.render import as_json as render_json
from seshat.integrations.render import as_text as render_text
from seshat.integrations.resolvers import Resolvers, live_resolvers

__all__ = [
    "DAGSTER_PROJECT",
    "DBT_CORE_PIN",
    "DBT_POSTGRES_PIN",
    "DBT_SKILLS",
    "DEFAULT_PROFILE",
    "FABRIC_SKILLS",
    "INTEGRATIONS_DIR",
    "LOCK_FILE",
    "MCP_CONFIG",
    "PROFILE_NAMES",
    "Channel",
    "IntegrationResult",
    "McpServer",
    "Resolvers",
    "SkillBundle",
    "UnknownProfile",
    "apply_profile",
    "confirm",
    "live_resolvers",
    "needs_operator_action",
    "plan_profile",
    "profile_components",
    "render_json",
    "render_results",
    "render_text",
    "setup_integrations",
]

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

# The MCP entries carry an EXACT version, never `@latest` and never a bare
# `uvx dbt-mcp`. A moving reference in an active configuration silently changes
# meaning when upstream publishes, so the version-channel-aware path
# (`seshat integrations setup --refresh`) resolves the pin and these
# lock-recorded defaults are what a no-network run registers.
#
# `POWERBI_MCP_FALLBACK_VERSION` / `DBT_MCP_FALLBACK_VERSION` are the last
# coordinates this repository verified. They are a floor for the legacy
# no-profile path, not a claim about what is newest: `--refresh` is how a newer
# compatible release is discovered and pinned.
POWERBI_MCP_FALLBACK_VERSION = "1.3.4"
DBT_MCP_FALLBACK_VERSION = "1.5.1"

POWERBI_MCP = McpServer(
    name="powerbi-modeling-mcp",
    executable="npx",
    requirement="Node.js/npx is not on PATH",
    entry=mcp_config.powerbi_entry(POWERBI_MCP_FALLBACK_VERSION),
)

DBT_MCP = McpServer(
    name="dbt-mcp",
    executable="uvx",
    requirement="uvx is not on PATH",
    entry=mcp_config.dbt_entry(DBT_MCP_FALLBACK_VERSION),
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
# The approval prompt
# --------------------------------------------------------------------------- #


def confirm(question: str) -> bool:
    """A yes/no prompt that reads every non-answer -- including EOF -- as "no"."""
    try:
        answer = input(question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"y", "yes"}
