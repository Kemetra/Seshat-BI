"""T028 -- the `seshat-studio` consumer skill ships through both authorities.

Spec 139 requirements under test:

* FR-027 -- Studio ships a `seshat-studio` consumer skill in BOTH generated
  bundles, classified through the canonical capability inventory and the export
  pipeline.
* FR-028 -- natural-language launch is PRIMARY; the technical launcher is named
  only in troubleshooting detail.

Why BOTH authorities are asserted here rather than trusting one of them: they run
in opposite directions and neither implies the other. `capabilities.yaml` is the
authored generation INPUT -- `seshat.allowlist_derivation` walks `ships: true`
entries by `references.skill` and emits one allowlist row per file, so an entry
missing there produces no bundle file at all. `public-command-surface.yaml` is the
declared public CONTRACT that is checked against the produced bundles. A capability
registered in only one of the two is the half-shipped verb T030 names: either a
bundle nobody declared, or a declaration nothing generates.

The skill-body assertions are deliberately structural (which section names the
launcher) rather than prose-matching. FR-028 is a claim about WHERE a technical
name may appear, and only a positional assertion can fail when the launcher
migrates up into the primary lane.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY = REPO_ROOT / "docs/capabilities/capabilities.yaml"
SURFACE = REPO_ROOT / "distribution/public-command-surface.yaml"
SKILL_DIR = REPO_ROOT / ".claude/skills/seshat-studio"
SKILL_MD = SKILL_DIR / "SKILL.md"
ROUTER = REPO_ROOT / "distribution/bundle-templates/shared/skills/seshat-bi/SKILL.md"

BUNDLE_ROOTS = {
    "claude": REPO_ROOT / "integrations/claude-code/seshat-bi",
    "codex": REPO_ROOT / "integrations/codex/seshat-bi",
}

SKILL_NAME = "seshat-studio"

# The console command. FR-028 confines this exact token to troubleshooting.
LAUNCHER = "seshat-studio"


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def capability() -> dict[str, Any]:
    entries = _load(INVENTORY)["capabilities"]
    matching = [entry for entry in entries if entry.get("id") == SKILL_NAME]
    assert matching, f"no `{SKILL_NAME}` entry in the capability inventory"
    return matching[0]


@pytest.fixture(scope="module")
def surface_skill() -> dict[str, Any]:
    skills = _load(SURFACE)["skills"]
    matching = [skill for skill in skills if skill.get("name") == SKILL_NAME]
    assert matching, f"no `{SKILL_NAME}` entry in the public command surface"
    return matching[0]


# --------------------------------------------------------------------------- #
# FR-027 -- the authored inventory entry                                       #
# --------------------------------------------------------------------------- #


def test_capability_is_a_shipping_consumer_capability(
    capability: dict[str, Any],
) -> None:
    """The inventory is the generation input, so `ships` must be explicitly true.

    `consumer-capability` rather than `compass-verb`: a compass verb must appear in
    `.seshat/kit-source.yaml`, and Studio is a console/product surface, not one of
    the ten readiness verbs that own a stage transition.
    """
    assert capability["surface"] == "skill"
    assert capability["ships"] is True
    assert capability["ship_classification"] == "consumer-capability"
    assert capability["state"] == "shipped"
    assert capability["command"] is None


def test_capability_points_at_the_canonical_skill_body(
    capability: dict[str, Any],
) -> None:
    """`references.skill` is what the derivation resolves to a directory."""
    assert capability["references"]["skill"] == SKILL_NAME
    canonical = capability["ownership"]["canonical_source"]
    assert canonical == ".claude/skills/seshat-studio/SKILL.md"
    assert (REPO_ROOT / canonical).is_file()
    assert (REPO_ROOT / capability["documentation"]).is_file()


def test_derivation_emits_the_studio_skill_into_the_allowlist() -> None:
    """The authored entry must actually reach the generated allowlist.

    This is the load-bearing link: `ships: true` is inert unless the derivation
    resolves `references.skill` to a real directory carrying a SKILL.md.
    """
    from seshat.allowlist_derivation import derive_allowlist

    derived = derive_allowlist(REPO_ROOT)
    sources = {str(entry["source"]) for entry in derived["entries"]}

    assert f".claude/skills/{SKILL_NAME}/SKILL.md" in sources


# --------------------------------------------------------------------------- #
# FR-027 -- the declared public surface, and both bundles                      #
# --------------------------------------------------------------------------- #


def test_surface_declares_the_skill_for_both_platforms(
    surface_skill: dict[str, Any],
) -> None:
    assert surface_skill["status"] == "shipped"
    assert sorted(surface_skill["platforms"]) == ["claude", "codex"]
    assert surface_skill["wrapper_template"] == ".claude/skills/seshat-studio/SKILL.md"
    assert surface_skill["bundle_destination"] == "skills/seshat-studio/SKILL.md"


@pytest.mark.parametrize("platform", sorted(BUNDLE_ROOTS))
def test_the_skill_is_present_in_each_generated_bundle(platform: str) -> None:
    """FR-027 says BOTH bundles, so neither is allowed to be the only one."""
    generated = BUNDLE_ROOTS[platform] / "skills" / SKILL_NAME / "SKILL.md"

    assert generated.is_file(), f"{platform} bundle carries no {SKILL_NAME} skill"


def test_the_router_routes_to_the_studio_skill() -> None:
    """An unrouted skill is unreachable by name in a consumer workspace."""
    assert f"`{SKILL_NAME}`" in ROUTER.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# FR-028 -- natural language is primary, the launcher is troubleshooting-only  #
# --------------------------------------------------------------------------- #


def _sections(text: str) -> dict[str, str]:
    """Map `##` heading -> that section's body text."""
    sections: dict[str, str] = {}
    current = "<preamble>"
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[current] = "\n".join(buffer)
            current = line[3:].strip()
            buffer = []
        else:
            buffer.append(line)
    sections[current] = "\n".join(buffer)
    return sections


def test_the_launcher_appears_only_under_troubleshooting() -> None:
    """FR-028 -- naming the console command in the primary lane is the defect.

    The frontmatter `name` is necessarily the skill's own name, so the assertion
    runs over the BODY, and a section qualifies only if its heading marks it as
    the technical/troubleshooting lane.
    """
    body = SKILL_MD.read_text(encoding="utf-8").split("---", 2)[2]
    offenders = [
        heading
        for heading, content in _sections(body).items()
        if f"`{LAUNCHER}" in content and "troubleshoot" not in heading.lower()
    ]

    assert not offenders, (
        f"FR-028: the `{LAUNCHER}` launcher is named outside troubleshooting, in "
        f"{offenders}"
    )


def test_natural_language_launch_is_stated_before_any_command() -> None:
    """Primary means FIRST, not merely present somewhere in the file."""
    body = SKILL_MD.read_text(encoding="utf-8").split("---", 2)[2]

    assert "open studio" in body.lower(), (
        "the skill states no natural-language launch phrase"
    )
    assert body.lower().index("open studio") < body.index(f"`{LAUNCHER}"), (
        "FR-028: the technical launcher is introduced before natural language"
    )


# --------------------------------------------------------------------------- #
# Portability + development-path bans over the shipped text                    #
# --------------------------------------------------------------------------- #


def test_the_skill_body_passes_the_portability_gate() -> None:
    """`portability-audit-v1` gates the export; failing it blocks regeneration."""
    from seshat.portability_audit import audit_skill_text

    findings = audit_skill_text(SKILL_NAME, SKILL_MD.read_text(encoding="utf-8"))

    assert not findings, [(finding.path, finding.reason) for finding in findings]
