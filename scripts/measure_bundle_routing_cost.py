"""Measure the per-session routing cost a generated agent bundle imposes.

Spec 138 (FR-021a / SC-010), research decision R5. The routing cost is the
material an agent must hold merely to KNOW WHICH SKILLS EXIST -- each shipped
skill's `name` and `description` frontmatter -- before it invokes any of them.

Skill BODIES are excluded on purpose. They load on demand (FR-021b), so body
size is not a per-session cost. Measuring them would produce an alarming number
that describes nothing a user pays for: the bodies here run to tens of
kilobytes while their descriptions are a line each.

This emits a SIZE, never a score. Nothing may derive a confidence, health,
maturity or completeness value from it (hard rule #9).

Stdlib only -- no YAML dependency, no tokenizer. The authoritative figures are
the exact character and byte counts; `tokens_approx` is a derived estimate using
one fixed, stated divisor so successive runs stay comparable.

    python scripts/measure_bundle_routing_cost.py
    python scripts/measure_bundle_routing_cost.py --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Fixed, stated divisor. The ABSOLUTE token figure is an estimate; what the
# ceiling governs is the trend across stories, so the divisor must never change
# between runs or the before/after comparison becomes meaningless.
_CHARS_PER_TOKEN = 4

_BUNDLES: dict[str, str] = {
    "claude": "integrations/claude-code/seshat-bi",
    "codex": "integrations/codex/seshat-bi",
}


@dataclass(frozen=True)
class SkillRouting:
    """One shipped skill's contribution to the routing surface."""

    name: str
    description: str

    @property
    def chars(self) -> int:
        return len(self.name) + len(self.description)


@dataclass(frozen=True)
class BundleRouting:
    """The whole routing surface of one generated bundle."""

    harness: str
    skills: tuple[SkillRouting, ...]

    @property
    def chars(self) -> int:
        return sum(s.chars for s in self.skills)

    @property
    def payload(self) -> dict[str, object]:
        return {
            "harness": self.harness,
            "skill_count": len(self.skills),
            "chars": self.chars,
            "bytes": sum(
                len((s.name + s.description).encode("utf-8")) for s in self.skills
            ),
            "tokens_approx": self.chars // _CHARS_PER_TOKEN,
            "chars_per_token_divisor": _CHARS_PER_TOKEN,
            "skills": [
                {"name": s.name, "chars": s.chars}
                for s in sorted(self.skills, key=lambda s: -s.chars)
            ],
        }


def _frontmatter(text: str) -> dict[str, str]:
    """Parse the leading `---` block into flat scalars.

    Deliberately minimal: SKILL.md frontmatter carries only `name` and
    `description`, the latter often as a `>-` folded block. A YAML dependency
    would pull a third-party import into a measurement script for no gain.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    key = ""
    for raw in text[3:end].splitlines():
        if not raw.strip():
            continue
        if not raw.startswith((" ", "\t")) and ":" in raw:
            key, _, value = raw.partition(":")
            key = key.strip()
            fields[key] = value.strip().lstrip(">|-").strip()
        elif key:
            fields[key] = f"{fields[key]} {raw.strip()}".strip()
    return fields


def measure(bundle_root: Path, harness: str) -> BundleRouting:
    """Measure one bundle's routing surface."""
    skills: list[SkillRouting] = []
    for skill_md in sorted((bundle_root / "skills").rglob("SKILL.md")):
        fields = _frontmatter(skill_md.read_text(encoding="utf-8"))
        skills.append(
            SkillRouting(
                name=fields.get("name", skill_md.parent.name),
                description=fields.get("description", ""),
            )
        )
    return BundleRouting(harness=harness, skills=tuple(skills))


def _render(results: list[BundleRouting]) -> str:
    lines = ["Bundle routing cost (name + description only; bodies load on demand)", ""]
    for result in results:
        data = result.payload
        lines.append(
            f"  {data['harness']:<8} skills={data['skill_count']:<4} "
            f"chars={data['chars']:<7} bytes={data['bytes']:<7} "
            f"tokens_approx={data['tokens_approx']}"
        )
    lines += [
        "",
        f"  tokens_approx = chars // {_CHARS_PER_TOKEN} (fixed divisor; the exact",
        "  figures are chars/bytes). This is a SIZE, not a score.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    root = Path(args.repo)
    results: list[BundleRouting] = []
    for harness, relative in _BUNDLES.items():
        bundle_root = root / relative
        if not (bundle_root / "skills").is_dir():
            print(f"error: no skills directory at {bundle_root}", file=sys.stderr)
            return 2
        results.append(measure(bundle_root, harness))

    if args.format == "json":
        print(json.dumps([r.payload for r in results], indent=2))
    else:
        print(_render(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
