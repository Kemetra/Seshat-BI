"""The curated analytics-stack catalog -- the ONE source of profile membership.

Everything that may be installed is declared here: its profile, its version
channel, its source type, and the allowlisted official source it comes from.
The argparse `--profile` choices, the installer, the docs table, and the tests
all READ this module. Nothing re-types a membership list, because a second copy
is how a profile silently loses a component (or gains an ungoverned one).

Three rules govern what may be added:

* a clear analytical role,
* an allowlisted official source, and
* a defined version channel.

`Channel` is the honesty axis. `stable` is an official non-draft, non-prerelease
release. `preview` is officially distributed but pre-GA. `rolling` means upstream
publishes no usable release or tag, so Seshat records an exact commit snapshot --
it is NEVER relabelled `stable`. `bundled` ships with Seshat and is validated
locally rather than downloaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath

INTEGRATIONS_DIR = Path(".seshat/integrations")
MCP_CONFIG = INTEGRATIONS_DIR / "mcp.json"
LOCK_FILE = INTEGRATIONS_DIR / "lock.json"
SKILLS_DIR = INTEGRATIONS_DIR / "skills"
# `env` rather than `environments`: this path is a prefix of every installed
# package's path, and Windows caps a full path at 260 characters (a hard repo
# rule). Thirteen characters saved here are thirteen more available to
# `Lib/site-packages/<deep>/<nested>/<module>.py`.
ENV_DIR = INTEGRATIONS_DIR / "env"
NODE_DIR = INTEGRATIONS_DIR / "node"
STAGING_DIR = INTEGRATIONS_DIR / "staging"

DAGSTER_PROJECT = Path("orchestration/dagster")


class Channel(str, Enum):
    """How mature the pinned coordinate is. Never cosmetic."""

    STABLE = "stable"
    PREVIEW = "preview"
    ROLLING = "rolling"
    BUNDLED = "bundled"


class SourceType(str, Enum):
    PYPI = "pypi"
    GITHUB = "github"
    NPM = "npm"
    BUNDLED = "bundled"


CLAUDE_CODE = "claude-code"
CODEX = "codex"
SUPPORTED_HARNESSES = (CLAUDE_CODE, CODEX)


@dataclass(frozen=True)
class SkillTarget:
    """One upstream skill identity a supported harness must expose."""

    name: str
    source_path: str
    plugin_id: str | None = None


@dataclass(frozen=True)
class McpSurfacePolicy:
    """One MCP surface a native plugin is allowed to activate."""

    name: str
    transport: str
    package: str | None = None
    required_args: tuple[str, ...] = ()
    forbidden_args: tuple[str, ...] = ()
    forbid_moving_coordinate: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("MCP surface name is blank")
        if self.transport not in {"stdio", "http", "sse"}:
            raise ValueError(f"unsupported MCP transport: {self.transport!r}")
        if self.package is not None and not self.package.strip():
            raise ValueError(f"{self.name}: MCP package is blank")
        _validate_unique_strings(self.name, "required MCP argument", self.required_args)
        _validate_unique_strings(
            self.name, "forbidden MCP argument", self.forbidden_args
        )
        overlap = set(self.required_args) & set(self.forbidden_args)
        if overlap:
            raise ValueError(
                f"{self.name}: MCP arguments cannot be both required and forbidden: "
                f"{sorted(overlap)!r}"
            )


@dataclass(frozen=True)
class NativePluginPolicy:
    """The complete reviewed capability surface of one native plugin."""

    plugin_id: str
    manifest_path: str
    manifest_name: str
    allowed_skills: tuple[str, ...]
    allowed_mcp_servers: tuple[McpSurfacePolicy, ...] = ()
    allowed_agents: tuple[str, ...] = ()
    allowed_hooks: tuple[str, ...] = ()
    incompatible_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.plugin_id.strip():
            raise ValueError("native plugin id is blank")
        if not self.manifest_name.strip():
            raise ValueError(f"{self.plugin_id}: manifest name is blank")
        _validate_relative_path(
            self.plugin_id, self.manifest_path, label="plugin manifest path"
        )
        _validate_unique_strings(self.plugin_id, "allowed skill", self.allowed_skills)
        _validate_unique_strings(self.plugin_id, "allowed agent", self.allowed_agents)
        _validate_unique_strings(self.plugin_id, "allowed hook", self.allowed_hooks)
        _validate_unique_strings(
            self.plugin_id,
            "incompatible capability",
            self.incompatible_capabilities,
        )
        mcp_names = tuple(server.name for server in self.allowed_mcp_servers)
        _validate_unique_strings(self.plugin_id, "allowed MCP server", mcp_names)
        allowed = (
            set(self.allowed_skills)
            | set(mcp_names)
            | set(self.allowed_agents)
            | set(self.allowed_hooks)
        )
        overlap = allowed & set(self.incompatible_capabilities)
        if overlap:
            raise ValueError(
                f"{self.plugin_id}: capabilities cannot be both allowed and "
                f"incompatible: {sorted(overlap)!r}"
            )


@dataclass(frozen=True)
class SkillActivation:
    """Catalog-owned discovery contract for one official package and harness."""

    harness: str
    mechanism: str
    targets: tuple[SkillTarget, ...]
    install_hint: str
    native_plugins: tuple[NativePluginPolicy, ...] = ()


# Allowlisted official sources. A component may name only a source declared
# here; an arbitrary URL is not installable by construction.
ALLOWLISTED_SOURCES: dict[str, str] = {
    "pypi": "https://pypi.org",
    "github-microsoft-fabric": "https://github.com/microsoft/skills-for-fabric",
    "github-dbt-labs-skills": "https://github.com/dbt-labs/dbt-agent-skills",
    "github-dagster-skills": "https://github.com/dagster-io/skills",
    "npm-microsoft": "https://registry.npmjs.org",
    "seshat-bundled": "seshat",
}


@dataclass(frozen=True)
class Component:
    """One installable member of the curated stack.

    `channel` is the DECLARED maturity ceiling: a `stable` component refuses a
    pre-release, and a `preview` one is allowed to resolve one but stays
    labelled `preview`. `mode` carries an installation posture the operator must
    be able to see -- the Power BI MCP's `readonly` is the reason it exists.
    """

    id: str
    source_type: SourceType
    source: str
    channel: Channel
    role: str
    # PyPI distribution name, GitHub "owner/repo", or npm package name.
    coordinate: str = ""
    mode: str | None = None
    # A component whose pinned version must agree with another's (the dbt pair).
    compat_group: str | None = None
    # Whether this component ALSO registers an MCP server. Independent of
    # `source_type` on purpose: `dbt-mcp` is distributed on PyPI but launched
    # through `uvx` as an MCP server, so inferring registration from the source
    # type would silently skip writing its config -- and skip the conflict and
    # exact-version checks that go with it.
    mcp_server: bool = False
    # Files that must exist inside an installed upstream payload. This belongs
    # to the catalog because it is component identity/validation metadata, not
    # installer behavior. Empty for components whose installed state is proven
    # by package metadata, MCP registration, or a bundled repository path.
    required_paths: tuple[str, ...] = ()
    skill_activations: tuple[SkillActivation, ...] = ()

    def __post_init__(self) -> None:
        if self.source not in ALLOWLISTED_SOURCES:
            raise ValueError(f"{self.id}: source is not allowlisted: {self.source}")
        for required in self.required_paths:
            _validate_relative_path(self.id, required, label="required path")
        self._validate_skill_activations()

    def _validate_skill_activations(self) -> None:
        """Each declared harness appears once and names contained targets."""
        declared_harnesses: set[str] = set()
        for activation in self.skill_activations:
            if activation.harness not in SUPPORTED_HARNESSES:
                raise ValueError(
                    f"{self.id}: unsupported skill harness: {activation.harness!r}"
                )
            if activation.harness in declared_harnesses:
                raise ValueError(
                    f"{self.id}: duplicate skill harness: {activation.harness!r}"
                )
            declared_harnesses.add(activation.harness)
            self._validate_activation_targets(activation)

    def _validate_activation_targets(self, activation: SkillActivation) -> None:
        """Every target names a non-blank skill at a contained relative path."""
        if not activation.targets:
            raise ValueError(f"{self.id}: skill activation needs at least one target")
        for target in activation.targets:
            if not target.name.strip():
                raise ValueError(f"{self.id}: skill target name is blank")
            _validate_relative_path(
                self.id, target.source_path, label="skill source path"
            )
        plugin_ids = tuple(policy.plugin_id for policy in activation.native_plugins)
        _validate_unique_strings(self.id, "native plugin policy", plugin_ids)
        target_plugin_ids = {
            target.plugin_id for target in activation.targets if target.plugin_id
        }
        undeclared = target_plugin_ids - set(plugin_ids)
        if activation.mechanism == "native-plugin" and undeclared:
            raise ValueError(
                f"{self.id}: native plugin targets lack policy: {sorted(undeclared)!r}"
            )


def _validate_relative_path(component_id: str, value: str, *, label: str) -> None:
    """Refuse paths that can escape an installed upstream payload."""

    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        not value.strip()
        or "\\" in value
        or posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or ".." in posix.parts
    ):
        raise ValueError(
            f"{component_id}: {label} must be a contained relative POSIX path: "
            f"{value!r}"
        )


def _validate_unique_strings(owner: str, label: str, values: tuple[str, ...]) -> None:
    """Require non-blank, duplicate-free tuple members."""

    seen: set[str] = set()
    for value in values:
        if not value.strip():
            raise ValueError(f"{owner}: {label} is blank")
        if value in seen:
            raise ValueError(f"{owner}: duplicate {label}: {value!r}")
        seen.add(value)


# --------------------------------------------------------------------------- #
# Components, grouped by the profile that introduces them.
# --------------------------------------------------------------------------- #

_ANALYTICS_CORE = (
    Component(
        id="duckdb",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="in-process analytical SQL engine for local gold-layer inspection",
        coordinate="duckdb",
    ),
    Component(
        id="polars",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="columnar DataFrame engine for silver-layer transformation",
        coordinate="polars",
    ),
    Component(
        id="pyarrow",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="Arrow interchange between readers, Polars, and DuckDB",
        coordinate="pyarrow",
    ),
    Component(
        id="pandera",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="declarative dataframe schema validation for mapping checks",
        coordinate="pandera",
    ),
    Component(
        id="connectorx",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="fast source-database extraction into Arrow",
        coordinate="connectorx",
    ),
)

_TRANSFORMATION = (
    Component(
        id="dbt-core",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="governed shadow transformation engine",
        coordinate="dbt-core",
        compat_group="dbt",
    ),
    Component(
        id="dbt-postgres",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="Postgres adapter for the dbt engine",
        coordinate="dbt-postgres",
        compat_group="dbt",
    ),
    Component(
        id="dbt-agent-skills",
        source_type=SourceType.GITHUB,
        source="github-dbt-labs-skills",
        channel=Channel.STABLE,
        role="upstream dbt Labs agent skill bundle",
        coordinate="dbt-labs/dbt-agent-skills",
        required_paths=(
            "skills/dbt/skills/using-dbt-for-analytics-engineering/SKILL.md",
            "skills/dbt/skills/configuring-dbt-mcp-server/SKILL.md",
        ),
        skill_activations=(
            SkillActivation(
                harness=CLAUDE_CODE,
                mechanism="native-plugin",
                targets=(
                    SkillTarget(
                        name="using-dbt-for-analytics-engineering",
                        source_path=(
                            "skills/dbt/skills/"
                            "using-dbt-for-analytics-engineering/SKILL.md"
                        ),
                        plugin_id="dbt@dbt-agent-marketplace",
                    ),
                    SkillTarget(
                        name="configuring-dbt-mcp-server",
                        source_path=(
                            "skills/dbt/skills/configuring-dbt-mcp-server/SKILL.md"
                        ),
                        plugin_id="dbt@dbt-agent-marketplace",
                    ),
                ),
                native_plugins=(
                    NativePluginPolicy(
                        plugin_id="dbt@dbt-agent-marketplace",
                        manifest_path=".claude-plugin/marketplace.json",
                        manifest_name="dbt",
                        allowed_skills=(
                            "using-dbt-for-analytics-engineering",
                            "configuring-dbt-mcp-server",
                        ),
                    ),
                ),
                install_hint=(
                    "/plugin marketplace add dbt-labs/dbt-agent-skills; "
                    "/plugin install dbt@dbt-agent-marketplace"
                ),
            ),
            SkillActivation(
                harness=CODEX,
                mechanism="agent-skills-projection",
                targets=(
                    SkillTarget(
                        name="using-dbt-for-analytics-engineering",
                        source_path=(
                            "skills/dbt/skills/"
                            "using-dbt-for-analytics-engineering/SKILL.md"
                        ),
                    ),
                    SkillTarget(
                        name="configuring-dbt-mcp-server",
                        source_path=(
                            "skills/dbt/skills/configuring-dbt-mcp-server/SKILL.md"
                        ),
                    ),
                ),
                install_hint=(
                    "link the locked upstream skill directories into "
                    "$CODEX_HOME/skills and start a new Codex session"
                ),
            ),
        ),
    ),
    Component(
        id="dbt-mcp",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="dbt MCP server, launched through uvx at an exact version",
        coordinate="dbt-mcp",
        # Resolved from PyPI (so the pin is a real, existing release) but
        # installed as an MCP registration rather than into a venv.
        mcp_server=True,
    ),
)

_ORCHESTRATION = (
    Component(
        id="dagster",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="orchestrator for the governed medallion sequence",
        coordinate="dagster",
        compat_group="dagster",
    ),
    Component(
        id="seshat-dagster-adapter",
        source_type=SourceType.BUNDLED,
        source="seshat-bundled",
        channel=Channel.BUNDLED,
        role="Seshat's own read-only Dagster gate adapter",
    ),
    Component(
        id="seshat-dagster-workflows",
        source_type=SourceType.BUNDLED,
        source="seshat-bundled",
        channel=Channel.BUNDLED,
        role="Seshat's bundled governed Dagster workflow router",
    ),
    Component(
        id="dagster-agent-skills",
        source_type=SourceType.GITHUB,
        source="github-dagster-skills",
        channel=Channel.STABLE,
        role="upstream Dagster agent skill bundle",
        coordinate="dagster-io/skills",
        required_paths=("skills/dagster-expert/skills/dagster-expert/SKILL.md",),
        skill_activations=(
            SkillActivation(
                harness=CLAUDE_CODE,
                mechanism="native-plugin",
                targets=(
                    SkillTarget(
                        name="dagster-expert",
                        source_path=(
                            "skills/dagster-expert/skills/dagster-expert/SKILL.md"
                        ),
                        plugin_id="dagster-expert@dagster",
                    ),
                ),
                native_plugins=(
                    NativePluginPolicy(
                        plugin_id="dagster-expert@dagster",
                        manifest_path=".claude-plugin/marketplace.json",
                        manifest_name="dagster-expert",
                        allowed_skills=("dagster-expert",),
                    ),
                ),
                install_hint=(
                    "/plugin marketplace add dagster-io/skills; "
                    "/plugin install dagster-expert@dagster"
                ),
            ),
            SkillActivation(
                harness=CODEX,
                mechanism="agent-skills-projection",
                targets=(
                    SkillTarget(
                        name="dagster-expert",
                        source_path=(
                            "skills/dagster-expert/skills/dagster-expert/SKILL.md"
                        ),
                    ),
                ),
                install_hint=(
                    "link the locked upstream skill directory into "
                    "$CODEX_HOME/skills and start a new Codex session"
                ),
            ),
        ),
    ),
)

_POWERBI_FABRIC = (
    Component(
        id="fabric-skills",
        source_type=SourceType.GITHUB,
        source="github-microsoft-fabric",
        channel=Channel.STABLE,
        role="upstream Microsoft Fabric and Power BI skill bundle",
        coordinate="microsoft/skills-for-fabric",
        required_paths=(
            "skills/semantic-model-authoring/SKILL.md",
            "plugins/powerbi-authoring/skills/powerbi-report-design/SKILL.md",
            "plugins/powerbi-authoring/skills/powerbi-report-authoring/SKILL.md",
        ),
        skill_activations=(
            SkillActivation(
                harness=CLAUDE_CODE,
                mechanism="native-plugin",
                targets=(
                    SkillTarget(
                        name="semantic-model-authoring",
                        source_path="skills/semantic-model-authoring/SKILL.md",
                        plugin_id="fabric-skills@fabric-collection",
                    ),
                    SkillTarget(
                        name="powerbi-report-design",
                        source_path=(
                            "plugins/powerbi-authoring/skills/"
                            "powerbi-report-design/SKILL.md"
                        ),
                        plugin_id="powerbi-authoring@fabric-collection",
                    ),
                    SkillTarget(
                        name="powerbi-report-authoring",
                        source_path=(
                            "plugins/powerbi-authoring/skills/"
                            "powerbi-report-authoring/SKILL.md"
                        ),
                        plugin_id="powerbi-authoring@fabric-collection",
                    ),
                ),
                native_plugins=(
                    NativePluginPolicy(
                        plugin_id="fabric-skills@fabric-collection",
                        manifest_path=".claude-plugin/marketplace.json",
                        manifest_name="fabric-skills",
                        allowed_skills=("semantic-model-authoring",),
                    ),
                    NativePluginPolicy(
                        plugin_id="powerbi-authoring@fabric-collection",
                        manifest_path=".claude-plugin/marketplace.json",
                        manifest_name="powerbi-authoring",
                        allowed_skills=(
                            "powerbi-report-design",
                            "powerbi-report-authoring",
                        ),
                        incompatible_capabilities=(
                            "powerbi-report-planning",
                            "powerbi-report-management",
                            "semantic-model-authoring",
                            "powerbi-modeling-mcp",
                        ),
                    ),
                ),
                install_hint=(
                    "/plugin marketplace add microsoft/skills-for-fabric; "
                    "/plugin install fabric-skills@fabric-collection; "
                    "/plugin install powerbi-authoring@fabric-collection"
                ),
            ),
            SkillActivation(
                harness=CODEX,
                mechanism="agent-skills-projection",
                targets=(
                    SkillTarget(
                        name="semantic-model-authoring",
                        source_path="skills/semantic-model-authoring/SKILL.md",
                    ),
                    SkillTarget(
                        name="powerbi-report-design",
                        source_path=(
                            "plugins/powerbi-authoring/skills/"
                            "powerbi-report-design/SKILL.md"
                        ),
                    ),
                    SkillTarget(
                        name="powerbi-report-authoring",
                        source_path=(
                            "plugins/powerbi-authoring/skills/"
                            "powerbi-report-authoring/SKILL.md"
                        ),
                    ),
                ),
                install_hint=(
                    "link the locked upstream skill directories into "
                    "$CODEX_HOME/skills and start a new Codex session"
                ),
            ),
        ),
    ),
    Component(
        id="powerbi-modeling-mcp",
        source_type=SourceType.NPM,
        source="npm-microsoft",
        # Pre-GA upstream. Recorded as `preview` and shown as `preview`; the
        # read-only mode below is not a substitute for saying so.
        channel=Channel.PREVIEW,
        role="Power BI semantic-model MCP server, read-only",
        coordinate="@microsoft/powerbi-modeling-mcp",
        mode="readonly",
        mcp_server=True,
    ),
)

_REPORTING = (
    Component(
        id="jinja2",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="template rendering for governed report and evidence output",
        coordinate="jinja2",
    ),
    Component(
        id="xlsxwriter",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="Excel workbook output for consumer hand-offs",
        coordinate="xlsxwriter",
    ),
    Component(
        id="playwright",
        source_type=SourceType.PYPI,
        source="pypi",
        channel=Channel.STABLE,
        role="headless capture for report screenshot QA",
        coordinate="playwright",
    ),
)


# --------------------------------------------------------------------------- #
# Profiles. `analytics-full` is DERIVED, never hand-listed.
# --------------------------------------------------------------------------- #

ANALYTICS_FULL = "analytics-full"

# Insertion order is the resolution and rendering order, and it is the order
# `analytics-full` unions in. Declared as a tuple of pairs rather than relying
# on dict ordering being incidental -- the determinism is the contract.
_BASE_PROFILES: tuple[tuple[str, tuple[Component, ...]], ...] = (
    ("analytics-core", _ANALYTICS_CORE),
    ("transformation", _TRANSFORMATION),
    ("orchestration", _ORCHESTRATION),
    ("powerbi-fabric", _POWERBI_FABRIC),
    ("reporting", _REPORTING),
)


def _union(
    profiles: tuple[tuple[str, tuple[Component, ...]], ...],
) -> tuple[Component, ...]:
    """Every component once, in declaration order.

    Ordered dedupe on `id`, NOT `set()`: a set would make the plan order --
    and therefore the rendered output and the lock file's key order -- vary
    between runs.
    """
    seen: set[str] = set()
    merged: list[Component] = []
    for _name, components in profiles:
        for component in components:
            if component.id in seen:
                continue
            seen.add(component.id)
            merged.append(component)
    return tuple(merged)


PROFILES: dict[str, tuple[Component, ...]] = {
    **{name: components for name, components in _BASE_PROFILES},
    ANALYTICS_FULL: _union(_BASE_PROFILES),
}

DEFAULT_PROFILE = ANALYTICS_FULL

# The argparse choices are DERIVED. A profile added above is reachable from the
# CLI with no second edit -- §5's "keep profile definitions in one catalog
# source" applied to the parser too.
PROFILE_NAMES: tuple[str, ...] = tuple(PROFILES)


class UnknownProfile(KeyError):
    """A profile name that is not in the catalog."""


def profile_components(profile: str) -> tuple[Component, ...]:
    """The components of `profile`, in deterministic order."""
    try:
        return PROFILES[profile]
    except KeyError as exc:
        known = ", ".join(PROFILE_NAMES)
        raise UnknownProfile(f"unknown profile {profile!r}; known: {known}") from exc


LEGACY_COMPONENT_IDS: dict[str, str] = {
    "dagster-skills": "seshat-dagster-workflows",
}


def component(component_id: str) -> Component:
    """One component by id, across every profile."""
    resolved_id = LEGACY_COMPONENT_IDS.get(component_id, component_id)
    for candidate in PROFILES[ANALYTICS_FULL]:
        if candidate.id == resolved_id:
            return candidate
    raise KeyError(component_id)


def profiles_for(component_id: str) -> tuple[str, ...]:
    """The base profiles that introduce `component_id` (excluding the union)."""
    return tuple(
        name
        for name, components in _BASE_PROFILES
        if any(item.id == component_id for item in components)
    )
