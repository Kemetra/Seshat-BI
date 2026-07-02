"""`retail init` substrate bootstrap (feature 070) -- SUBSTRATE-WRITING ONLY.

This module is the mechanical half of the Compass-Driven `init`: it writes the
backstage substrate (compass projection + manifests via ``compass_project``, and the
fenced ``SESHAT-KIT`` regions of AGENTS.md / CLAUDE.md via ``fence``) and returns a
"next agent step" string. It does NOT profile, open a DB, prompt, or show a menu
(BLOCKER-1 / FR-001 / FR-003): the delegate -> route -> profile flow is the AGENT
performing ``.claude/skills/retail-init/SKILL.md`` over the existing prose verbs
(``first-hour-compass`` -> ``retail-onboard-table``), never this module.

NO DB, NO network, NO execution, NO run-state (FR-005/FR-010/FR-011). It MAY parse
YAML lazily via ``compass_project`` (which owns the pyyaml import); the ``retail
check`` core stays stdlib-only. Authored files are UTF-8 no BOM, ``\\n`` (Principle IX).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import compass_project
from .fence import START, read_fence_body, write_fence

# The governed files whose fenced SESHAT-KIT region init projects into. Only the
# fenced region is ever written; everything outside is hand-authored / constitution
# -owned and left byte-identical (FR-006/FR-007).
_FENCED_FILES = ("AGENTS.md", "CLAUDE.md")

_NEXT_STEP = (
    "Bootstrapped. Next (agent-performed, not this CLI): run the `retail-init` skill "
    "-> delegate the worked-example offer to `first-hour-compass` -> route into "
    "`retail-onboard-table` to profile your table (grain candidates + column types "
    "over a live DB, or `[PENDING LIVE PROFILE]` without one). The agent handles "
    "sequence + plumbing; you own grain / PII / rollups / product identity."
)


@dataclass(frozen=True)
class BootstrapResult:
    """Outcome of a substrate bootstrap run."""

    written: tuple[str, ...]
    fenced: tuple[str, ...]
    already_bootstrapped: bool
    next_step: str


def bootstrap(repo: Path | str) -> BootstrapResult:
    """Write the kit substrate for ``repo`` (idempotent). Returns the next agent step.

    Writes compass.yaml + manifests, then projects the canonical prose into the
    ``SESHAT-KIT`` fence of each governed file. Re-running with an unchanged source
    is a no-op on already-correct fences and reports ``already_bootstrapped``.
    """
    repo = Path(repo)

    # Detect prior bootstrap BEFORE writing: a compass.yaml + at least one fence.
    was_bootstrapped = (repo / compass_project.COMPASS_REL).exists() and any(
        _has_fence(repo / f) for f in _FENCED_FILES
    )

    written = compass_project.project_all(repo)

    source = compass_project.load_source(repo)
    prose = compass_project.render_prose(source)

    fenced: list[str] = []
    for name in _FENCED_FILES:
        path = repo / name
        if not path.exists():
            # init never CREATES a governed file it wasn't given; skip absent ones.
            continue
        result = write_fence(path, prose)
        if not result.ok:
            # A malformed fence is a hard stop (FR edge case): report, do not force.
            raise RuntimeError(
                f"cannot write SESHAT-KIT fence in {name}: {result.stopped_reason}"
            )
        fenced.append(name)

    return BootstrapResult(
        written=written,
        fenced=tuple(fenced),
        already_bootstrapped=was_bootstrapped,
        next_step=_NEXT_STEP,
    )


def _has_fence(path: Path) -> bool:
    """True if ``path`` exists and already carries a SESHAT-KIT fence."""
    if not path.exists():
        return False
    return read_fence_body(path) is not None or START in path.read_text(
        encoding="utf-8-sig"
    )
