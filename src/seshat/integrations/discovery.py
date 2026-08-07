"""Read-only discovery proof for official Agent Skills packages.

Installation, activation, and discovery are deliberately separate facts. The
catalog owns the expected identities; this module only observes a requested
harness. It never installs a plugin, writes a projection, or mutates a user's
Claude/Codex configuration.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from seshat.integrations.catalog import (
    CLAUDE_CODE,
    CODEX,
    SKILLS_DIR,
    Component,
    SkillActivation,
)

NOT_CHECKED = "not-checked"
NOT_INSTALLED = "not-installed"
ACTIVATION_REQUIRED = "activation-required"
DISCOVERABLE = "discoverable"
CONFLICT = "conflict"
FAILED = "failed"

Runner = Callable[[list[str], Path], subprocess.CompletedProcess]
ToolLookup = Callable[[str], str | None]


@dataclass(frozen=True)
class SkillDiscovery:
    """One package/harness discovery verdict with its observable evidence."""

    component: str
    harness: str
    mechanism: str
    checked: bool
    installed: bool
    activated: bool | None
    discoverable: bool | None
    status: str
    evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    next_action: str

    @property
    def needs_action(self) -> bool:
        return self.checked and self.discoverable is not True


def inspect_official_skills(
    root: Path,
    components: Iterable[Component],
    *,
    installed: Mapping[str, bool],
    harnesses: Iterable[str] = (),
    runner: Runner | None = None,
    harness_roots: Mapping[str, Path] | None = None,
    tool_lookup: ToolLookup | None = None,
) -> list[SkillDiscovery]:
    """Classify catalog-declared official skills for requested harnesses.

    An omitted harness produces an explicit ``not-checked`` record. Requesting
    Claude Code executes only ``claude plugin list --json``. Requesting Codex
    reads its skill directory. Neither path writes anything.
    """

    root = Path(root).resolve()
    requested = frozenset(harnesses)
    harness_roots = harness_roots or {}
    runner = runner or _run
    tool_lookup = tool_lookup or shutil.which

    claude_plugins: dict[str, dict] | None = None
    claude_error: str | None = None
    if CLAUDE_CODE in requested:
        claude_plugins, claude_error = _claude_inventory(root, runner, tool_lookup)

    results: list[SkillDiscovery] = []
    for item in components:
        for activation in item.skill_activations:
            is_installed = bool(installed.get(item.id, False))
            if activation.harness not in requested:
                results.append(_not_checked(item, activation, is_installed))
                continue
            if not is_installed:
                results.append(_not_installed(item, activation))
                continue
            if activation.harness == CLAUDE_CODE:
                results.append(
                    _inspect_claude(
                        item,
                        activation,
                        claude_plugins or {},
                        claude_error,
                    )
                )
                continue
            results.append(
                _inspect_codex(
                    root,
                    item,
                    activation,
                    harness_roots.get(CODEX, _codex_skills_root()),
                )
            )
    return results


def _not_checked(
    item: Component, activation: SkillActivation, installed: bool
) -> SkillDiscovery:
    return SkillDiscovery(
        component=item.id,
        harness=activation.harness,
        mechanism=activation.mechanism,
        checked=False,
        installed=installed,
        activated=None,
        discoverable=None,
        status=NOT_CHECKED,
        evidence=(f"installed={str(installed).lower()}",),
        blockers=(),
        next_action=(
            "rerun the read-only plan with "
            f"--harness {activation.harness} to verify discovery"
        ),
    )


def _not_installed(item: Component, activation: SkillActivation) -> SkillDiscovery:
    return SkillDiscovery(
        component=item.id,
        harness=activation.harness,
        mechanism=activation.mechanism,
        checked=True,
        installed=False,
        activated=False,
        discoverable=False,
        status=NOT_INSTALLED,
        evidence=(),
        blockers=("the exact catalog payload is not installed",),
        next_action=(
            "approve seshat integrations setup --refresh --apply before "
            "activating this package"
        ),
    )


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - fixed read-only argv, no shell
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _claude_inventory(
    root: Path, runner: Runner, tool_lookup: ToolLookup
) -> tuple[dict[str, dict] | None, str | None]:
    if tool_lookup("claude") is None:
        return None, "Claude Code is not on PATH"
    result = runner(["claude", "plugin", "list", "--json"], root)
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        return None, detail or "Claude Code plugin inventory failed"
    try:
        body = json.loads(result.stdout or "")
    except ValueError:
        return None, "Claude Code plugin inventory was not valid JSON"
    if not isinstance(body, list):
        return None, "Claude Code plugin inventory was not a list"
    plugins = {
        entry["id"]: entry
        for entry in body
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    return plugins, None


def _inspect_claude(
    item: Component,
    activation: SkillActivation,
    plugins: Mapping[str, dict],
    inventory_error: str | None,
) -> SkillDiscovery:
    if inventory_error is not None:
        return _blocked(
            item,
            activation,
            status=FAILED,
            blockers=(inventory_error,),
        )

    evidence: list[str] = []
    blockers: list[str] = []
    plugin_entries: dict[str, dict] = {}
    for plugin_id in dict.fromkeys(
        target.plugin_id for target in activation.targets if target.plugin_id
    ):
        entry = plugins.get(plugin_id)
        if entry is None:
            blockers.append(f"Claude plugin {plugin_id!r} is not installed")
            continue
        plugin_entries[plugin_id] = entry
        if entry.get("enabled") is not True:
            blockers.append(f"Claude plugin {plugin_id!r} is disabled")
        errors = entry.get("errors")
        if isinstance(errors, list) and errors:
            blockers.append(f"Claude plugin {plugin_id!r} reports errors")
        evidence.append(f"plugin={plugin_id} version={entry.get('version', 'unknown')}")

    if blockers:
        return _blocked(
            item,
            activation,
            status=ACTIVATION_REQUIRED,
            evidence=tuple(evidence),
            blockers=tuple(blockers),
        )

    for target in activation.targets:
        entry = plugin_entries.get(target.plugin_id or "")
        install_path = entry.get("installPath") if entry else None
        if not isinstance(install_path, str) or not install_path:
            blockers.append(f"Claude plugin {target.plugin_id!r} has no install path")
            continue
        skill = Path(install_path) / "skills" / target.name / "SKILL.md"
        if not skill.is_file():
            blockers.append(f"Claude skill {target.name!r} is not discoverable")
            continue
        evidence.append(f"skill={target.name} path={skill}")

    if blockers:
        return _blocked(
            item,
            activation,
            status=FAILED,
            evidence=tuple(evidence),
            blockers=tuple(blockers),
            activated=True,
        )
    return _success(item, activation, tuple(evidence))


def _codex_skills_root() -> Path:
    configured = os.environ.get("CODEX_HOME")
    home = Path(configured).expanduser() if configured else Path.home() / ".codex"
    return home / "skills"


def _inspect_codex(
    root: Path,
    item: Component,
    activation: SkillActivation,
    skills_root: Path,
) -> SkillDiscovery:
    evidence: list[str] = []
    missing: list[str] = []
    conflicts: list[str] = []
    upstream = root / SKILLS_DIR / item.id

    for target in activation.targets:
        source = upstream / Path(*target.source_path.split("/"))
        projected = Path(skills_root) / target.name / "SKILL.md"
        if not projected.is_file():
            missing.append(f"Codex skill {target.name!r} is not activated")
            continue
        try:
            same_file = source.is_file() and projected.samefile(source)
        except OSError:
            same_file = False
        if not same_file:
            conflicts.append(
                f"Codex skill {target.name!r} is not linked to the locked payload"
            )
            continue
        evidence.append(f"skill={target.name} path={projected}")

    if conflicts:
        return _blocked(
            item,
            activation,
            status=CONFLICT,
            evidence=tuple(evidence),
            blockers=tuple(conflicts + missing),
            activated=True,
        )
    if missing:
        return _blocked(
            item,
            activation,
            status=ACTIVATION_REQUIRED,
            evidence=tuple(evidence),
            blockers=tuple(missing),
        )
    return _success(item, activation, tuple(evidence))


def _blocked(
    item: Component,
    activation: SkillActivation,
    *,
    status: str,
    blockers: tuple[str, ...],
    evidence: tuple[str, ...] = (),
    activated: bool = False,
) -> SkillDiscovery:
    return SkillDiscovery(
        component=item.id,
        harness=activation.harness,
        mechanism=activation.mechanism,
        checked=True,
        installed=True,
        activated=activated,
        discoverable=False,
        status=status,
        evidence=evidence,
        blockers=blockers,
        next_action=activation.install_hint,
    )


def _success(
    item: Component, activation: SkillActivation, evidence: tuple[str, ...]
) -> SkillDiscovery:
    return SkillDiscovery(
        component=item.id,
        harness=activation.harness,
        mechanism=activation.mechanism,
        checked=True,
        installed=True,
        activated=True,
        discoverable=True,
        status=DISCOVERABLE,
        evidence=evidence,
        blockers=(),
        next_action="route matching execution intent to the official skill",
    )


__all__ = [
    "ACTIVATION_REQUIRED",
    "CLAUDE_CODE",
    "CODEX",
    "CONFLICT",
    "DISCOVERABLE",
    "FAILED",
    "NOT_CHECKED",
    "NOT_INSTALLED",
    "SkillDiscovery",
    "inspect_official_skills",
]
