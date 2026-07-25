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

    This means "the kit substrate is installed HERE" -- nothing more. It is the
    right predicate for the kit-lint drift checks below (there is a projection to
    reconcile) and for the generators (Spec C).

    It is deliberately NOT the predicate for the KIT_SELF rule tier: ``seshat
    init`` (``kit_init.bootstrap`` + ``compass_project.seed_kit_source``) writes
    exactly these two files into ANY repo the kit was installed into, so
    substrate presence cannot distinguish the kit from its consumers. Use
    ``is_kit_self_repo`` for that (issue #486).
    """
    return (repo / compass_project.SOURCE_REL).exists() and (
        repo / compass_project.COMPASS_REL
    ).exists()


# The kit's own distribution name, as declared in its pyproject.
_KIT_DIST_NAME = "seshat-bi"
_KIT_PACKAGE_REL = "src/seshat/__init__.py"
_PYPROJECT_REL = "pyproject.toml"


def is_kit_self_repo(repo: Path) -> bool:
    """True only for the kit's OWN source repo -- the ``seshat-bi`` distribution.

    The KIT_SELF rule tier checks the kit's own internal manifests
    (``docs/routing/routes.yaml``, ``docs/quality/status-claims.yaml``, the KPI
    domain corpus, ...). Those are files only the kit's own repo has, and which a
    consumer workspace "never has and must never fabricate" (FR-004, recorded in
    ``workspace_init``'s spike note). So the tier must key on kit IDENTITY, not on
    substrate presence.

    Identity = the repo carries the kit's own package source AND declares itself
    as the ``seshat-bi`` distribution. Neither ``seshat init``, ``init-project``,
    nor ``seed_kit_source`` ever writes ``pyproject.toml`` or ``src/seshat/``, so
    no supported setup flow can make a consumer repo satisfy this (issue #486:
    ``is_bootstrapped`` could, which fired 10 hard errors on the golden path).
    """
    if not (repo / _KIT_PACKAGE_REL).exists():
        return False
    pyproject = repo / _PYPROJECT_REL
    try:
        text = pyproject.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False
    return _declares_kit_distribution(text)


def _declares_kit_distribution(pyproject_text: str) -> bool:
    """True when ``pyproject_text`` declares ``name = "seshat-bi"``.

    Text-scanned rather than TOML-parsed: this runs on every ``check`` and must
    never raise on a malformed or partially written pyproject -- an unreadable
    manifest simply means "not provably the kit", which fails safe toward the
    consumer-repo behavior (rules skip rather than error).
    """
    for raw_line in pyproject_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("name"):
            continue
        key, _, value = line.partition("=")
        if key.strip() != "name":
            continue
        if value.strip().strip("\"'") == _KIT_DIST_NAME:
            return True
    return False


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
