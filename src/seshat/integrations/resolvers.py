"""Turning a catalog entry into an exact, immovable coordinate.

Every remote lookup sits behind a Protocol. The installer takes the protocols as
parameters, so a unit test supplies a fake and NOTHING here contacts a network;
the live implementations at the bottom are the only code that opens a socket, and
they are never constructed by default.

The one rule the whole module serves: an active configuration must never carry a
moving reference. Not `@latest`, not an unversioned `uvx` package, not an
unpinned Git default branch. A resolver either produces an exact
version/tag/commit or it REFUSES with a categorical reason -- it never falls back
to something that floats.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from seshat.integrations.catalog import Channel, Component, SourceType
from seshat.integrations.versions import (
    artifact_sha256,
    is_prerelease,
    latest_compatible,
    latest_stable,
)

# Only these hosts are ever contacted, and only over https.
PYPI_JSON_URL = "https://pypi.org/pypi/{dist}/json"
GITHUB_API = "https://api.github.com"
NPM_REGISTRY_URL = "https://registry.npmjs.org/{package}"

_TIMEOUT = 30


# --------------------------------------------------------------------------- #
# Outcomes. Categorical, with an actionable reason.
# --------------------------------------------------------------------------- #

# `unavailable` = upstream has nothing usable; `incompatible` = it has something
# but not for this environment; `conflict` = two components disagree; `failed` =
# the lookup itself broke. Each says something different to the operator, so
# none of them collapse into a generic error.
UNAVAILABLE = "unavailable"
INCOMPATIBLE = "incompatible"
CONFLICT = "conflict"
FAILED = "failed"


@dataclass(frozen=True)
class Resolution:
    """An exact coordinate, or a refusal carrying a reason.

    `ok` is not derived from `version` being truthy: a `rolling` component
    resolves a commit and no version, and conflating the two would let an
    empty-but-ok resolution through.
    """

    component_id: str
    ok: bool
    channel: Channel | None = None
    version: str | None = None
    tag: str | None = None
    commit: str | None = None
    sha256: str | None = None
    signature_verified: bool | None = None
    status: str = ""
    reason: str = ""

    @property
    def pinned(self) -> str:
        """The exact coordinate, for display and for generated commands."""
        return self.version or self.tag or (self.commit or "")[:12]


def _refuse(component_id: str, status: str, reason: str) -> Resolution:
    return Resolution(component_id=component_id, ok=False, status=status, reason=reason)


# --------------------------------------------------------------------------- #
# Injectable interfaces.
# --------------------------------------------------------------------------- #


class PypiIndex(Protocol):
    """The PyPI JSON API, reduced to what resolution needs."""

    def project(self, dist: str) -> dict:
        """The project JSON body for `dist`."""
        ...


class GitHubIndex(Protocol):
    """The GitHub releases/refs API, reduced to what resolution needs."""

    def latest_release(self, repo: str) -> dict | None:
        """The newest non-draft, non-prerelease release, or None if there is none."""
        ...

    def commit_for_ref(self, repo: str, ref: str) -> dict | None:
        """The commit a tag or branch points at, with verification metadata."""
        ...

    def default_branch(self, repo: str) -> str:
        """The repository's default branch name."""
        ...


class NpmRegistry(Protocol):
    """The npm registry, reduced to what resolution needs."""

    def package(self, name: str) -> dict:
        """The packument for `name` (`dist-tags` plus `versions`)."""
        ...


def running_python() -> tuple[int, ...]:
    return sys.version_info[:2]


# --------------------------------------------------------------------------- #
# PyPI.
# --------------------------------------------------------------------------- #


def resolve_pypi(
    item: Component,
    index: PypiIndex,
    *,
    python_version: tuple[int, ...] | None = None,
) -> Resolution:
    """Resolve a PyPI distribution to an exact version plus artifact digest.

    Prereleases are excluded unless the catalog declares the component
    `preview`; yanked releases are always excluded; and a release whose
    `requires-python` rejects the running interpreter is skipped in favour of
    the newest one that accepts it -- compatibility beats recency. When nothing
    is both stable and compatible the answer is a refusal, never a guess.
    """
    python_version = python_version or running_python()
    try:
        body = index.project(item.coordinate)
    except Exception as exc:  # noqa: BLE001 - any lookup failure is `failed`
        return _refuse(item.id, FAILED, f"PyPI lookup failed: {exc}")

    allow_preview = item.channel is Channel.PREVIEW
    version = latest_compatible(body, python_version=python_version)
    if version is None:
        stable = latest_stable(body)
        if stable is not None:
            # Something stable exists, but not for this interpreter. That is a
            # different fact from "nothing is published", so it gets its own
            # status and names the version it rejected.
            return _refuse(
                item.id,
                INCOMPATIBLE,
                f"no release of {item.coordinate} supports Python "
                f"{'.'.join(str(part) for part in python_version)} "
                f"(latest stable {stable} declares an incompatible "
                f"requires-python)",
            )
        if allow_preview:
            return _refuse(
                item.id,
                UNAVAILABLE,
                f"{item.coordinate} publishes no usable release",
            )
        return _refuse(
            item.id,
            UNAVAILABLE,
            f"{item.coordinate} has no stable, non-yanked release; "
            "prereleases are not installed for a stable component",
        )

    files = body.get("releases", {}).get(version)
    return Resolution(
        component_id=item.id,
        ok=True,
        channel=item.channel,
        version=version,
        sha256=artifact_sha256(files),
        status="resolved",
    )


# --------------------------------------------------------------------------- #
# GitHub.
# --------------------------------------------------------------------------- #


def resolve_github(item: Component, index: GitHubIndex) -> Resolution:
    """Resolve a GitHub skill bundle to an exact tag+commit, or a rolling commit.

    A released repository is pinned to its newest non-draft, non-prerelease tag
    AND the commit that tag resolves to. A repository with no usable release is
    pinned to one exact commit and classified `rolling` -- never `stable`, and
    never left on an unpinned default branch, which is the reference that would
    move under the operator.
    """
    try:
        release = index.latest_release(item.coordinate)
    except Exception as exc:  # noqa: BLE001
        return _refuse(item.id, FAILED, f"GitHub release lookup failed: {exc}")

    if release:
        tag = str(release.get("tag_name") or "").strip()
        if not tag:
            return _refuse(item.id, FAILED, "release carries no tag_name")
        commit = _commit(item, index, tag)
        if isinstance(commit, Resolution):
            return commit
        sha, verified = commit
        return Resolution(
            component_id=item.id,
            ok=True,
            channel=item.channel,
            tag=tag,
            commit=sha,
            signature_verified=verified,
            status="resolved",
        )

    # No usable release: snapshot the default branch's current commit and say
    # plainly that this is a rolling pin.
    try:
        branch = index.default_branch(item.coordinate)
    except Exception as exc:  # noqa: BLE001
        return _refuse(item.id, FAILED, f"GitHub branch lookup failed: {exc}")
    commit = _commit(item, index, branch)
    if isinstance(commit, Resolution):
        return commit
    sha, verified = commit
    return Resolution(
        component_id=item.id,
        ok=True,
        # The catalog may declare `stable`; upstream reality overrides the
        # declaration downward. A rolling commit is never reported as stable.
        channel=Channel.ROLLING,
        commit=sha,
        signature_verified=verified,
        status="resolved",
        reason=(
            f"{item.coordinate} publishes no release or tag; pinned to an exact "
            f"commit on {branch} and classified rolling"
        ),
    )


def _commit(
    item: Component, index: GitHubIndex, ref: str
) -> tuple[str, bool | None] | Resolution:
    try:
        payload = index.commit_for_ref(item.coordinate, ref)
    except Exception as exc:  # noqa: BLE001
        return _refuse(item.id, FAILED, f"GitHub commit lookup failed: {exc}")
    if not payload:
        return _refuse(item.id, UNAVAILABLE, f"ref {ref} does not resolve to a commit")
    sha = str(payload.get("sha") or "").strip()
    if not sha:
        return _refuse(item.id, FAILED, f"ref {ref} resolved without a commit sha")
    return sha, _verified(payload)


def _verified(payload: dict) -> bool | None:
    """Whether GitHub reports the commit's signature as verified.

    None when GitHub says nothing -- recorded as null rather than as `false`,
    because "not reported" and "reported unverified" are different claims.
    """
    verification = payload.get("verification")
    if isinstance(verification, dict) and "verified" in verification:
        return bool(verification["verified"])
    commit = payload.get("commit")
    if isinstance(commit, dict):
        nested = commit.get("verification")
        if isinstance(nested, dict) and "verified" in nested:
            return bool(nested["verified"])
    return None


# --------------------------------------------------------------------------- #
# npm.
# --------------------------------------------------------------------------- #


def resolve_npm(item: Component, registry: NpmRegistry) -> Resolution:
    """Resolve an npm package's stable dist-tag to an exact semantic version.

    The resolved version is what gets written into generated commands, so
    `@latest` never survives into an active configuration. The component's
    declared maturity is retained: resolving the Power BI MCP to an exact
    version does not promote it out of `preview`.
    """
    try:
        body = registry.package(item.coordinate)
    except Exception as exc:  # noqa: BLE001
        return _refuse(item.id, FAILED, f"npm lookup failed: {exc}")

    tags = body.get("dist-tags")
    version = ""
    if isinstance(tags, dict):
        version = str(tags.get("latest") or "").strip()
    if not version:
        return _refuse(
            item.id, UNAVAILABLE, f"{item.coordinate} publishes no stable dist-tag"
        )
    if item.channel is not Channel.PREVIEW and is_prerelease(version):
        return _refuse(
            item.id,
            UNAVAILABLE,
            f"{item.coordinate}@{version} is a prerelease; not installed for a "
            "stable component",
        )
    # `sha256` stays None on purpose: npm publishes a sha512 `dist.integrity`,
    # and recording that under a sha256 field would mislabel the digest. The lock
    # carries null rather than a wrong algorithm.
    return Resolution(
        component_id=item.id,
        ok=True,
        channel=item.channel,
        version=version,
        sha256=None,
        status="resolved",
    )


# --------------------------------------------------------------------------- #
# Dispatch.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Resolvers:
    """The three injectable indexes, bundled.

    All three default to None so a caller must OPT IN to a network resolver. A
    plan that forgot to pass one gets a refusal, not a silent live lookup.
    """

    pypi: PypiIndex | None = None
    github: GitHubIndex | None = None
    npm: NpmRegistry | None = None
    python_version: tuple[int, ...] | None = None


# Per source type: the `Resolvers` field holding its index, the label used when
# that index was not injected, and how to call the matching resolver.
_INDEXES: dict[
    SourceType, tuple[str, str, Callable[[Component, Resolvers], Resolution]]
]
_INDEXES = {
    SourceType.PYPI: (
        "pypi",
        "PyPI",
        lambda item, rs: resolve_pypi(item, rs.pypi, python_version=rs.python_version),
    ),
    SourceType.GITHUB: (
        "github",
        "GitHub",
        lambda item, rs: resolve_github(item, rs.github),
    ),
    SourceType.NPM: ("npm", "npm", lambda item, rs: resolve_npm(item, rs.npm)),
}


def resolve(item: Component, resolvers: Resolvers) -> Resolution:
    """Resolve one component through the matching injected index."""
    if item.source_type is SourceType.BUNDLED:
        return Resolution(
            component_id=item.id,
            ok=True,
            channel=Channel.BUNDLED,
            status="resolved",
            reason="ships with Seshat; validated locally, never downloaded",
        )
    index = _INDEXES.get(item.source_type)
    if index is None:
        return _refuse(item.id, FAILED, f"unsupported source type: {item.source_type}")
    field_name, label, resolver = index
    if getattr(resolvers, field_name) is None:
        return _refuse(item.id, UNAVAILABLE, f"no {label} resolver was provided")
    return resolver(item, resolvers)


# --------------------------------------------------------------------------- #
# The live implementations. Constructed ONLY on an explicit `--refresh`.
# --------------------------------------------------------------------------- #


def _get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json"})  # noqa: S310
    if not url.startswith("https://"):  # pragma: no cover - constants are https
        raise ValueError(f"refusing a non-https URL: {url}")
    with urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


class LivePypi:
    """The real PyPI JSON API."""

    def project(self, dist: str) -> dict:
        return _get_json(PYPI_JSON_URL.format(dist=dist))


class LiveGitHub:
    """The real GitHub API, over public read-only endpoints."""

    def latest_release(self, repo: str) -> dict | None:
        try:
            body = _get_json(f"{GITHUB_API}/repos/{repo}/releases/latest")
        except HTTPError as exc:
            if exc.code == 404:  # no releases published at all
                return None
            raise
        except URLError:
            raise
        if body.get("draft") or body.get("prerelease"):
            return None
        return body

    def commit_for_ref(self, repo: str, ref: str) -> dict | None:
        try:
            return _get_json(f"{GITHUB_API}/repos/{repo}/commits/{ref}")
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def default_branch(self, repo: str) -> str:
        body = _get_json(f"{GITHUB_API}/repos/{repo}")
        return str(body.get("default_branch") or "main")


class LiveNpm:
    """The real npm registry."""

    def package(self, name: str) -> dict:
        return _get_json(NPM_REGISTRY_URL.format(package=name))


def live_resolvers() -> Resolvers:
    """The network-backed resolvers. Built only behind an explicit `--refresh`."""
    return Resolvers(pypi=LivePypi(), github=LiveGitHub(), npm=LiveNpm())
