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
STALE = "stale"
FAILED = "failed"

INSTALL_MARKER = ".seshat-installed"

Runner = Callable[[list[str], Path], subprocess.CompletedProcess]
ToolLookup = Callable[[str], str | None]


def installed_ref(root: Path, component_id: str) -> str | None:
    """The exact ref recorded by the installer for a cloned skill payload.

    ``None`` when no marker exists or it cannot be read. Only GitHub components
    record a ref; the marker for other source types carries a version instead,
    so callers must scope the comparison themselves.
    """
    marker = Path(root) / SKILLS_DIR / component_id / INSTALL_MARKER
    try:
        return marker.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _stale(
    item: Component,
    activation: SkillActivation,
    marker_ref: str,
    resolved_ref: str,
) -> SkillDiscovery:
    """A payload on disk whose ref is not the one now resolved.

    Presence alone would report ``discoverable`` for a coordinate the checkout
    does not actually contain, so an upgrade would silently keep serving the
    old upstream instructions (Codex P2, #597). The mismatch is named rather
    than collapsed into ``not-installed``: the operator needs to see which ref
    is on disk to know what they are running.
    """
    return SkillDiscovery(
        component=item.id,
        harness=activation.harness,
        mechanism=activation.mechanism,
        checked=True,
        installed=True,
        activated=False,
        discoverable=False,
        status=STALE,
        evidence=(f"marker_ref={marker_ref}", f"resolved_ref={resolved_ref}"),
        blockers=(
            f"the installed payload is at {marker_ref!r} but {resolved_ref!r} "
            "is now resolved; discovery cannot prove the resolved coordinate",
        ),
        next_action=(
            "approve seshat integrations setup --refresh --apply to reinstall "
            "this package at the resolved ref"
        ),
    )


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


@dataclass(frozen=True)
class _Probe:
    """The resolved seams one inspection pass runs against.

    Bundled so the entry point keeps a small signature and every helper reads
    the same already-defaulted seams instead of re-deriving them.
    """

    root: Path
    requested: frozenset[str]
    harness_roots: Mapping[str, Path]
    resolved_refs: Mapping[str, str]
    claude_plugins: Mapping[str, dict]
    claude_error: str | None

    def codex_root(self) -> Path:
        return self.harness_roots.get(CODEX, _codex_skills_root())


@dataclass(frozen=True)
class DiscoveryInputs:
    """What a caller may supply to one read-only discovery pass.

    Every field is optional and injectable so a test never touches the real
    PATH, a real harness directory, or a real subprocess. Bundled rather than
    passed as loose keywords: the set grows with each supported harness, and a
    caller that supplies none must still get the safe defaults.

    ``resolved_refs`` maps a component id to the ref currently resolved for it.
    When supplied, a payload whose install marker records a DIFFERENT ref is
    reported ``stale`` rather than inspected, because presence at some ref is
    not proof of discovery at the resolved one.
    """

    harnesses: tuple[str, ...] = ()
    runner: Runner | None = None
    harness_roots: Mapping[str, Path] | None = None
    tool_lookup: ToolLookup | None = None
    resolved_refs: Mapping[str, str] | None = None


def inspect_official_skills(
    root: Path,
    components: Iterable[Component],
    *,
    installed: Mapping[str, bool],
    inputs: DiscoveryInputs | None = None,
) -> list[SkillDiscovery]:
    """Classify catalog-declared official skills for requested harnesses.

    An omitted harness produces an explicit ``not-checked`` record. Requesting
    Claude Code executes only ``claude plugin list --json``. Requesting Codex
    reads its skill directory. Neither path writes anything.
    """

    probe = _build_probe(root, inputs or DiscoveryInputs())
    return [
        _classify(item, activation, probe, bool(installed.get(item.id, False)))
        for item in components
        for activation in item.skill_activations
    ]


def _build_probe(root: Path, inputs: DiscoveryInputs) -> _Probe:
    """Resolve every caller-supplied seam to its default exactly once.

    The Claude inventory is read here rather than per component, so requesting
    that harness costs one ``claude plugin list`` call for the whole pass.
    """
    resolved_root = Path(root).resolve()
    requested = frozenset(inputs.harnesses)

    claude_plugins: dict[str, dict] | None = None
    claude_error: str | None = None
    if CLAUDE_CODE in requested:
        claude_plugins, claude_error = _claude_inventory(
            resolved_root,
            inputs.runner or _run,
            inputs.tool_lookup or shutil.which,
        )

    return _Probe(
        root=resolved_root,
        requested=requested,
        harness_roots=inputs.harness_roots or {},
        resolved_refs=inputs.resolved_refs or {},
        claude_plugins=claude_plugins or {},
        claude_error=claude_error,
    )


def _classify(
    item: Component,
    activation: SkillActivation,
    probe: _Probe,
    is_installed: bool,
) -> SkillDiscovery:
    """One package/harness verdict, ordered cheapest observation first."""
    if activation.harness not in probe.requested:
        return _not_checked(item, activation, is_installed)
    if not is_installed:
        return _not_installed(item, activation)
    drifted = _drifted_ref(probe, item)
    if drifted is not None:
        return _stale(item, activation, *drifted)
    if activation.harness == CLAUDE_CODE:
        return _inspect_claude(
            item, activation, probe.claude_plugins, probe.claude_error
        )
    return _inspect_codex(probe.root, item, activation, probe.codex_root())


def _drifted_ref(probe: _Probe, item: Component) -> tuple[str, str] | None:
    """``(marker_ref, resolved_ref)`` when the checkout is not the resolved ref.

    Scoped to components that record a ref at all: an absent expectation, an
    unreadable marker, or a matching pair all mean "no drift to report", so a
    caller that never resolved refs keeps the previous behaviour exactly.
    """
    expected = probe.resolved_refs.get(item.id)
    if not expected:
        return None
    marker_ref = installed_ref(probe.root, item.id)
    if marker_ref is None or marker_ref == expected:
        return None
    return marker_ref, expected


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
    """The installed Claude plugins, or the reason they could not be read.

    Every failure is a NAMED error rather than an empty inventory: an
    unreadable inventory must not look like "no plugins installed", which
    would report a present package as missing.
    """
    if tool_lookup("claude") is None:
        return None, "Claude Code is not on PATH"
    result = runner(["claude", "plugin", "list", "--json"], root)
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        return None, detail or "Claude Code plugin inventory failed"
    return _parse_plugin_inventory(result.stdout or "")


def _parse_plugin_inventory(
    stdout: str,
) -> tuple[dict[str, dict] | None, str | None]:
    """Parse ``claude plugin list --json`` output into id-keyed entries."""
    try:
        body = json.loads(stdout)
    except ValueError:
        return None, "Claude Code plugin inventory was not valid JSON"
    if not isinstance(body, list):
        return None, "Claude Code plugin inventory was not a list"
    return {
        entry["id"]: entry
        for entry in body
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }, None


def _plugin_activation(
    activation: SkillActivation, plugins: Mapping[str, dict]
) -> tuple[dict[str, dict], list[str], list[str]]:
    """Activation state of every distinct plugin one activation names.

    Returns the usable entries plus their evidence and blockers. A plugin that
    is absent contributes no entry, so the payload pass below cannot mistake it
    for one that merely lacks an install path.
    """
    entries: dict[str, dict] = {}
    evidence: list[str] = []
    blockers: list[str] = []
    for plugin_id in dict.fromkeys(
        target.plugin_id for target in activation.targets if target.plugin_id
    ):
        entry = plugins.get(plugin_id)
        if entry is None:
            blockers.append(f"Claude plugin {plugin_id!r} is not installed")
            continue
        entries[plugin_id] = entry
        blockers.extend(_plugin_faults(plugin_id, entry))
        evidence.append(f"plugin={plugin_id} version={entry.get('version', 'unknown')}")
    return entries, evidence, blockers


def _plugin_faults(plugin_id: str, entry: Mapping[str, object]) -> list[str]:
    """Every reason an installed plugin is still not usable."""
    faults: list[str] = []
    if entry.get("enabled") is not True:
        faults.append(f"Claude plugin {plugin_id!r} is disabled")
    errors = entry.get("errors")
    if isinstance(errors, list) and errors:
        faults.append(f"Claude plugin {plugin_id!r} reports errors")
    return faults


def _claude_payload(
    activation: SkillActivation, entries: Mapping[str, dict]
) -> tuple[list[str], list[str]]:
    """Whether each named skill file is actually on disk under its plugin."""
    evidence: list[str] = []
    blockers: list[str] = []
    for target in activation.targets:
        entry = entries.get(target.plugin_id or "")
        install_path = entry.get("installPath") if entry else None
        if not isinstance(install_path, str) or not install_path:
            blockers.append(f"Claude plugin {target.plugin_id!r} has no install path")
            continue
        skill = Path(install_path) / "skills" / target.name / "SKILL.md"
        if not skill.is_file():
            blockers.append(f"Claude skill {target.name!r} is not discoverable")
            continue
        evidence.append(f"skill={target.name} path={skill}")
    return evidence, blockers


def _inspect_claude(
    item: Component,
    activation: SkillActivation,
    plugins: Mapping[str, dict],
    inventory_error: str | None,
) -> SkillDiscovery:
    if inventory_error is not None:
        return _blocked(item, activation, _Block(FAILED, (inventory_error,)))

    entries, evidence, blockers = _plugin_activation(activation, plugins)
    if blockers:
        return _blocked(
            item,
            activation,
            _Block(ACTIVATION_REQUIRED, tuple(blockers), tuple(evidence)),
        )

    payload_evidence, payload_blockers = _claude_payload(activation, entries)
    evidence.extend(payload_evidence)
    if payload_blockers:
        return _blocked(
            item,
            activation,
            _Block(FAILED, tuple(payload_blockers), tuple(evidence), activated=True),
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
            _Block(
                CONFLICT,
                tuple(conflicts + missing),
                tuple(evidence),
                activated=True,
            ),
        )
    if missing:
        return _blocked(
            item,
            activation,
            _Block(ACTIVATION_REQUIRED, tuple(missing), tuple(evidence)),
        )
    return _success(item, activation, tuple(evidence))


@dataclass(frozen=True)
class _Block:
    """One non-discoverable verdict's payload, kept together as it travels."""

    status: str
    blockers: tuple[str, ...]
    evidence: tuple[str, ...] = ()
    activated: bool = False


def _blocked(
    item: Component,
    activation: SkillActivation,
    block: _Block,
) -> SkillDiscovery:
    status, blockers = block.status, block.blockers
    evidence, activated = block.evidence, block.activated
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
    "DiscoveryInputs",
    "DISCOVERABLE",
    "FAILED",
    "NOT_CHECKED",
    "NOT_INSTALLED",
    "STALE",
    "SkillDiscovery",
    "inspect_official_skills",
    "installed_ref",
]
