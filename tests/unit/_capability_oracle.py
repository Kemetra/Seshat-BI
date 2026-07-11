"""Independent ground-truth oracle for the capability inventory (spec 118).

This module is the FEEDER-reading machinery behind the O1-O8 truthfulness
checks. It is split out of ``test_capability_inventory.py`` so neither file
carries too many responsibilities; the test module imports these helpers and
asserts against them.

ANTI-CIRCULARITY (load-bearing, repo lesson ``verifier-must-sit-on-the-risk``):
this module reads the FEEDER sources DIRECTLY and re-implements every reader.
It MUST NOT import ``seshat.capability_feeders`` or ``seshat.capability_inventory``
-- the oracle must never learn what a feeder says by calling the code under
test, or a builder bug that hides drift on both sides would pass vacuously.
The ``import``-free-of-those-modules property is asserted by the test module.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import yaml

LIFECYCLE_STATES = {"shipped", "spec-only", "deferred"}
NUMERIC_FIELD_HINTS = ("score", "maturity", "confidence", "completeness", "health")

# Independent restatement of the closed field set (contracts/inventory-output.md
# Form 2) -- deliberately NOT imported from capability_inventory, so the closed-
# schema checks assert against the SPEC'S field list, not whatever the builder
# happens to emit today.
DECLARED_RECORD_FIELDS = {
    "id",
    "name",
    "summary",
    "state",
    "authority",
    "surface",
    "requirements",
    "provenance",
    "readiness_stage",
    "command",
    "documentation",
    "group",
}


# ---------------------------------------------------------------------------
# Ground-truth readers used BY THE ORACLE ITSELF (independent of the builder)
# ---------------------------------------------------------------------------


def load_manifest(repo_root: Path) -> list[dict]:
    path = repo_root / "docs" / "capabilities" / "capabilities.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return data.get("capabilities", []) if isinstance(data, dict) else []


def as_list(value: object) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _is_dispatch_assign(node: ast.AST) -> bool:
    """True iff ``node`` is the ``_DISPATCH: dict = {...}`` module-level
    annotated assignment (dict literal)."""
    if not isinstance(node, ast.AnnAssign):
        return False
    target = node.target
    return (
        isinstance(target, ast.Name)
        and target.id == "_DISPATCH"
        and isinstance(node.value, ast.Dict)
    )


def dispatch_keys_via_ast(repo_root: Path) -> set[str]:
    """Independent AST read of _DISPATCH -- duplicated from capability_feeders
    on purpose (anti-circularity)."""
    path = repo_root / "src" / "seshat" / "cli" / "__init__.py"
    if not path.exists():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    dispatch_assign = next((n for n in ast.walk(tree) if _is_dispatch_assign(n)), None)
    if dispatch_assign is None:
        return set()
    return {
        k.value
        for k in dispatch_assign.value.keys
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    }


def _name_from_fence_line(fence: str) -> str | None:
    """Fallback line-scan for ``name:`` when the fence is not strict YAML."""
    for line in fence.splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            value = stripped[len("name:") :].strip().strip('"').strip("'")
            return value or None
    return None


def _frontmatter_fence(text: str) -> str | None:
    """The raw YAML fence text of a SKILL.md's frontmatter block, or None."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end]


def _frontmatter_name(raw_fence: str) -> str | None:
    """The declared ``name`` out of a frontmatter fence -- strict YAML first,
    falling back to a line-scan for a fence that fails strict parsing."""
    try:
        fence = yaml.safe_load(raw_fence)
    except yaml.YAMLError:
        fence = None
    if isinstance(fence, dict) and isinstance(fence.get("name"), str):
        return fence["name"].strip().strip('"')
    return _name_from_fence_line(raw_fence)


def skill_frontmatter_names(repo_root: Path) -> set[str]:
    skills_dir = repo_root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return set()
    names = set()
    for skill_md in skills_dir.glob("*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8-sig")
        raw_fence = _frontmatter_fence(text)
        if raw_fence is None:
            continue
        name = _frontmatter_name(raw_fence)
        if name:
            names.add(name)
    return names


def _id_set_from_yaml(
    repo_root: Path, rel_path: str, list_key: str, predicate=None
) -> set[str]:
    """Shared shape behind every 'read a YAML file, pull ``id`` out of a named
    list, keep rows matching an optional predicate' oracle reader."""
    path = repo_root / rel_path
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    rows = data.get(list_key) if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return set()
    return {
        row["id"]
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("id"), str)
        and (predicate is None or predicate(row))
    }


def kit_source_verb_ids(repo_root: Path) -> set[str]:
    return _id_set_from_yaml(repo_root, ".seshat/kit-source.yaml", "verbs")


def rule_titles(repo_root: Path) -> dict[str, str]:
    path = repo_root / "docs" / "rules" / "rules-manifest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        row["id"]: row["title"]
        for row in data
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }


def roadmap_text(repo_root: Path) -> str:
    path = repo_root / "docs" / "roadmap" / "roadmap.md"
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def status_claims_built(repo_root: Path) -> set[str]:
    return _id_set_from_yaml(
        repo_root,
        "docs/quality/status-claims.yaml",
        "claims",
        predicate=lambda row: row.get("claimed-status") == "built",
    )


def valid_stage_tokens(repo_root: Path) -> set[str]:
    path = repo_root / "templates" / "readiness-status.yaml"
    if not path.exists():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    stages = data.get("stages") if isinstance(data, dict) else None
    return set(stages) if isinstance(stages, dict) else set()


# ---------------------------------------------------------------------------
# The oracle: O1-O8, run against an arbitrary repo root
# ---------------------------------------------------------------------------


def _orphans_in(entry_id: str, values: list, known: set[str], kind: str) -> list[str]:
    """Every value in ``values`` absent from ``known``, phrased as an O1
    orphan-reference problem for the given reference kind."""
    return [
        f"{entry_id}: orphan {kind} reference {value!r}"
        for value in values
        if value not in known
    ]


def _orphan_command(entry: dict, dispatch_keys: set[str]) -> list[str]:
    """A non-null ``command`` scalar that is not a real _DISPATCH key."""
    command = entry.get("command")
    if command is None or command in dispatch_keys:
        return []
    return [f"{entry['id']}: command {command!r} is not a _DISPATCH key"]


def find_orphans(repo_root: Path) -> list[str]:
    """O1: a references target absent from its feeder."""
    manifest = load_manifest(repo_root)
    dispatch_keys = dispatch_keys_via_ast(repo_root)
    skill_names = skill_frontmatter_names(repo_root)
    verb_ids = kit_source_verb_ids(repo_root)
    rule_ids = set(rule_titles(repo_root))

    problems: list[str] = []
    for entry in manifest:
        refs = entry.get("references") or {}
        entry_id = entry["id"]
        problems += _orphans_in(
            entry_id, as_list(refs.get("skill")), skill_names, "skill"
        )
        problems += _orphans_in(entry_id, as_list(refs.get("verb")), verb_ids, "verb")
        problems += _orphans_in(
            entry_id, as_list(refs.get("rules_manifest")), rule_ids, "rule"
        )
        problems += _orphan_command(entry, dispatch_keys)
        problems += _orphans_in(
            entry_id, as_list(refs.get("dispatch")), dispatch_keys, "dispatch"
        )
    return problems


def _referenced(manifest: list[dict], kind: str) -> set[str]:
    """Union of every entry's ``references.<kind>`` values across the manifest."""
    out: set[str] = set()
    for entry in manifest:
        refs = entry.get("references") or {}
        out.update(as_list(refs.get(kind)))
    return out


def find_unlisted(repo_root: Path) -> list[str]:
    """O2: a real wired representation covered by NO entry's references
    (reference-coverage, not entry-per-representation)."""
    manifest = load_manifest(repo_root)
    problems: list[str] = []
    for key in dispatch_keys_via_ast(repo_root) - _referenced(manifest, "dispatch"):
        problems.append(f"unlisted dispatch command: {key!r}")
    for name in skill_frontmatter_names(repo_root) - _referenced(manifest, "skill"):
        problems.append(f"unlisted skill: {name!r}")
    for verb_id in kit_source_verb_ids(repo_root) - _referenced(manifest, "verb"):
        problems.append(f"unlisted kit-source verb: {verb_id!r}")
    return problems


def roadmap_row_is_shipped(f_number: str, repo_root: Path) -> bool:
    """True iff the roadmap table row whose FIRST cell names exactly this
    F-number has a status cell that reads SHIPPED (not PARTLY, not spec-only).

    Structural, not a floating substring + char-window: locate the pipe-table
    row whose first cell is ``F0NN`` (optionally bold-wrapped) and read THAT
    row's own last cell, so a SHIPPED neighbor row -- or a prose mention near an
    unrelated "SHIPPED" -- can never grant a false signal to a spec-only feature
    (the O3 fail-closed guarantee)."""
    row_start = re.compile(
        r"^\|\s*\*{0,2}" + re.escape(f_number) + r"\*{0,2}\s*\|", re.IGNORECASE
    )
    for line in roadmap_text(repo_root).splitlines():
        if not row_start.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            return False
        status_cell = cells[-1].upper()
        if "SHIPPED" not in status_cell:
            return False
        disqualifiers = ("PARTLY", "SPEC-ONLY", "SPEC ONLY", "DEFERRED", "PLANNED")
        return not any(d in status_cell for d in disqualifiers)
    return False


def _signal_dispatch(refs: dict, repo_root: Path) -> bool:
    refs_list = as_list(refs.get("dispatch"))
    keys = dispatch_keys_via_ast(repo_root)
    return any(k in keys for k in refs_list)


def _signal_skill(refs: dict, repo_root: Path) -> bool:
    refs_list = as_list(refs.get("skill"))
    names = skill_frontmatter_names(repo_root)
    return any(s in names for s in refs_list)


def _signal_roadmap(refs: dict, repo_root: Path) -> bool:
    ref = refs.get("roadmap")
    return bool(ref) and roadmap_row_is_shipped(ref, repo_root)


def _signal_status_claims(refs: dict, repo_root: Path) -> bool:
    ref = refs.get("status_claims")
    return bool(ref) and ref in status_claims_built(repo_root)


def has_positive_ship_signal(entry: dict, repo_root: Path) -> bool:
    refs = entry.get("references") or {}
    return any(
        signal(refs, repo_root)
        for signal in (
            _signal_dispatch,
            _signal_skill,
            _signal_roadmap,
            _signal_status_claims,
        )
    )


def find_false_shipped(repo_root: Path) -> list[str]:
    """O3: state: shipped with no positive feeder signal (fail-closed)."""
    manifest = load_manifest(repo_root)
    return [
        f"{entry['id']}: state=shipped with no positive ship signal"
        for entry in manifest
        if entry.get("state") == "shipped"
        and not has_positive_ship_signal(entry, repo_root)
    ]


def find_false_released(repo_root: Path) -> list[str]:
    """O4: provenance: publicly-released with no release evidence (fail-closed).
    No feeder in this repo positively records external release evidence today,
    so ANY publicly-released claim currently fails -- the correct, conservative
    behavior FR-013(d) demands."""
    manifest = load_manifest(repo_root)
    problems = []
    for entry in manifest:
        if entry.get("provenance") != "publicly-released":
            continue
        refs = entry.get("references") or {}
        evidence = refs.get("release_evidence")
        if not evidence or not (repo_root / evidence).exists():
            problems.append(
                f"{entry['id']}: publicly-released with no release evidence"
            )
    return problems


def _name_disagrees_with_title(entry: dict, title: str | None) -> bool:
    """True iff ``title`` is a real rule title and the entry's own ``name``
    neither equals it nor contains it as a substring."""
    if title is None:
        return False
    name = entry.get("name")
    return name != title and title not in entry.get("name", "")


def find_contradictions(repo_root: Path) -> list[str]:
    """O5: the manifest echoes a feeder-owned fact that disagrees with the
    feeder (here: a rules_manifest-referenced rule's title vs entry name)."""
    manifest = load_manifest(repo_root)
    titles = rule_titles(repo_root)
    problems = []
    for entry in manifest:
        refs = entry.get("references") or {}
        for rule_id in as_list(refs.get("rules_manifest")):
            title = titles.get(rule_id)
            if _name_disagrees_with_title(entry, title):
                problems.append(
                    f"{entry['id']}: name {entry.get('name')!r} disagrees with "
                    f"rule {rule_id} title {title!r}"
                )
    return problems


def _walk_scalars(node: object, path: str = "") -> list[tuple[str, object]]:
    """Yield (dotted-path, scalar) for every leaf value in a nested dict/list."""
    if isinstance(node, dict):
        return [
            pair
            for k, v in node.items()
            for pair in _walk_scalars(v, f"{path}.{k}" if path else str(k))
        ]
    if isinstance(node, list):
        return [
            pair
            for i, v in enumerate(node)
            for pair in _walk_scalars(v, f"{path}[{i}]")
        ]
    return [(path or "<root>", node)]


def _walk_keys(node: object) -> list[str]:
    """Yield every string key anywhere in a nested dict/list."""
    if isinstance(node, dict):
        own = [k for k in node.keys() if isinstance(k, str)]
        return own + [key for v in node.values() for key in _walk_keys(v)]
    if isinstance(node, list):
        return [key for v in node for key in _walk_keys(v)]
    return []


def _axis_state_violation(entry: dict) -> list[str]:
    state = entry.get("state")
    if state in LIFECYCLE_STATES:
        return []
    return [f"{entry['id']}: state {state!r} is not a LIFECYCLE token"]


def _axis_numeric_scalars(entry: dict) -> list[str]:
    """A numeric maturity/confidence/health value is forbidden ANYWHERE in a
    record (FR-009 / hard rule #9), including nested containers."""
    return [
        f"{entry['id']}: {path} carries a numeric value {value!r}"
        for path, value in _walk_scalars(entry)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]


def _axis_numeric_field_names(entry: dict) -> list[str]:
    return [
        f"{entry['id']}: field name {key!r} suggests a score/maturity value"
        for key in _walk_keys(entry)
        if any(hint in key.lower() for hint in NUMERIC_FIELD_HINTS)
    ]


def find_axis_violations(repo_root: Path) -> list[str]:
    """O6: state holds an authority/provenance token, or any field holds a
    numeric maturity/confidence/completeness/health value."""
    manifest = load_manifest(repo_root)
    problems: list[str] = []
    for entry in manifest:
        problems += _axis_state_violation(entry)
        problems += _axis_numeric_scalars(entry)
        problems += _axis_numeric_field_names(entry)
    return problems


def find_invalid_stage(repo_root: Path) -> list[str]:
    """O8: readiness_stage neither not-stage-scoped nor a valid stages.* key."""
    manifest = load_manifest(repo_root)
    valid = valid_stage_tokens(repo_root)
    problems = []
    for entry in manifest:
        stage = entry.get("readiness_stage", "not-stage-scoped")
        if stage != "not-stage-scoped" and stage not in valid:
            problems.append(
                f"{entry['id']}: readiness_stage {stage!r} is not a valid stage token"
            )
    return problems


def oracle_all_clear(repo_root: Path) -> dict[str, list[str]]:
    return {
        "orphan": find_orphans(repo_root),
        "unlisted": find_unlisted(repo_root),
        "false_shipped": find_false_shipped(repo_root),
        "false_released": find_false_released(repo_root),
        "contradiction": find_contradictions(repo_root),
        "axis_violation": find_axis_violations(repo_root),
        "invalid_stage": find_invalid_stage(repo_root),
    }
