"""Kit projection-drift linter (feature 072) -- the compass's enforcement arm.

Fails loud when a compass PROJECTION drifts from the canonical kit source:
  - YAML projection: ``.seshat/compass.yaml`` vs ``project_yaml(source)``;
  - prose projection: each governed file's ``SESHAT-KIT`` fenced body vs
    ``render_prose(source)``.

Both checks REUSE 070's ``compass_project`` callables -- no re-derivation. This is a
standalone step (``retail kit-lint``), NOT a ``retail check`` core rule: it parses YAML
(via ``compass_project``), which the stdlib-only core must never do. It is read-only,
reads NO constitution at all, and emits no numeric score -- explicit pass/fail per check
+ the exit code.

The source-vs-constitution check proposed in an earlier draft was CUT (it was a
source-vs-source tautology; only 2 of 4 hard_stops have a constitutional-document home)
and is deferred as a human-shaped governance slice. See
``specs/072-kit-drift-linter/`` (the scope-cut note).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import compass_project
from .fence import read_fence_body

# Governed files whose SESHAT-KIT fenced body is a prose projection of the source.
_FENCED_FILES = ("AGENTS.md", "CLAUDE.md")


@dataclass(frozen=True)
class CheckResult:
    """One drift check's outcome. No numeric score (FR-009) -- pass/fail + detail."""

    name: str
    ok: bool
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class LintReport:
    """Aggregate of the checks run. ``ok`` maps to the CLI exit code."""

    results: tuple[CheckResult, ...] = ()
    bootstrapped: bool = True

    @property
    def ok(self) -> bool:
        # Not bootstrapped -> nothing to lint -> clean (absence is not drift, FR-006).
        if not self.bootstrapped:
            return True
        return all(r.ok for r in self.results)


def is_bootstrapped(repo: Path) -> bool:
    """True once ``repo`` has a kit source + a compass projection.

    Public since Spec A: the CLI check path and the generators (Spec C) reuse this
    single predicate to decide whether a repo is the kit itself (run everything) or
    a repo the kit was merely downloaded into (KIT_SELF rules skip; generators refuse).
    """
    return (repo / compass_project.SOURCE_REL).exists() and (
        repo / compass_project.COMPASS_REL
    ).exists()


# Back-compat alias for internal callers/tests that referenced the private name.
_is_bootstrapped = is_bootstrapped


def check_yaml_projection(repo: Path) -> CheckResult:
    """YAML projection drift: compass.yaml byte-equals project_yaml(source)."""
    ok = compass_project.check_yaml_drift(repo)
    details = (
        ()
        if ok
        else (
            f"{compass_project.COMPASS_REL} != project_yaml(kit-source.yaml) "
            "-- re-run `retail init` to re-project",
        )
    )
    return CheckResult(name="yaml_projection", ok=ok, details=details)


def check_prose_projection(repo: Path, source: dict) -> CheckResult:
    """Prose projection drift: each fenced body == render_prose(source)."""
    drifted: list[str] = []
    for name in _FENCED_FILES:
        path = repo / name
        if not path.exists():
            continue
        body = read_fence_body(path)
        if body is None:
            drifted.append(f"{name}: missing/malformed SESHAT-KIT fence")
            continue
        if not compass_project.check_prose_drift(source, body):
            drifted.append(
                f"{name}: SESHAT-KIT fenced body drifted from render_prose(source)"
            )
    return CheckResult(name="prose_projection", ok=not drifted, details=tuple(drifted))


def lint(repo: Path | str) -> LintReport:
    """Run the projection-drift checks over ``repo``. Read-only.

    Not-bootstrapped -> a clean report (exit 0). A broken/unparseable source ->
    a named ``source_parse`` failing check, never a raw traceback (FR-008).
    """
    repo = Path(repo)

    if not _is_bootstrapped(repo):
        return LintReport(results=(), bootstrapped=False)

    # Load the source once; a parse/shape error is a named failing check, not a crash.
    try:
        source = compass_project.load_source(repo)
    except Exception as exc:  # yaml parse error, non-mapping, unreadable -> report it
        return LintReport(
            results=(
                CheckResult(
                    name="source_parse",
                    ok=False,
                    details=(
                        f"{compass_project.SOURCE_REL} could not be parsed: {exc}",
                    ),
                ),
            ),
            bootstrapped=True,
        )

    return LintReport(
        results=(
            check_yaml_projection(repo),
            check_prose_projection(repo, source),
        ),
        bootstrapped=True,
    )
