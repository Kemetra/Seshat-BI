"""Scaffold-rule authoring helper + doctor (feature 062).

A static, stdlib-only authoring helper with two modes.

Author mode WRITES the mechanical boilerplate a new governance rule needs and
PRINTS -- never runs -- the follow-up regen commands and glossary row:

WRITES (exactly these three):
  1. a generic stub rule module under ``src/seshat/rules/`` calling
     ``@register(<id>, "<title>")`` with a body that yields no findings;
  2. a matching failing test stub under ``tests/unit/`` (honest red);
  3. an insertion of ``<id>`` into ``EXPECTED_RULE_IDS`` in
     ``tests/unit/test_rules_wiring.py``.

PRINTS (never writes / never runs):
  - the two golden-record regen commands (rule-inventory manifest + severity);
  - a suggested glossary row for the human to paste into ``docs/glossary.md``;
  - the import + ``__all__`` edit for ``src/seshat/rules/__init__.py``.

Doctor mode READS the five wiring places and REPORTS, per rule id (single or
sweep), which places the id is present in and which it is missing from. It never
writes.

The helper NEVER invents rule intent (the author supplies id + title, DEC-1),
NEVER edits prose or golden records (Principle V), and NEVER self-grants a wiring
pass -- the suite + gate exit code remain the truth (Principle I). Its own
five-place list is a declared, guard-tested constant so it cannot silently drift.

stdlib-only; no DB, no network, no execution (Principle VIII). All authored files
are UTF-8 without BOM, ``\\n`` line endings, ASCII-safe (Principle IX).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Repo-relative wiring-place targets (single source of truth for path strings).
# ---------------------------------------------------------------------------

REGISTRY_REL = "src/seshat/registry.py"
RULES_INIT_REL = "src/seshat/rules/__init__.py"
WIRING_TEST_REL = "tests/unit/test_rules_wiring.py"
MANIFEST_REL = "docs/rules/rules-manifest.json"
SEVERITY_REL = "docs/rules/severity-posture.json"
GLOSSARY_REL = "docs/glossary.md"

# The token the id is inserted into / read from in the wiring test.
EXPECTED_SET_NAME = "EXPECTED_RULE_IDS"

# A valid rule id: a letter-led short token like S1, S4a, D10, PP1, AL1.
# ASCII letters + digits only; no separators. Keeps ids glossary/manifest-stable.
_RULE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


# ---------------------------------------------------------------------------
# Value objects (immutable).
# ---------------------------------------------------------------------------


class WiringPlace(NamedTuple):
    """One of the five locations a rule id must appear in to be fully wired."""

    key: str
    label: str
    targets: tuple[str, ...]
    write_mode: str  # "write" (scaffold may author it) or "print" (print-only)


# The declared, guard-tested five-place list (FR-017). Order is the report order.
# ``golden`` spans two files (manifest + severity posture); both print-only.
FIVE_PLACES: tuple[WiringPlace, ...] = (
    WiringPlace(
        key="register",
        label="registry @register",
        targets=(RULES_INIT_REL,),
        write_mode="write",
    ),
    WiringPlace(
        key="import_all",
        label="rules package import + __all__",
        targets=(RULES_INIT_REL,),
        write_mode="print",
    ),
    WiringPlace(
        key="expected_ids",
        label="EXPECTED_RULE_IDS set",
        targets=(WIRING_TEST_REL,),
        write_mode="write",
    ),
    WiringPlace(
        key="golden",
        label="golden records (manifest + severity posture)",
        targets=(MANIFEST_REL, SEVERITY_REL),
        write_mode="print",
    ),
    WiringPlace(
        key="glossary",
        label="glossary row",
        targets=(GLOSSARY_REL,),
        write_mode="print",
    ),
)

# The keys the repo actually has today (FR-017 guard invariant). Declared here as
# the expected set the guard test cross-checks the FIVE_PLACES declaration against.
REPO_WIRING_KEYS: frozenset[str] = frozenset(
    {"register", "import_all", "expected_ids", "golden", "glossary"}
)


class RuleIdentity(NamedTuple):
    """The author-supplied identity of a new rule. Intent is NEVER invented."""

    id: str
    title: str


@dataclass(frozen=True)
class ScaffoldResult:
    """Outcome of a scaffold (author) run. Enforces the write/print split."""

    written: tuple[str, ...] = ()
    printed: tuple[str, ...] = ()
    refused: str | None = None

    @property
    def ok(self) -> bool:
        return self.refused is None


@dataclass(frozen=True)
class DoctorEntry:
    """Per-id presence record across the five places."""

    id: str
    places: dict[str, str]  # key -> "present" | "missing" | "unverifiable"

    @property
    def has_drift(self) -> bool:
        return any(state == "missing" for state in self.places.values())


@dataclass(frozen=True)
class DoctorReport:
    """Read-only output of Doctor mode."""

    entries: tuple[DoctorEntry, ...] = field(default_factory=tuple)

    @property
    def has_drift(self) -> bool:
        return any(e.has_drift for e in self.entries)


PRESENT = "present"
MISSING = "missing"
UNVERIFIABLE = "unverifiable"


# ---------------------------------------------------------------------------
# Input validation (FR-010).
# ---------------------------------------------------------------------------


def validate_identity(rule_id: str, title: str) -> str | None:
    """Return an error message if the identity is invalid, else None.

    A malformed id or an empty/whitespace title is rejected at the boundary
    before anything is written.
    """
    if not rule_id or not _RULE_ID_RE.match(rule_id):
        return (
            f"invalid rule id {rule_id!r}: must be a letter-led alphanumeric "
            "token (e.g. 'S9', 'D12', 'PP2'), ASCII only, no separators"
        )
    if not title or not title.strip():
        return "invalid title: must be a non-empty one-line string"
    if not title.isascii():
        return "invalid title: must be ASCII-safe (Principle IX)"
    return None


# ---------------------------------------------------------------------------
# Read-only place readers (Doctor). Each returns present/missing/unverifiable.
# ---------------------------------------------------------------------------


def _read(repo: Path, rel: str) -> str | None:
    """Read a repo file as text, or None if it is absent/unreadable."""
    try:
        return (repo / rel).read_text(encoding="utf-8-sig")
    except (OSError, ValueError):
        return None


def _registered_ids(repo: Path) -> frozenset[str] | None:
    """Place #1: the ids the live registry reports.

    Read from the live registry (import side effect) -- authoritative, not a text
    scrape. Returns None only if the registry cannot be loaded at all.
    """
    try:
        import seshat.rules  # noqa: F401  (side effect: fires every @register)

        from .registry import all_rules

        return frozenset(r.id for r in all_rules())
    except Exception:
        return None


def check_register(repo: Path, rule_id: str, registered: frozenset[str] | None) -> str:
    if registered is None:
        return UNVERIFIABLE
    return PRESENT if rule_id in registered else MISSING


def check_import_all(repo: Path, rule_id: str) -> str:
    """Place #2: the id's rule appears in the package import list + __all__.

    The import list names MODULES, not ids, so presence is checked by confirming
    the id is registered AND the package import succeeded. The registry side
    effect only fires if the module is in the import list, so a registered id is
    necessarily import-wired. Absent/unreadable __init__ -> unverifiable.
    """
    text = _read(repo, RULES_INIT_REL)
    if text is None:
        return UNVERIFIABLE
    registered = _registered_ids(repo)
    if registered is None:
        return UNVERIFIABLE
    return PRESENT if rule_id in registered else MISSING


def check_expected_ids(repo: Path, rule_id: str) -> str:
    """Place #3: the id is a member of EXPECTED_RULE_IDS in the wiring test."""
    text = _read(repo, WIRING_TEST_REL)
    if text is None:
        return UNVERIFIABLE
    return PRESENT if _id_in_expected_set(text, rule_id) else MISSING


def check_golden(repo: Path, rule_id: str) -> str:
    """Place #4: the id is in BOTH golden records (manifest + severity posture).

    Missing from either -> missing. Either file unreadable -> unverifiable.
    """
    manifest = _read(repo, MANIFEST_REL)
    severity = _read(repo, SEVERITY_REL)
    if manifest is None or severity is None:
        return UNVERIFIABLE
    try:
        manifest_ids = {e.get("id") for e in json.loads(manifest)}
    except (ValueError, TypeError, AttributeError):
        return UNVERIFIABLE
    try:
        severity_ids = set(json.loads(severity).get("registered", {}).keys())
    except (ValueError, TypeError, AttributeError):
        return UNVERIFIABLE
    in_both = rule_id in manifest_ids and rule_id in severity_ids
    return PRESENT if in_both else MISSING


def check_glossary(repo: Path, rule_id: str) -> str:
    """Place #5: the id is referenced somewhere in the glossary prose."""
    text = _read(repo, GLOSSARY_REL)
    if text is None:
        return UNVERIFIABLE
    return PRESENT if _id_referenced(text, rule_id) else MISSING


# Map place key -> reader. Keeps doctor iteration data-driven over FIVE_PLACES.
def _check_place(
    repo: Path, key: str, rule_id: str, registered: frozenset[str] | None
) -> str:
    if key == "register":
        return check_register(repo, rule_id, registered)
    if key == "import_all":
        return check_import_all(repo, rule_id)
    if key == "expected_ids":
        return check_expected_ids(repo, rule_id)
    if key == "golden":
        return check_golden(repo, rule_id)
    if key == "glossary":
        return check_glossary(repo, rule_id)
    raise ValueError(f"unknown wiring place key: {key!r}")


def _id_referenced(text: str, rule_id: str) -> bool:
    """True if ``rule_id`` appears as a standalone token in ``text``."""
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(rule_id) + r"(?![A-Za-z0-9])")
    return pattern.search(text) is not None


def _id_in_expected_set(text: str, rule_id: str) -> bool:
    """True if ``rule_id`` is a quoted member inside the EXPECTED_RULE_IDS block."""
    block = _expected_set_block(text)
    if block is None:
        return False
    quoted = re.compile(
        r'"' + re.escape(rule_id) + r'"' + r"|'" + re.escape(rule_id) + r"'"
    )
    return quoted.search(block) is not None


def _expected_set_block(text: str) -> str | None:
    """Return the source text of the EXPECTED_RULE_IDS frozenset({...}) block."""
    start = text.find(EXPECTED_SET_NAME)
    if start == -1:
        return None
    brace = text.find("{", start)
    if brace == -1:
        return None
    depth = 0
    for i in range(brace, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace : i + 1]
    return None


# ---------------------------------------------------------------------------
# Doctor: single-id and sweep.
# ---------------------------------------------------------------------------


def doctor(repo: Path | str, rule_id: str | None = None) -> DoctorReport:
    """Verify wiring across the five places (read-only).

    With ``rule_id``: verify that one id. Without: sweep every registered id.
    """
    repo = Path(repo)
    registered = _registered_ids(repo)
    if rule_id is not None:
        ids = [rule_id]
    else:
        ids = sorted(registered) if registered else []
    entries: list[DoctorEntry] = []
    for rid in ids:
        places = {
            p.key: _check_place(repo, p.key, rid, registered) for p in FIVE_PLACES
        }
        entries.append(DoctorEntry(id=rid, places=places))
    return DoctorReport(entries=tuple(entries))


# ---------------------------------------------------------------------------
# Author mode: render + write the three targets, print the follow-ups.
# ---------------------------------------------------------------------------


def _module_name(rule_id: str) -> str:
    """A safe stub module name derived from the id (lowercased id)."""
    return f"rule_{rule_id.lower()}"


def render_stub_module(rule_id: str, title: str) -> str:
    """Render a GENERIC stub rule module (no worked-example specifics, FR-003).

    The rule body yields NO findings -- it is a registered no-op the author fills
    in with real logic. The matching test stub fails until that logic lands.
    """
    return (
        f'"""{rule_id} -- {title}.\n'
        "\n"
        "Generated stub (feature 062 scaffold). Replace the placeholder body with\n"
        "the real check logic. Until then the rule is a registered no-op and its\n"
        "test stub fails (honest red).\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from typing import Iterable\n"
        "\n"
        "from ..core import Finding, RuleContext\n"
        "from ..registry import register\n"
        "\n"
        "\n"
        f'@register("{rule_id}", "{title}")\n'
        f"def check_{rule_id.lower()}(ctx: RuleContext) -> Iterable[Finding]:\n"
        "    # TODO: implement the real check. Placeholder body yields no findings.\n"
        "    return []\n"
    )


def render_test_stub(rule_id: str) -> str:
    """Render a failing test stub (honest red, SC-002 / US1 scenario 3).

    The stub asserts False with a clear TODO message so it FAILS immediately
    after scaffolding until the author writes a real test + real logic.
    """
    low = rule_id.lower()
    return (
        f'"""Test stub for rule {rule_id} (062 scaffold). RED until filled."""\n'
        "\n"
        "import pytest\n"
        "\n"
        "pytestmark = pytest.mark.unit\n"
        "\n"
        "\n"
        f"def test_{low}_not_yet_implemented() -> None:\n"
        f"    # Honest red: replace with a real test for {rule_id}, then remove\n"
        "    # this failing assertion once the rule logic exists.\n"
        f"    pytest.fail(\n"
        f'        "rule {rule_id} not yet implemented -- write real logic + test"\n'
        f"    )\n"
    )


def _insert_into_expected_set(text: str, rule_id: str) -> str | None:
    """Return ``text`` with ``rule_id`` inserted into the EXPECTED_RULE_IDS block.

    The insertion is a mechanical membership add (DEC/plan design-decision 5): the
    expected-id set is a source-of-truth set the author is entitled to have the
    helper edit. Returns None if the block cannot be located.
    """
    block = _expected_set_block(text)
    if block is None:
        return None
    # Insert a new quoted member on its own line just after the opening brace,
    # matching the file's existing indentation style (8 spaces inside the set).
    insertion = f'        "{rule_id}",\n'
    open_brace = text.find(block)
    after_brace = open_brace + 1  # position just past "{"
    # Preserve a leading newline if the block opens with one.
    if text[after_brace] == "\n":
        after_brace += 1
    return text[:after_brace] + insertion + text[after_brace:]


def _regen_commands() -> tuple[str, str]:
    return (
        f"retail manifest   # regenerate {MANIFEST_REL}",
        f"retail severity-posture   # regenerate {SEVERITY_REL}",
    )


def _glossary_row(rule_id: str, title: str) -> str:
    """A suggested glossary row for the human to paste (print-only, never written)."""
    src = f"src/seshat/rules/{_module_name(rule_id)}.py"
    return f"| **{rule_id}** | {title} (see {src}). |"


def _import_all_edit(rule_id: str) -> str:
    module = _module_name(rule_id)
    return (
        f'add `{module},` to the import tuple AND `"{module}",` to __all__ in '
        f"{RULES_INIT_REL} (place #2 -- shown for review, apply by hand)"
    )


def scaffold(
    repo: Path | str, rule_id: str, title: str, *, dry_run: bool = False
) -> ScaffoldResult:
    """Author-mode scaffold: write the three targets, return the follow-ups.

    Refuses (no changes) when the id is invalid, already registered, or a stub
    module already exists. Writes NOTHING to any golden record or the glossary.
    ``dry_run`` computes the result without writing (used by tests to inspect the
    plan); the default performs the writes.
    """
    repo = Path(repo)

    # 1. Validate identity at the boundary (FR-010).
    err = validate_identity(rule_id, title)
    if err is not None:
        return ScaffoldResult(refused=err)

    # 2. Refuse if already registered (FR-009).
    registered = _registered_ids(repo)
    if registered is not None and rule_id in registered:
        return ScaffoldResult(refused=f"rule id {rule_id!r} is already registered")

    # 2b. Refuse if the id is already a member of EXPECTED_RULE_IDS even when the
    #     live registry does not know it (a prior partial scaffold whose stub
    #     module was deleted but whose EXPECTED_RULE_IDS edit survived). Without
    #     this the id would be inserted a SECOND time -- contradicting the spec's
    #     idempotent-safe "will not double-insert" guarantee. Read-only check.
    wiring_probe = _read(repo, WIRING_TEST_REL)
    if wiring_probe is not None and _id_in_expected_set(wiring_probe, rule_id):
        return ScaffoldResult(
            refused=(
                f"rule id {rule_id!r} is already a member of {EXPECTED_SET_NAME} "
                f"in {WIRING_TEST_REL} (prior partial scaffold?); refusing to "
                f"double-insert"
            )
        )

    module_rel = f"src/seshat/rules/{_module_name(rule_id)}.py"
    test_rel = f"tests/unit/test_{_module_name(rule_id)}.py"

    # 3. Refuse if a stub module already exists (no overwrite, FR-009).
    if (repo / module_rel).exists():
        return ScaffoldResult(refused=f"stub module already exists: {module_rel}")

    # 4. Render the three write targets.
    module_text = render_stub_module(rule_id, title)
    test_text = render_test_stub(rule_id)
    wiring_text = _read(repo, WIRING_TEST_REL)
    if wiring_text is None:
        return ScaffoldResult(refused=f"cannot read {WIRING_TEST_REL} to insert the id")
    new_wiring = _insert_into_expected_set(wiring_text, rule_id)
    if new_wiring is None:
        return ScaffoldResult(
            refused=f"could not locate {EXPECTED_SET_NAME} in {WIRING_TEST_REL}"
        )

    # 5. Build the print list (never written): regen commands, glossary row,
    #    the import/__all__ edit.
    regen_a, regen_b = _regen_commands()
    printed = (
        regen_a,
        regen_b,
        _glossary_row(rule_id, title),
        _import_all_edit(rule_id),
    )

    written = (module_rel, test_rel, WIRING_TEST_REL)

    if dry_run:
        return ScaffoldResult(written=written, printed=printed)

    # 6. Write exactly the three targets (UTF-8 no BOM, \n endings, Principle IX).
    _write_text(repo / module_rel, module_text)
    _write_text(repo / test_rel, test_text)
    _write_text(repo / WIRING_TEST_REL, new_wiring)

    return ScaffoldResult(written=written, printed=printed)


def _write_text(path: Path, text: str) -> None:
    """Write UTF-8 without BOM and ``\\n`` line endings (Windows-stable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
