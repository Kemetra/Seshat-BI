"""Drift gates for the canonical public command surface.

``distribution/public-command-surface.yaml`` is the single authority for what
the generated agent bundles advertise (commands, deprecated command aliases,
and bundled skills). These tests fail closed whenever any of the participating
surfaces drift from it: wrapper templates, the public-knowledge allowlist, the
generated Claude/Codex bundles, the router skill, the ``help`` command map,
active install documentation, and the CLI ``_DISPATCH`` table a command claims
to drive.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

from seshat import capability_feeders as feeders

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_BUNDLE = ROOT / "integrations" / "claude-code" / "seshat-bi"
CODEX_BUNDLE = ROOT / "integrations" / "codex" / "seshat-bi"
BUNDLE_ROOTS = {"claude": CLAUDE_BUNDLE, "codex": CODEX_BUNDLE}
COMMAND_TEMPLATE_DIR = (
    ROOT / "distribution" / "bundle-templates" / "claude" / "commands"
)

_STATUSES = {"shipped", "deferred", "internal"}
_MODES = {"read-only", "mutating"}
_COMMAND_FIELDS = {
    "name",
    "platform",
    "intent",
    "cli_verbs",
    "skill",
    "wrapper_template",
    "bundle_destination",
    "mode",
    "gates",
    "documentation",
    "status",
}
_ALIAS_FIELDS = {"name", "alias_of", "wrapper_template", "bundle_destination", "status"}
_SKILL_FIELDS = {
    "name",
    "platforms",
    "intent",
    "wrapper_template",
    "bundle_destination",
    "documentation",
    "status",
}
# Development-only path fragments that must never leak into a public bundle
# or a bundle template: an installed plugin has neither of these trees.
_DEVELOPMENT_PATHS = (".claude/skills/", "docs/powerbi/")
_NAME_TOKEN = re.compile(r"`((?:seshat|powerbi)-[a-z][a-z-]*)`")
_NAMESPACED = re.compile(r"/seshat-bi:([a-z0-9][a-z0-9-]*)")
_VERSION_PIN = re.compile(r"seshat-bi==(\d+\.\d+\.\d+)")


def _surface() -> dict:
    return yaml.safe_load(
        (ROOT / "distribution" / "public-command-surface.yaml").read_text(
            encoding="utf-8"
        )
    )


def _allowlist_targets() -> dict[str, dict[str, str]]:
    """``{source: {target: destination}}`` across both allowlist sections."""
    document = yaml.safe_load(
        (ROOT / "distribution" / "public-knowledge-allowlist.yaml").read_text(
            encoding="utf-8"
        )
    )
    mapping: dict[str, dict[str, str]] = {}
    for section in ("entries", "template_entries"):
        for entry in document.get(section, []):
            mapping[str(entry["source"])] = {
                str(target): str(dest) for target, dest in entry["targets"].items()
            }
    return mapping


def _shipped_commands(surface: dict) -> list[dict]:
    return [c for c in surface["commands"] if c["status"] == "shipped"]


def _shipped_aliases(surface: dict) -> list[dict]:
    return [a for a in surface.get("command_aliases", []) if a["status"] == "shipped"]


def _shipped_skills(surface: dict) -> list[dict]:
    return [s for s in surface["skills"] if s["status"] == "shipped"]


def _wrapper_body(template: Path) -> str:
    """The instruction body of a command template, after its frontmatter."""
    text = template.read_text(encoding="utf-8")
    assert text.startswith("---\n"), template
    return text.split("---", 2)[2].strip()


def _pyproject_version() -> str:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


# ---------------------------------------------------------------------------
# The manifest itself
# ---------------------------------------------------------------------------


def test_surface_manifest_schema() -> None:
    surface = _surface()
    assert surface["schema_version"] == 1
    assert surface["canonical_repository"] == "Kemetra/Seshat-BI"
    names = [c["name"] for c in surface["commands"]]
    assert len(names) == len(set(names)), "duplicate command names"
    for command in surface["commands"]:
        assert set(command) == _COMMAND_FIELDS, command["name"]
        assert command["platform"] == "claude", command["name"]
        assert command["status"] in _STATUSES, command["name"]
        assert command["mode"] in _MODES, command["name"]
        assert isinstance(command["cli_verbs"], list), command["name"]
        assert isinstance(command["gates"], list), command["name"]
        assert (ROOT / command["documentation"]).is_file(), command["name"]
    alias_names = [a["name"] for a in surface.get("command_aliases", [])]
    assert len(alias_names) == len(set(alias_names)), "duplicate alias names"
    assert not set(alias_names) & set(names), "alias name collides with a command"
    shipped = {c["name"] for c in _shipped_commands(surface)}
    for alias in surface.get("command_aliases", []):
        assert set(alias) == _ALIAS_FIELDS, alias["name"]
        assert alias["status"] in _STATUSES, alias["name"]
        assert alias["alias_of"] in shipped, (
            f"alias {alias['name']} points at unshipped command {alias['alias_of']!r}"
        )
    skill_names = [s["name"] for s in surface["skills"]]
    assert len(skill_names) == len(set(skill_names)), "duplicate skill names"
    for skill in surface["skills"]:
        assert set(skill) == _SKILL_FIELDS, skill["name"]
        assert skill["status"] in _STATUSES, skill["name"]
        assert set(skill["platforms"]) <= {"claude", "codex"}, skill["name"]
        assert (ROOT / skill["documentation"]).is_file(), skill["name"]


# ---------------------------------------------------------------------------
# Commands <-> templates <-> allowlist <-> generated bundle
# ---------------------------------------------------------------------------


def test_every_shipped_command_is_templated_allowlisted_and_bundled() -> None:
    surface = _surface()
    allowlist = _allowlist_targets()
    for entry in _shipped_commands(surface) + _shipped_aliases(surface):
        template = ROOT / entry["wrapper_template"]
        assert template.is_file(), f"{entry['name']}: missing wrapper template"
        targets = allowlist.get(entry["wrapper_template"])
        assert targets, f"{entry['name']}: wrapper not allowlisted"
        assert targets.get("claude") == entry["bundle_destination"], entry["name"]
        generated = CLAUDE_BUNDLE / entry["bundle_destination"]
        assert generated.is_file(), f"{entry['name']}: missing generated wrapper"


def test_no_undeclared_or_unshipped_command_wrappers() -> None:
    surface = _surface()
    declared = {c["name"] for c in _shipped_commands(surface)} | {
        a["name"] for a in _shipped_aliases(surface)
    }
    for directory in (COMMAND_TEMPLATE_DIR, CLAUDE_BUNDLE / "commands"):
        actual = {path.stem for path in directory.glob("*.md")}
        assert actual == declared, f"command drift in {directory}: {actual ^ declared}"
    for entry in surface["commands"] + surface.get("command_aliases", []):
        if entry["status"] == "shipped":
            continue
        assert not (CLAUDE_BUNDLE / entry["bundle_destination"]).exists(), (
            f"{entry['name']} is not shipped but has a generated wrapper"
        )


def test_alias_wrappers_carry_the_canonical_body() -> None:
    """A deprecated alias must state its deprecation AND repeat its canonical
    command's instruction body verbatim, so the two names can never drift."""
    surface = _surface()
    by_name = {c["name"]: c for c in _shipped_commands(surface)}
    for alias in _shipped_aliases(surface):
        alias_text = _wrapper_body(ROOT / alias["wrapper_template"])
        assert "Deprecated" in alias_text, alias["name"]
        assert f"/seshat-bi:{alias['alias_of']}" in alias_text, alias["name"]
        canonical = by_name[alias["alias_of"]]
        canonical_body = _wrapper_body(ROOT / canonical["wrapper_template"])
        assert canonical_body in alias_text, (
            f"alias {alias['name']} drifted from canonical {alias['alias_of']}"
        )


def test_command_cli_verbs_are_real_dispatch_keys() -> None:
    dispatch_keys = feeders.read_dispatch_keys(ROOT)
    assert dispatch_keys, "no _DISPATCH keys found -- stale CLI source path?"
    for command in _surface()["commands"]:
        for verb in command["cli_verbs"]:
            assert verb in dispatch_keys, (
                f"{command['name']} references unknown CLI verb {verb!r}"
            )


def test_command_skill_targets_are_shipped_bundled_skills() -> None:
    surface = _surface()
    shipped_skills = {s["name"] for s in _shipped_skills(surface)}
    declared_names = (
        shipped_skills
        | {c["name"] for c in surface["commands"]}
        | {a["name"] for a in surface.get("command_aliases", [])}
    )
    for command in _shipped_commands(surface):
        assert command["skill"] in shipped_skills, (
            f"{command['name']} routes to missing skill {command['skill']!r}"
        )
        wrapper = (ROOT / command["wrapper_template"]).read_text(encoding="utf-8")
        for token in _NAME_TOKEN.findall(wrapper):
            assert token in declared_names, (
                f"{command['name']} wrapper mentions undeclared name {token!r}"
            )


# ---------------------------------------------------------------------------
# Skills <-> both platform bundles (Claude/Codex shared-skill drift)
# ---------------------------------------------------------------------------


def test_declared_skills_exist_in_each_platform_bundle() -> None:
    allowlist = _allowlist_targets()
    for skill in _shipped_skills(_surface()):
        template = ROOT / skill["wrapper_template"]
        assert template.is_file(), f"{skill['name']}: missing wrapper template"
        targets = allowlist.get(skill["wrapper_template"])
        assert targets, f"{skill['name']}: wrapper not allowlisted"
        for platform in skill["platforms"]:
            assert targets.get(platform) == skill["bundle_destination"], skill["name"]
            generated = BUNDLE_ROOTS[platform] / skill["bundle_destination"]
            assert generated.is_file(), f"{skill['name']}: missing in {platform}"


def test_bundled_skill_sets_match_the_declared_surface_exactly() -> None:
    skills = _shipped_skills(_surface())
    for platform, bundle in BUNDLE_ROOTS.items():
        declared = {s["name"] for s in skills if platform in s["platforms"]}
        actual = {path.parent.name for path in (bundle / "skills").glob("*/SKILL.md")}
        assert actual == declared, f"{platform} skill drift: {actual ^ declared}"


# ---------------------------------------------------------------------------
# Router and help-map drift
# ---------------------------------------------------------------------------


def test_router_reaches_every_declared_skill() -> None:
    surface = _surface()
    router_entry = next(s for s in surface["skills"] if s["name"] == "seshat-bi")
    router = (ROOT / router_entry["wrapper_template"]).read_text(encoding="utf-8")
    for skill in _shipped_skills(surface):
        if skill["name"] == "seshat-bi":
            continue
        assert f"`{skill['name']}`" in router, (
            f"router does not route to shipped skill {skill['name']!r}"
        )


def test_help_command_matches_the_declared_surface() -> None:
    surface = _surface()
    help_entry = next(c for c in surface["commands"] if c["name"] == "help")
    text = (ROOT / help_entry["wrapper_template"]).read_text(encoding="utf-8")
    for command in _shipped_commands(surface):
        assert f"`{command['name']}`" in text, (
            f"help map omits shipped command {command['name']!r}"
        )
    skills = {s["name"] for s in _shipped_skills(surface)}
    aliases = {a["name"] for a in _shipped_aliases(surface)}
    undeclared = (
        set(_NAME_TOKEN.findall(text))
        - skills
        - aliases
        - {c["name"] for c in _shipped_commands(surface)}
    )
    assert not undeclared, f"help map advertises undeclared names: {undeclared}"


# ---------------------------------------------------------------------------
# Documentation drift
# ---------------------------------------------------------------------------


def test_active_docs_advertise_exactly_the_shipped_commands() -> None:
    surface = _surface()
    shipped = {c["name"] for c in _shipped_commands(surface)}
    aliases = {a["name"] for a in _shipped_aliases(surface)}
    advertised: set[str] = set()
    for doc in (ROOT / "docs" / "install").glob("*.md"):
        found = set(_NAMESPACED.findall(doc.read_text(encoding="utf-8")))
        unknown = found - shipped - aliases
        assert not unknown, f"{doc.name} advertises unknown commands: {unknown}"
        advertised |= found
    missing = shipped - advertised
    assert not missing, f"install docs omit shipped commands: {sorted(missing)}"


def test_install_docs_version_pins_match_the_packaged_version() -> None:
    version = _pyproject_version()
    for doc in (ROOT / "docs" / "install").glob("*.md"):
        text = doc.read_text(encoding="utf-8")
        for pin in _VERSION_PIN.findall(text):
            assert pin == version, (
                f"{doc.name} pins seshat-bi=={pin} but the package is {version}"
            )
        heading = text.splitlines()[0]
        assert not re.search(r"v?\d+\.\d+", heading), (
            f"{doc.name} hardcodes a version in its title: {heading!r}"
        )


# ---------------------------------------------------------------------------
# No development-only paths in anything a user installs
# ---------------------------------------------------------------------------


def test_documented_governor_tools_match_the_mcp_server() -> None:
    """The router skill and the agent install guide document the MCP governor's
    tool names; they must match the tools the server actually defines."""
    server_source = (ROOT / "src" / "seshat" / "governor" / "mcp_server.py").read_text(
        encoding="utf-8"
    )
    actual = set(re.findall(r"def (seshat_[a-z_]+)\(", server_source))
    assert actual, "no governor tools found -- did mcp_server.py move?"
    router_entry = next(s for s in _surface()["skills"] if s["name"] == "seshat-bi")
    for doc in (
        ROOT / router_entry["wrapper_template"],
        ROOT / "docs" / "install" / "agent-install.md",
    ):
        documented = set(re.findall(r"`(seshat_[a-z_]+)`", doc.read_text("utf-8")))
        assert documented == actual, (
            f"{doc.name} governor-tool drift: {documented ^ actual}"
        )


def _bundle_text_files(bundle: Path) -> list[Path]:
    return [
        path
        for path in bundle.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".yaml", ".yml", ".json"}
        and path.name != "bundle-manifest.json"  # provenance records source paths
    ]


def test_no_development_paths_in_public_bundles_or_templates() -> None:
    roots = [CLAUDE_BUNDLE, CODEX_BUNDLE, ROOT / "distribution" / "bundle-templates"]
    for root in roots:
        for path in _bundle_text_files(root):
            text = path.read_text(encoding="utf-8")
            for fragment in _DEVELOPMENT_PATHS:
                assert fragment not in text, (
                    f"{path.relative_to(ROOT)} references development-only "
                    f"path {fragment!r}"
                )
