"""Guard the domain packs' ``## Owner questions`` cards (c10).

The rule-fix table drifted to 47 of 79 ids because nothing read the file
(``seshat.rule_fix_table`` module docstring). These cards are the same shape of
surface -- authored markdown that a rule never opens -- so they get their own
guard rather than trusting review.

Two properties are load-bearing:

* every card records under a REAL critical decision type, so an answer can
  actually be stored; and
* every ambiguity a pack lists either has a card or is excluded for one of the
  two reasons the section preamble declares (already RULED, or an instruction
  rather than an owner question). A silently dropped ambiguity is invisible.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from seshat.decision_store import CRITICAL_DECISION_TYPES

_ROOT = Path(__file__).resolve().parents[2]
DOMAINS = _ROOT / "skills" / "retail-kpi-knowledge" / "domains"

_SECTION = re.compile(r"## Owner questions\n(.*?)(?=\n## |\Z)", re.DOTALL)
_AMBIGUITIES = re.compile(r"## Key ambiguities.*?\n(.*?)(?=\n## )", re.DOTALL)
_CARD_ROW = re.compile(
    r"^\| (?P<ref>[^|]+?) \| (?P<ask>[^|]+?) \| (?P<risk>[^|]+?) \| "
    r"(?P<default>[^|]+?) \| `(?P<dtype>[a-z_]+)` \|$",
    re.MULTILINE,
)
_BULLET = re.compile(r"^- (.+)$", re.MULTILINE)

# A card opening with one of these is a closed question: it can be answered "no"
# and recorded as a governed decision while the ambiguity stays open.
_CLOSED_OPENERS = frozenset(
    {
        "do",
        "does",
        "did",
        "is",
        "are",
        "was",
        "were",
        "can",
        "will",
        "should",
        "has",
        "have",
    }
)

# An ambiguity legitimately carries no card when it is already settled, or when it
# states how to compute something rather than asking the owner to decide. Keep this
# list explicit: it is the exclusion ledger the section preamble promises.
_UNCARDED_BY_DESIGN = {
    ("basket-and-transactions", "grain"),  # "count distinct receipts" is an instruction
}


def _packs() -> list[Path]:
    return sorted(DOMAINS.glob("*.md"))


def test_domain_packs_are_present() -> None:
    """A vacuity guard: the sweeps below prove nothing over an empty glob."""
    assert len(_packs()) >= 10


@pytest.mark.unit
@pytest.mark.parametrize("pack", _packs(), ids=lambda p: p.stem)
def test_every_card_records_under_a_real_decision_type(pack: Path) -> None:
    section = _SECTION.search(pack.read_text(encoding="utf-8"))
    assert section, f"{pack.name} has no '## Owner questions' section"
    body = section.group(1)
    rows = _CARD_ROW.findall(body)
    if not rows:
        # A pack whose every ambiguity is already RULED offers no cards. That is a
        # declared state, not an empty section: it must say so, so a reader can tell
        # "nothing to ask" from "someone forgot to write the cards".
        assert body.lstrip().startswith("None."), (
            f"{pack.name} declares the section but lists no cards and does not say why"
        )
        return
    for _ref, _ask, _risk, _default, dtype in rows:
        assert dtype in CRITICAL_DECISION_TYPES, (
            f"{pack.name} card records under '{dtype}', which is not one of the "
            f"critical decision types the Decision Store accepts"
        )


@pytest.mark.unit
@pytest.mark.parametrize("pack", _packs(), ids=lambda p: p.stem)
def test_every_card_asks_a_question(pack: Path) -> None:
    """A card whose 'Ask the owner' cell is not a question cannot be asked."""
    section = _SECTION.search(pack.read_text(encoding="utf-8"))
    assert section
    for _ref, ask, _risk, _default, _dtype in _CARD_ROW.findall(section.group(1)):
        assert ask.strip().endswith("?"), f"{pack.name}: {ask!r} is not a question"


@pytest.mark.unit
@pytest.mark.parametrize("pack", _packs(), ids=lambda p: p.stem)
def test_no_card_is_answerable_without_resolving(pack: Path) -> None:
    """A yes/no card can be answered "no" and recorded, resolving nothing.

    Three cards shipped this way (PR #709 Codex review): a closed question whose
    wrong branch was approvable, a question narrower than its own ambiguity, and a
    confirmation that supplied no rule. An answerable card that leaves the
    ambiguity open unblocks the domain on a non-answer, which is the fail-open the
    cards exist to prevent. Cards must demand the artifact that settles the
    question -- which field, how often, which calendar -- not a yes/no.
    """
    section = _SECTION.search(pack.read_text(encoding="utf-8"))
    assert section
    for _ref, ask, _risk, _default, _dtype in _CARD_ROW.findall(section.group(1)):
        text = ask.strip()
        opener = text.split()[0].lower()
        if opener not in _CLOSED_OPENERS:
            continue
        # "X, or Y?" names its alternatives, so an answer picks one and resolves.
        # A bare binary does not: "no" is recordable and settles nothing.
        assert " or " in text.lower(), (
            f"{pack.name}: {ask!r} is answerable yes/no; name the alternatives or "
            f"ask for the rule/field that resolves the ambiguity"
        )


@pytest.mark.unit
@pytest.mark.parametrize("pack", _packs(), ids=lambda p: p.stem)
def test_no_card_records_its_own_default_as_a_ruling(pack: Path) -> None:
    """The layer default is CONTEXT. A card must never present it as decided.

    ``kpi-ambiguities.md``'s Resolution rule: this layer never invents a policy to
    make a number appear.
    """
    section = _SECTION.search(pack.read_text(encoding="utf-8"))
    assert section
    body = section.group(1)
    for _ref, _ask, _risk, default, _dtype in _CARD_ROW.findall(body):
        lowered = default.strip().lower()
        assert not lowered.startswith("ruled"), (
            f"{pack.name}: a card default must not assert a ruling ({default!r})"
        )


@pytest.mark.unit
@pytest.mark.parametrize("pack", _packs(), ids=lambda p: p.stem)
def test_a_fixed_rule_is_stated_not_offered_as_a_choice(pack: Path) -> None:
    """A card must not offer the side its own pack forbids.

    Where a pack states an invariant -- "aggregate on the key only", "use net
    sales, never gross", an Unknown member is "not a valid analysis member" -- an
    owner picking the forbidden branch would have their choice recorded as an
    APPROVED decision that contradicts the seeded contracts (PR #709 Codex review,
    five instances). Such a card must ask only the genuinely open part, and its
    default column must restate the invariant rather than read "None".

    The check is narrow on purpose: it pins the specific invariants the packs
    state today, so it fails loudly if a card reintroduces the choice.
    """
    forbidden = {
        "margin-profitability": ("gross or net", "net sales is the base"),
        "discounts-and-promotions": ("gross or net", "gross sales is the denominator"),
        "data-quality-control": (
            "analysable category",
            "never a valid analysis member",
        ),
        "targets-and-budgets": ("be shown?", "never shown as 0%"),
    }
    if pack.stem not in forbidden:
        pytest.skip(f"{pack.stem} states no pinned invariant")
    offered, restated = forbidden[pack.stem]

    section = _SECTION.search(pack.read_text(encoding="utf-8"))
    assert section
    body = section.group(1)
    asks = " ".join(a for _r, a, _k, _d, _t in _CARD_ROW.findall(body)).lower()
    assert offered not in asks, (
        f"{pack.stem}: a card offers {offered!r}, which this pack forbids -- ask "
        f"only the open part and state the invariant in the default column"
    )
    defaults = " ".join(d for _r, _a, _k, d, _t in _CARD_ROW.findall(body)).lower()
    assert restated in defaults, (
        f"{pack.stem}: no card default restates the invariant {restated!r}, so a "
        f"reader cannot tell the rule from an unmade decision"
    )


@pytest.mark.unit
@pytest.mark.parametrize("pack", _packs(), ids=lambda p: p.stem)
def test_every_open_ambiguity_has_a_card_or_a_declared_exclusion(pack: Path) -> None:
    """A dropped ambiguity is invisible unless something counts them."""
    text = pack.read_text(encoding="utf-8")
    ambiguities = _AMBIGUITIES.search(text)
    if not ambiguities:
        pytest.skip(f"{pack.name} lists no ambiguities")
    bullets = _BULLET.findall(ambiguities.group(1))
    # A settled bullet is excluded by the preamble's own rule: re-asking a RULED
    # decision invites a contradicting answer.
    open_bullets = [b for b in bullets if "RULED" not in b]
    excluded = sum(1 for stem, _why in _UNCARDED_BY_DESIGN if stem == pack.stem)

    section = _SECTION.search(text)
    cards = len(_CARD_ROW.findall(section.group(1))) if section else 0

    # No open ambiguities => no cards required; the section says so in prose.
    if not open_bullets:
        return

    assert cards + excluded >= len(open_bullets), (
        f"{pack.name}: {len(open_bullets)} open ambiguity/ies but only {cards} card(s) "
        f"and {excluded} declared exclusion(s) -- an ambiguity was dropped silently"
    )


@pytest.mark.unit
def test_interview_does_not_overclaim_which_card_types_block() -> None:
    """The skill must not promise a block the gate does not enforce.

    Cards record under five decision types, but the `kpi_contracts` gate blocks on
    three. Saying "an unanswered card leaves the domain blocked" was therefore
    false for `data_exclusion` and `table_grain` cards, which are recorded and
    then silently skipped by the gate (PR #709 Codex review). The skill now names
    the blocking three and says the others are recorded but non-blocking; this
    test fails if the gate's category set and that prose diverge.
    """
    from seshat.decision_gate import _load_blocking_categories

    blocking = _load_blocking_categories(_ROOT, "kpi_contracts") or set()
    assert blocking, (
        "kpi_contracts declares no blocking categories -- gate lookup broke"
    )

    skill = (
        _ROOT / ".claude" / "skills" / "business-knowledge-interview" / "SKILL.md"
    ).read_text(encoding="utf-8")
    step = skill.split("4. **Ask the domain's owner questions")[1]
    step = step.split(chr(10) + "5. ")[0]

    for dtype in sorted(blocking):
        assert dtype in step, f"step 4 does not name blocking type {dtype!r}"

    used = set()
    for pack in _packs():
        section = _SECTION.search(pack.read_text(encoding="utf-8"))
        if section:
            used |= {t for *_rest, t in _CARD_ROW.findall(section.group(1))}
    for dtype in sorted(used - blocking):
        assert dtype in step, (
            f"cards record under {dtype!r}, which the gate does NOT block on, and "
            f"step 4 never says so -- a reader would expect a block that never fires"
        )
