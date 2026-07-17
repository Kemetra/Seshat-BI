"""Governed dependency freshness and co-resolution (spec 136).

A plain script (NO new `seshat` CLI verb, ratified Option B). Two modes:

  * ``--check``     -- the fail-closed co-resolution gate. Resolves every
                       declared install environment and every declared
                       cross-product in an EPHEMERAL throwaway venv via
                       ``pip install --dry-run --report``; nothing is installed
                       into the caller's interpreter (SC-002). Exits non-zero on
                       any RESOLUTION or CONFIG outcome, printing the (redacted)
                       resolver text; exits with a DISTINCT code if only INFRA
                       occurred so a flaky network is never read as a conflict.
  * ``--freshness`` -- the advisory reporter. For each governed pin, reports the
                       latest STABLE version on PyPI and, when a newer stable
                       exists, PROPOSES a bump carrying a solve-proof. It changes
                       NO pin value and opens NO PR (FR-008/FR-012).

The declared environments live as committed DATA in ``dependency-environments.yaml``
(FR-001); this script hardcodes no pin list (FR-015).

Import boundary: this is a CI script, not part of the offline stdlib-only
``seshat check`` core, so it may import ``yaml`` and (for redaction) the repo's
C2 secret-shape regexes. It bootstraps ``<repo>/src`` onto ``sys.path`` so it
runs WITHOUT ``seshat`` being installed (the co-resolution CI job installs no
optional extra into its interpreter).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
import venv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import mkdtemp
from urllib.error import URLError
from urllib.request import urlopen

# --- path bootstrap: reach the repo's src/ so redaction can reuse the C2 shapes
# without seshat being pip-installed (SC-002: nothing installed in the job
# interpreter). Computed from this file's location, not the cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import yaml  # noqa: E402  (after the path bootstrap; a CI-script dep, not core)

# --------------------------------------------------------------------------- #
# Outcome model.
# --------------------------------------------------------------------------- #


class ResolveOutcome(Enum):
    """The classified result of one resolve attempt (spec Key Entities)."""

    PASS = "pass"
    RESOLUTION = "resolution"
    INFRA = "infra"
    CONFIG = "config"


# Distinct process exit codes so CI can tell the four outcomes apart from the
# code alone (FR-004/FR-005, SC-004). CONFIG gets its OWN code so it is
# distinguishable from BOTH RESOLUTION and INFRA at the exit-code level, not
# only in the printed label -- both CONFIG and RESOLUTION still fail CLOSED
# (non-zero, not retryable); INFRA is the one retryable/annotatable case.
EXIT_OK = 0
EXIT_RESOLUTION = 1  # a real dependency conflict -- fail closed
EXIT_CONFIG = 2  # a bad manifest entry (missing pyproject / undefined extra)
EXIT_INFRA = 3  # network/index only -- distinct so a flake is not a conflict

# pip >= 22.2 introduced `--report` (plan-review D5).
_MIN_PIP_FOR_REPORT = (22, 2)


class InfraError(Exception):
    """Raised by the PyPI fetch seam on a network/index failure."""


# --------------------------------------------------------------------------- #
# Manifest records.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Environment:
    id: str
    pyproject: str
    extras: tuple[str, ...]
    local: bool
    path: str | None


@dataclass(frozen=True)
class CrossProduct:
    id: str
    combine: tuple[str, ...]


@dataclass(frozen=True)
class GovernedPin:
    dist: str


@dataclass(frozen=True)
class Manifest:
    root: Path
    environments: tuple[Environment, ...]
    cross_products: tuple[CrossProduct, ...]
    governed_pins: tuple[GovernedPin, ...]

    def by_id(self, env_id: str) -> Environment | None:
        return next((e for e in self.environments if e.id == env_id), None)


@dataclass(frozen=True)
class ResolveResult:
    """One resolve attempt's classified outcome plus a (redacted) detail line."""

    target_id: str
    outcome: ResolveOutcome
    detail: str


@dataclass(frozen=True)
class ResolveRun:
    """The raw result of one `pip install --dry-run --report` subprocess."""

    returncode: int
    stdout: str
    stderr: str
    report_json: str | None


def _parse_environment(entry: dict) -> Environment:
    return Environment(
        id=str(entry["id"]),
        pyproject=str(entry["pyproject"]),
        extras=tuple(str(x) for x in (entry.get("extras") or [])),
        local=bool(entry.get("local", False)),
        path=(str(entry["path"]) if entry.get("path") is not None else None),
    )


def _parse_cross_product(entry: dict) -> CrossProduct:
    return CrossProduct(
        id=str(entry["id"]),
        combine=tuple(str(m) for m in (entry.get("combine") or [])),
    )


def load_manifest(path: Path) -> Manifest:
    """Parse the committed environments manifest into typed records (FR-001).

    Structural problems that are not resolvable per-environment (a non-mapping
    document) raise; a per-environment problem (missing pyproject, undefined
    extra) is deferred to ``resolve_environment`` so it classifies as CONFIG.
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"manifest is not a mapping: {path}")
    return Manifest(
        root=path.resolve().parent,
        environments=tuple(map(_parse_environment, _section(doc, "environments"))),
        cross_products=tuple(
            map(_parse_cross_product, _section(doc, "cross_products"))
        ),
        governed_pins=tuple(map(_parse_governed_pin, _section(doc, "governed_pins"))),
    )


def _section(doc: dict, key: str) -> list:
    """One manifest section as a list (an absent/None section is empty)."""
    return doc.get(key) or []


def _parse_governed_pin(entry: dict) -> GovernedPin:
    return GovernedPin(dist=str(entry["dist"]))


# --------------------------------------------------------------------------- #
# Requirement assembly (plan-review D1: local members as LOCAL PATHS).
# --------------------------------------------------------------------------- #


class ConfigError(Exception):
    """A manifest points at a missing pyproject or an undefined extra (FR-005)."""


def _read_pyproject_extras(project_path: Path) -> set[str]:
    data = tomllib.loads(project_path.read_text(encoding="utf-8"))
    optional = data.get("project", {}).get("optional-dependencies", {})
    return set(optional.keys())


def _assemble_member(manifest: Manifest, env: Environment) -> str:
    """Assemble ONE declared environment's install requirement.

    A repository-local project (``local: true``) is assembled as a LOCAL PATH
    requirement (``<path>[extras]``), NEVER by distribution name (plan-review
    D1) -- so the gate proves the PR's working tree resolves, not PyPI's
    published copy. The pyproject is read only to VALIDATE the declared extras
    exist (FR-005); the version pins are resolved by pip from that same tree.
    """
    _validate_member(manifest, env)
    local_dir = (manifest.root / env.path).resolve()  # type: ignore[arg-type]
    extras_suffix = f"[{','.join(env.extras)}]" if env.extras else ""
    return f"{local_dir.as_posix()}{extras_suffix}"


def _require_pyproject(manifest: Manifest, env: Environment) -> Path:
    project_path = manifest.root / env.pyproject
    if not project_path.is_file():
        raise ConfigError(
            f"environment {env.id!r}: pyproject not found: {env.pyproject}"
        )
    return project_path


def _require_defined_extras(env: Environment, project_path: Path) -> None:
    defined = _read_pyproject_extras(project_path)
    unknown = [x for x in env.extras if x not in defined]
    if unknown:
        raise ConfigError(
            f"environment {env.id!r}: undefined extra(s) {unknown} "
            f"(defined: {sorted(defined)})"
        )


def _require_local(env: Environment) -> None:
    if not env.local or env.path is None:
        raise ConfigError(
            f"environment {env.id!r}: only repository-local projects are "
            "supported; mark 'local: true' with a 'path'"
        )


def _validate_member(manifest: Manifest, env: Environment) -> None:
    """Fail-closed CONFIG validation of one declared environment (FR-005)."""
    project_path = _require_pyproject(manifest, env)
    _require_defined_extras(env, project_path)
    _require_local(env)


def assemble_requirements(manifest: Manifest, env: Environment) -> list[str]:
    """Requirements for one declared environment (a single local-path member)."""
    return [_assemble_member(manifest, env)]


def _member_environment(
    manifest: Manifest, cp: CrossProduct, member_id: str
) -> Environment:
    env = manifest.by_id(member_id)
    if env is None:
        raise ConfigError(f"cross-product {cp.id!r}: unknown member {member_id!r}")
    return env


def assemble_cross_product(manifest: Manifest, cp: CrossProduct) -> list[str]:
    """Union the requirement sets of a cross-product's members (T012)."""
    reqs: list[str] = []
    members = [_member_environment(manifest, cp, m) for m in cp.combine]
    for req in (r for env in members for r in assemble_requirements(manifest, env)):
        if req not in reqs:
            reqs.append(req)
    return reqs


# --------------------------------------------------------------------------- #
# Classification (plan-review D2: default RESOLUTION; INFRA on signatures only).
# --------------------------------------------------------------------------- #

# Explicit, fixture-tested network signatures. INFRA is claimed ONLY on one of
# these; anything else on a non-zero exit defaults to RESOLUTION (fail-closed).
_INFRA_SIGNATURES = (
    "temporary failure in name resolution",
    "failed to establish a new connection",
    "network is unreachable",
    "connection broken by",
    "connection refused",
    "connection reset",
    "connection timed out",
    "read timed out",
    "max retries exceeded",
    "name or service not known",
    "proxyerror",
    "503 server error",
    "502 server error",
    "504 server error",
)


def classify_resolve(returncode: int, stderr: str) -> ResolveOutcome:
    """Classify a resolve subprocess result (FR-003/FR-004).

    Defaults to RESOLUTION on any non-zero exit (fail-closed, plan-review D2);
    returns INFRA only when stderr carries an explicit network signature.
    """
    if returncode == 0:
        return ResolveOutcome.PASS
    low = stderr.lower()
    if any(sig in low for sig in _INFRA_SIGNATURES):
        return ResolveOutcome.INFRA
    return ResolveOutcome.RESOLUTION


def pip_supports_report(version: str) -> bool:
    """True if a pip version string is >= 22.2 (supports --report; D5)."""
    parts: list[int] = []
    for token in version.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        parts.append(int(digits) if digits else 0)
        if len(parts) == 2:
            break
    while len(parts) < 2:
        parts.append(0)
    return (parts[0], parts[1]) >= _MIN_PIP_FOR_REPORT


# --------------------------------------------------------------------------- #
# Redaction: reuse the repo's C2 connection-string shapes (FR-016).
# --------------------------------------------------------------------------- #

# The C2 DETECTION regexes live in seshat.rules.git_meta (they return findings,
# not masked text). We borrow pr_summary's masking POSTURE (iterate patterns,
# .sub a fixed token) but apply it over the C2 CONNECTION-STRING shapes -- not
# pr_summary's PII shapes, which by their own docstring do NOT cover a DSN URL.
from seshat.rules.git_meta import (  # noqa: E402
    CONN_URI_RE,
    DO_CLUSTER_SLUG_RE,
    DO_ENDPOINT_RE,
    MYSQL_URI_RE,
    ODBC_SECRET_RE,
)

_REDACT_TOKEN = "[REDACTED]"

# The exact C2 DETECTION shapes, applied by substitution -- NOT re-implemented
# (the reuse-only rule). CONN_URI_RE / MYSQL_URI_RE match up to and including
# the `@`, so the credential (userinfo) -- the thing FR-016 protects -- is what
# gets masked; the host after the `@` is not a credential and is deliberately
# left, matching C2's own posture (C2 masks a DigitalOcean host via
# DO_ENDPOINT_RE / DO_CLUSTER_SLUG_RE specifically, not a generic host).
_C2_SUBSTITUTION_SHAPES = (
    CONN_URI_RE,
    MYSQL_URI_RE,
    DO_ENDPOINT_RE,
    ODBC_SECRET_RE,
    DO_CLUSTER_SLUG_RE,
)


def redact(text: str) -> str:
    """Mask any C2 connection-string / secret shape in ``text`` before it is
    surfaced (FR-016). A clean conflict message is returned unchanged.

    Reuses the repository's C2 secret-shape posture: the SAME detection regexes
    ``seshat check``'s C2 rule uses (imported from ``git_meta``, never copied),
    applied by substitution (mirroring the masking style in
    ``seshat.pr_summary.mask``). Idempotent -- the ``[REDACTED]`` token matches
    none of the shapes.

    Non-coverage (documented, like pr_summary.mask's own DSN gap): the C2
    Snowflake account/password PAIR detector (``_has_snowflake_secret_pair``)
    is line-level pairing logic, not a substitutable regex, and is NOT applied
    here -- a resolver error is not a place a Snowflake kwargs pair is emitted,
    and lifting that pair logic would be a new redaction primitive the
    reuse-only rule forbids.
    """
    out = text
    for pattern in _C2_SUBSTITUTION_SHAPES:
        out = pattern.sub(_REDACT_TOKEN, out)
    return out


# --------------------------------------------------------------------------- #
# Ephemeral-venv resolve (implemented in Phase 3; the seam the stubs patch).
# --------------------------------------------------------------------------- #


def _venv_python(venv_dir: Path) -> Path:
    """The interpreter inside an ephemeral venv (cross-platform)."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run_resolve(requirements: list[str], report_path: Path) -> ResolveRun:
    """Resolve ``requirements`` in a throwaway venv via ``pip install --dry-run
    --report`` -- WITHOUT installing anything into this interpreter (FR-002).

    This is the seam unit tests stub; it is exercised for real only by the live
    CI job and the local smoke.
    """
    venv_dir = Path(mkdtemp(prefix="dep_coresolve_"))
    try:
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        py = _venv_python(venv_dir)
        version = subprocess.run(
            [str(py), "-m", "pip", "--version"],
            capture_output=True,
            text=True,
        )
        pip_ver = version.stdout.split()[1] if version.stdout.split() else "0"
        if not pip_supports_report(pip_ver):
            return ResolveRun(
                returncode=2,
                stdout="",
                stderr=(
                    f"CONFIG: ephemeral venv pip {pip_ver} is older than "
                    "22.2 and does not support --report"
                ),
                report_json=None,
            )
        proc = subprocess.run(
            [
                str(py),
                "-m",
                "pip",
                "install",
                "--dry-run",
                "--report",
                str(report_path),
                *requirements,
            ],
            capture_output=True,
            text=True,
        )
        report_json = (
            report_path.read_text(encoding="utf-8")
            if proc.returncode == 0 and report_path.is_file()
            else None
        )
        return ResolveRun(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            report_json=report_json,
        )
    finally:
        shutil.rmtree(venv_dir, ignore_errors=True)


def _resolve_reqs(target_id: str, requirements: list[str]) -> ResolveResult:
    """Run a resolve for an already-assembled requirement set and classify it."""
    report_path = Path(mkdtemp(prefix="dep_report_")) / "report.json"
    try:
        run = _run_resolve(requirements, report_path)
    finally:
        shutil.rmtree(report_path.parent, ignore_errors=True)
    # An explicit old-pip CONFIG signal from _run_resolve (D5).
    if run.returncode == 2 and run.stderr.startswith("CONFIG:"):
        return ResolveResult(target_id, ResolveOutcome.CONFIG, redact(run.stderr))
    outcome = classify_resolve(run.returncode, run.stderr)
    if outcome is ResolveOutcome.PASS:
        installed = _summarize_report(run.report_json)
        return ResolveResult(target_id, outcome, installed)
    return ResolveResult(target_id, outcome, redact(run.stderr.strip()))


def _summarize_report(report_json: str | None) -> str:
    if not report_json:
        return "resolved (empty install set)"
    try:
        doc = json.loads(report_json)
    except json.JSONDecodeError:
        return "resolved"
    names = [
        entry.get("metadata", {}).get("name", "?") for entry in doc.get("install", [])
    ]
    return f"resolved {len(names)} distribution(s)"


def resolve_environment(manifest: Manifest, env: Environment) -> ResolveResult:
    """Resolve one declared environment; a bad manifest entry -> CONFIG (FR-005)."""
    try:
        requirements = assemble_requirements(manifest, env)
    except ConfigError as exc:
        return ResolveResult(env.id, ResolveOutcome.CONFIG, str(exc))
    return _resolve_reqs(env.id, requirements)


def resolve_cross_product(manifest: Manifest, cp: CrossProduct) -> ResolveResult:
    """Resolve one declared cross-product (union of its members)."""
    try:
        requirements = assemble_cross_product(manifest, cp)
    except ConfigError as exc:
        return ResolveResult(cp.id, ResolveOutcome.CONFIG, str(exc))
    return _resolve_reqs(cp.id, requirements)


# --------------------------------------------------------------------------- #
# PyPI fetch seam (freshness; stubbed in unit tests).
# --------------------------------------------------------------------------- #

_PYPI_JSON_URL = "https://pypi.org/pypi/{dist}/json"


def _fetch_pypi_json(dist: str) -> dict:
    """Fetch the PyPI JSON API body for ``dist`` (network; stubbed in tests)."""
    url = _PYPI_JSON_URL.format(dist=dist)
    try:
        with urlopen(url, timeout=30) as resp:  # noqa: S310 (https literal)
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, OSError, json.JSONDecodeError) as exc:
        raise InfraError(f"PyPI fetch failed for {dist}: {exc}") from exc


# --------------------------------------------------------------------------- #
# Freshness reporting (US2). Advisory only: proposes, never applies (FR-008/12).
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Proposal:
    """An advisory freshness record for one governed pin (spec Key Entities).

    Carries the current pin specifier, the latest stable on PyPI, and the
    solve-proof result for SUBSTITUTING the proposed version (FR-009). It
    changes no pin and opens no PR (FR-008/FR-012).
    """

    dist: str
    env_id: str
    current: str
    latest_stable: str
    solve_outcome: ResolveOutcome
    solve_detail: str


# A pre-release / dev / rc / post local segment marker: any release whose
# version string carries one of these is not a "stable" target (FR-007).
_PRERELEASE_RE = re.compile(r"(a|b|rc|c|dev|alpha|beta|pre)\d*", re.IGNORECASE)


def _parse_version(version: str) -> tuple[int, ...] | None:
    """Parse a plain numeric release version into a comparable int tuple.

    stdlib-only (``packaging`` is not a guaranteed dependency), so ordering is
    NUMERIC, never lexical ("1.10" > "1.9"). Returns ``None`` for a version
    that is not a plain dotted-numeric release (a pre-release/dev/rc/local),
    which excludes it from the stable set (FR-007).
    """
    core = version.strip()
    # Reject anything carrying a pre-release/dev marker or a local segment.
    if "+" in core or _PRERELEASE_RE.search(core):
        return None
    parts: list[int] = []
    for token in core.split("."):
        if not token.isdigit():
            return None
        parts.append(int(token))
    return tuple(parts) if parts else None


def _release_is_yanked(files: object) -> bool:
    """A release is yanked ONLY when it has files and ALL of them are yanked
    (plan-review D5, PER-FILE). A release with no files is treated as not
    installable rather than yanked -- excluded from the stable set separately.
    """
    if not isinstance(files, list) or not files:
        return False
    return all(isinstance(f, dict) and f.get("yanked") for f in files)


def latest_stable(pypi_json: dict) -> str | None:
    """The highest non-yanked, non-pre-release version on PyPI (FR-007).

    ``pypi_json`` is the PyPI JSON API body (``releases`` maps version ->
    per-file list). Pre-release/dev/rc versions and FULLY-yanked releases are
    excluded. Ordering is numeric. Returns ``None`` when no stable release
    exists.
    """
    releases = pypi_json.get("releases", {})
    best: tuple[int, ...] | None = None
    best_str: str | None = None
    for version, files in releases.items():
        if not isinstance(files, list) or not files:
            continue
        if _release_is_yanked(files):
            continue
        parsed = _parse_version(str(version))
        if parsed is None:
            continue
        if best is None or parsed > best:
            best = parsed
            best_str = str(version)
    return best_str


# --------------------------------------------------------------------------- #
# Pin -> declared environment mapping + solve-proof (REPLACE semantics, D3).
# --------------------------------------------------------------------------- #


def _canonical(name: str) -> str:
    """PEP 503 canonical distribution name (lowercase, runs of -_. -> -)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _extra_requirements(project_path: Path, extra: str) -> list[str]:
    data = tomllib.loads(project_path.read_text(encoding="utf-8"))
    optional = data.get("project", {}).get("optional-dependencies", {})
    return [str(r) for r in optional.get(extra, [])]


def _base_requirements(project_path: Path) -> list[str]:
    """The [project].dependencies list -- governed pins can live HERE too
    (the orchestration project pins dagster in its base dependencies, not an
    extra; Codex review on PR #308)."""
    data = tomllib.loads(project_path.read_text(encoding="utf-8"))
    return [str(r) for r in data.get("project", {}).get("dependencies", [])]


def _requirement_dist(requirement: str) -> str:
    """The distribution name from a requirement string (drop the specifier)."""
    return re.split(r"[<>=!~ \[]", requirement.strip(), maxsplit=1)[0]


@dataclass(frozen=True)
class PinLocation:
    """Where a governed pin is declared: its environment, extra, the current
    requirement specifier, and the distribution name -- bundled so the
    solve-proof does not thread five positional arguments."""

    env: Environment
    extra: str | None  # None = pinned in the base [project].dependencies
    specifier: str
    dist: str


def _pin_in_extra(
    manifest: Manifest, env: Environment, extra: str, target: str
) -> str | None:
    """The current specifier declaring ``target`` in one env/extra, or None."""
    project_path = manifest.root / env.pyproject
    for req in _extra_requirements(project_path, extra):
        if _canonical(_requirement_dist(req)) == target:
            return req
    return None


def _pin_in_base(manifest: Manifest, env: Environment, target: str) -> str | None:
    """The requirement string when ``env``'s BASE [project].dependencies pin
    ``target``, else None."""
    for req in _base_requirements(manifest.root / env.pyproject):
        if _canonical(_requirement_dist(req)) == target:
            return req
    return None


def _pin_in_environment(
    manifest: Manifest, env: Environment, dist: str, target: str
) -> PinLocation | None:
    """A PinLocation if ``env`` declares ``dist`` in its base dependencies or
    one of its extras, else None (base scanned first: that is where the
    orchestration project pins dagster)."""
    if not (manifest.root / env.pyproject).is_file():
        return None
    base = _pin_in_base(manifest, env, target)
    if base is not None:
        return PinLocation(env=env, extra=None, specifier=base, dist=dist)
    for extra in env.extras:
        specifier = _pin_in_extra(manifest, env, extra, target)
        if specifier is not None:
            return PinLocation(env=env, extra=extra, specifier=specifier, dist=dist)
    return None


def _find_pin_environment(manifest: Manifest, dist: str) -> PinLocation | None:
    """Find the declared environment/extra/specifier that declares ``dist`` as a
    governed pin. Built from the pyprojects, never hardcoded. Returns None if no
    declared environment references the distribution."""
    target = _canonical(dist)
    for env in manifest.environments:
        found = _pin_in_environment(manifest, env, dist, target)
        if found is not None:
            return found
    return None


def _declared_ceiling(specifier: str) -> str | None:
    """The declared upper-bound clause (``<X`` / ``<=X``) of a requirement
    specifier, if any -- so D3's ceiling short-circuit can name it."""
    match = re.search(r"<=?[^,;\s]+", specifier)
    return match.group(0) if match else None


def _violates_ceiling(proposed: str, ceiling: str) -> bool:
    """True if ``proposed`` violates a ``<X`` / ``<=X`` ceiling (numeric)."""
    inclusive = ceiling.startswith("<=")
    bound = ceiling.lstrip("<=")
    prop = _parse_version(proposed)
    limit = _parse_version(bound)
    if prop is None or limit is None:
        return False
    return prop > limit or (prop == limit and not inclusive)


def _substituted_requirements(
    manifest: Manifest, loc: PinLocation, proposed: str
) -> list[str]:
    """The affected environment's extra requirement list with the target pin's
    specifier REPLACED by ``dist==proposed`` (FR-009 substitution semantics).

    Read from the LOCAL pyproject (so it still reflects the PR's declared
    pins, D1) but assembled as an EXPLICIT requirement list rather than the
    ``<path>[extra]`` local install -- otherwise the local metadata would
    re-impose the current pin and every exact-pinned bump would trivially
    conflict against itself (the ADD-vs-REPLACE trap).
    """
    project_path = manifest.root / loc.env.pyproject
    target = _canonical(loc.dist)
    substitute = f"{loc.dist}=={proposed}"
    requirements = (
        _base_requirements(project_path)
        if loc.extra is None
        else _extra_requirements(project_path, loc.extra)
    )
    return [
        substitute if _canonical(_requirement_dist(req)) == target else req
        for req in requirements
    ]


def _solve_proof(
    manifest: Manifest, loc: PinLocation, proposed: str
) -> tuple[ResolveOutcome, str]:
    """Prove whether ``dist==proposed`` co-resolves in its declared environment.

    D3: ALWAYS substitutes the proposed version. If the pin's own DECLARED
    CEILING forbids the proposed version, records RESOLUTION naming that
    ceiling BY CONSTRUCTION (that is the actionable info -- what the owner
    would have to relax), rather than relying on a resolver round-trip that a
    lone ceiling would not reproduce. Otherwise runs the real resolve.
    """
    ceiling = _declared_ceiling(loc.specifier)
    if ceiling is not None and _violates_ceiling(proposed, ceiling):
        return (
            ResolveOutcome.RESOLUTION,
            f"proposed {loc.dist}=={proposed} exceeds the declared ceiling "
            f"'{ceiling}' in '{loc.specifier}' (owner would have to relax it)",
        )
    requirements = _substituted_requirements(manifest, loc, proposed)
    result = _resolve_reqs(f"{loc.env.id}+{loc.dist}=={proposed}", requirements)
    return result.outcome, result.detail


def propose_bumps(manifest: Manifest) -> list[Proposal]:
    """For each governed pin behind its latest stable, emit an advisory
    PROPOSAL carrying a solve-proof (FR-008/FR-009). Read-only: mutates no pin,
    opens no PR (FR-012). A pin at/above latest yields no proposal.
    """
    proposals = [
        proposal
        for pin in manifest.governed_pins
        if (proposal := _proposal_for(manifest, pin)) is not None
    ]
    return proposals


def _proposal_for(manifest: Manifest, pin: GovernedPin) -> Proposal | None:
    """One governed pin's proposal, or None if it is not declared anywhere, has
    no stable release, or is already at/above the latest stable."""
    loc = _find_pin_environment(manifest, pin.dist)
    if loc is None:
        return None
    latest = latest_stable(_fetch_pypi_json(pin.dist))
    if latest is None:
        return None
    current_ver = _extract_pinned_version(loc.specifier)
    if current_ver is not None and not _is_newer(latest, current_ver):
        return None
    outcome, detail = _solve_proof(manifest, loc, latest)
    return Proposal(
        dist=pin.dist,
        env_id=loc.env.id,
        current=current_ver if current_ver is not None else loc.specifier,
        latest_stable=latest,
        solve_outcome=outcome,
        solve_detail=detail,
    )


def _extract_pinned_version(specifier: str) -> str | None:
    """The version from an ``==X`` exact pin, else the floor from ``>=X``,
    else None -- enough to decide 'is latest newer than what we declare'."""
    exact = re.search(r"==\s*([^,;\s]+)", specifier)
    if exact:
        return exact.group(1)
    floor = re.search(r">=\s*([^,;\s]+)", specifier)
    if floor:
        return floor.group(1)
    return None


def _is_newer(candidate: str, baseline: str) -> bool:
    cand = _parse_version(candidate)
    base = _parse_version(baseline)
    if cand is None or base is None:
        return candidate != baseline
    return cand > base


def render_freshness_markdown(proposals: list[Proposal]) -> str:
    """Render the advisory freshness report as Markdown (FR-011).

    Every proposal is rendered, including one whose solve FAILED -- marked
    'does not resolve', never omitted or crashed (FR-010).
    """
    lines = ["# Dependency freshness proposals (advisory)", ""]
    lines.append(
        "Governed pins are NEVER auto-bumped. Each row PROPOSES a bump to the "
        "owner and records whether the proposed version co-resolves. No pin "
        "value was changed and no pull request was opened."
    )
    lines.append("")
    if not proposals:
        lines.append("All governed pins are at their latest stable. No proposal.")
        return "\n".join(lines) + "\n"
    lines.append(
        "| distribution | environment | current | latest stable | solve-proof |"
    )
    lines.append("|---|---|---|---|---|")
    for p in proposals:
        if p.solve_outcome is ResolveOutcome.PASS:
            proof = "proposed, resolves"
        elif p.solve_outcome is ResolveOutcome.RESOLUTION:
            proof = f"proposed, does not resolve ({redact(p.solve_detail)})"
        else:
            proof = f"proposed, {p.solve_outcome.value} ({redact(p.solve_detail)})"
        lines.append(
            f"| {p.dist} | {p.env_id} | {p.current} | {p.latest_stable} | {proof} |"
        )
    return "\n".join(lines) + "\n"


def render_freshness_json(proposals: list[Proposal]) -> str:
    return json.dumps(
        {
            "proposals": [
                {
                    "dist": p.dist,
                    "environment": p.env_id,
                    "current": p.current,
                    "latest_stable": p.latest_stable,
                    "solve_outcome": p.solve_outcome.value,
                    "solve_detail": redact(p.solve_detail),
                }
                for p in proposals
            ]
        },
        indent=2,
    )


def _print_result(result: ResolveResult) -> None:
    if result.outcome is ResolveOutcome.PASS:
        print(f"[PASS] {result.target_id}: {result.detail}")
    else:
        label = result.outcome.value.upper()
        print(f"[{label}] {result.target_id}: {result.detail}")


def _exit_code_for(results: list[ResolveResult]) -> int:
    """Fail closed with a DISTINCT exit code per outcome (FR-003/FR-004/FR-005,
    SC-004). Precedence: a real conflict is never masked by a co-occurring
    lesser signal, so RESOLUTION > CONFIG > INFRA > OK.

    - any RESOLUTION -> EXIT_RESOLUTION (a real conflict wins over everything)
    - else any CONFIG -> EXIT_CONFIG (bad manifest; fails closed, own code so
      it is distinguishable from both RESOLUTION and INFRA)
    - else any INFRA -> EXIT_INFRA (the one retryable/annotatable case)
    - else EXIT_OK
    """
    outcomes = {r.outcome for r in results}
    if ResolveOutcome.RESOLUTION in outcomes:
        return EXIT_RESOLUTION
    if ResolveOutcome.CONFIG in outcomes:
        return EXIT_CONFIG
    if ResolveOutcome.INFRA in outcomes:
        return EXIT_INFRA
    return EXIT_OK


def run_check(manifest_path: Path) -> int:
    """The fail-closed co-resolution gate (T013, FR-006).

    Loads the manifest, resolves every declared environment and cross-product
    in an ephemeral venv, prints one line per target, and returns a distinct
    exit code by the worst outcome seen (a real conflict is never masked by a
    co-occurring network blip).
    """
    manifest = load_manifest(manifest_path)
    results: list[ResolveResult] = []
    for env in manifest.environments:
        result = resolve_environment(manifest, env)
        results.append(result)
        _print_result(result)
    for cp in manifest.cross_products:
        result = resolve_cross_product(manifest, cp)
        results.append(result)
        _print_result(result)
    code = _exit_code_for(results)
    labels = {
        EXIT_OK: "ok",
        EXIT_RESOLUTION: "conflict",
        EXIT_CONFIG: "config",
        EXIT_INFRA: "infra-only",
    }
    print(
        f"\n{len(results)} target(s) resolved; exit {code} "
        f"({labels.get(code, 'unknown')})"
    )
    return code


def run_freshness(manifest_path: Path, out: str | None) -> int:
    """The advisory freshness reporter (T022, FR-011).

    Writes a JSON report to ``out`` (default ``freshness-report.json``) and a
    sibling Markdown report. Read-only over pyproject files; opens no PR
    (FR-008/FR-012). Never a merge-blocking verdict -- it always returns
    EXIT_OK; a non-resolving proposal is rendered, not a failure.
    """
    manifest = load_manifest(manifest_path)
    proposals = propose_bumps(manifest)
    out_json = Path(out) if out else (_REPO_ROOT / "freshness-report.json")
    out_md = out_json.with_suffix(".md")
    out_json.write_text(render_freshness_json(proposals), encoding="utf-8")
    out_md.write_text(render_freshness_markdown(proposals), encoding="utf-8")
    print(f"freshness report written: {out_json} (+ {out_md.name})")
    print(f"{len(proposals)} proposal(s); no pin changed, no PR opened")
    return EXIT_OK


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run the gate")
    parser.add_argument("--freshness", action="store_true", help="run the reporter")
    parser.add_argument(
        "--manifest", default=str(_REPO_ROOT / "dependency-environments.yaml")
    )
    parser.add_argument("--out", default=None, help="freshness report output path")
    args = parser.parse_args(argv)
    if args.check:
        return run_check(Path(args.manifest))
    if args.freshness:
        return run_freshness(Path(args.manifest), args.out)
    parser.error("one of --check or --freshness is required")
    return EXIT_RESOLUTION


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main(sys.argv[1:]))
