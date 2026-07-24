"""Read-only narrative-brief checker (spec 021-analyst-narrative-layer, T013).

Validates a committed ``mappings/<table>/narrative-brief.md`` against the FROZEN
``seshat.narrative-brief/v1`` schema (``skills/bi-analyst-knowledge/
derivation-route.md``, "Rules the checker enforces against this schema"). It is
the read-only evidence surface for the Stage-6 narrative layer: it reports
categorical findings with named blockers so a human design review can see, at a
glance, whether a brief is structurally sound BEFORE any layout work.

WHY A CLI VERB, NOT A SKILL (same precedent as ``pbir-validate-bindings``)
--------------------------------------------------------------------------------
The delivery default for new capabilities is a SKILL (ratified Option-B). This
module is the narrow, established exception: a CHECK SURFACE that POLICES an
artifact a writer already produced (the ``bi-analyst-knowledge`` derivation
route). It computes nothing an analyst must judge; it asserts the brief obeys
its own frozen schema.

READ-ONLY, GRANTS NO APPROVAL (Principle VIII)
--------------------------------------------------------------------------------
Opens nothing for write, never mutates the Decision Store, never sets a
readiness stage. ``NarrativeCheckResult.grants_approval`` is ALWAYS False and
the shape carries no member that could flip it. Status vocabulary is the shipped
subset (``pass`` / ``blocked``); a clean brief is evidence FOR the human review,
never a substitute for it.

FAIL-CLOSED (FR-008; the #453 lesson: never a silent "0 findings" over nothing)
--------------------------------------------------------------------------------
A missing, unreadable, front-section-less, or malformed brief is a ``blocked``
finding NAMING the problem -- never an exit-0 "classified nothing". A checker
that silently validates nothing gives false comfort, the exact failure mode it
exists to remove.

SCOPE: the BRIEF only. The visual<->question binding-map orphan check (a design
guidance artifact) is authored by Phase B (dashboard-design's three-way map,
T010) and is NOT in scope here -- the map does not exist yet, and checking an
always-absent map would be a vacuous fail-open. Brief-absence IS fail-closed
input (FR-008); binding-map absence is simply out of this verb's scope.

No pbi-cli, no live DB, no network -- stdlib parsing plus PyYAML (already a
dependency) and the shared hardened read-only git probe for the revision guard.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from .gitstate import run_git

SCHEMA_LITERAL = "seshat.narrative-brief/v1"
BINDING_MAP_SCHEMA_LITERAL = "seshat.binding-map/v1"
_STAGES = ("overview", "change", "why_where", "action")

# The eight framing cards (skills/bi-analyst-knowledge/framing-*.md). A framing
# outside this set is a typo/unknown card -- validated so a misspelling cannot
# silently escape the guardrail rule below.
_ALL_FRAMINGS = frozenset(
    {
        "benchmark-threshold",
        "concentration",
        "contribution-mix",
        "period-variance",
        "rate-decomposition",
        "segment-behavior",
        "signal-vs-noise",
        "trend-anomaly",
    }
)

# Framings that carry a guardrail (derivation-route.md FR-002a). A question with
# one of these framings MUST state a named ``guardrail.basis``.
_GUARDRAIL_FRAMINGS = frozenset(
    {
        "trend-anomaly",
        "period-variance",
        "concentration",
        "segment-behavior",
        "benchmark-threshold",
        "signal-vs-noise",
    }
)


class NarrativeFinding(NamedTuple):
    """One brief defect: evidence only, grants nothing."""

    dimension: str  # the named check that fired (see module docstring / tests)
    locator: str  # where (question id, stage key, or the brief path)
    message: str  # human-readable statement naming the cause


class NarrativeCheckResult(NamedTuple):
    """The checker's verdict. Read-only evidence, never an approval grant --
    ``grants_approval`` is ALWAYS False; no member on this shape can flip it."""

    status: str  # "pass" | "blocked"; any finding blocks
    findings: tuple[NarrativeFinding, ...]
    evidence: tuple[str, ...]
    grants_approval: bool = False


# --------------------------------------------------------------------------- #
# Front-section extraction + parse (fail-closed at every step)
# --------------------------------------------------------------------------- #

_FRONT_FENCE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL)


def _extract_front_section(text: str) -> str | None:
    """The first fenced ``yaml`` block's body, or None when there is none."""
    match = _FRONT_FENCE.search(text)
    return match.group(1) if match else None


def _blocked(dimension: str, locator: str, message: str) -> NarrativeCheckResult:
    """A single-finding fail-closed result (used for input-level problems)."""
    return NarrativeCheckResult(
        status="blocked",
        findings=(NarrativeFinding(dimension, locator, message),),
        evidence=(
            "read-only narrative-brief check; this is EVIDENCE for the named "
            "human design review and grants NO approval",
        ),
        grants_approval=False,
    )


def _load_front(
    brief_path: Path,
) -> tuple[dict[str, Any] | None, NarrativeCheckResult | None]:
    """The parsed front-section mapping, or the fail-closed result naming why
    it could not be produced (missing / unreadable / no fence / malformed /
    non-mapping / wrong schema literal)."""
    locator = str(brief_path)
    if not brief_path.is_file():
        return None, _blocked(
            "missing_brief",
            locator,
            f"no narrative-brief.md at {brief_path} -- nothing to check "
            f"(fail closed); author the brief first via bi-analyst-knowledge",
        )
    try:
        text = brief_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None, _blocked(
            "unreadable_brief",
            locator,
            "narrative-brief.md is unreadable -- check blocked (fail closed)",
        )
    front = _extract_front_section(text)
    if front is None:
        return None, _blocked(
            "no_front_section",
            locator,
            "narrative-brief.md has no fenced ```yaml front section -- the "
            "machine-readable schema is required (fail closed)",
        )
    try:
        data = yaml.safe_load(front)
    except yaml.YAMLError as exc:
        return None, _blocked(
            "malformed_front_section",
            locator,
            f"narrative-brief.md front section is not valid YAML ({exc}) "
            f"-- check blocked (fail closed)",
        )
    if not isinstance(data, dict):
        return None, _blocked(
            "malformed_front_section",
            locator,
            "narrative-brief.md front section is not a YAML mapping "
            "-- check blocked (fail closed)",
        )
    if data.get("schema") != SCHEMA_LITERAL:
        return None, _blocked(
            "wrong_schema",
            locator,
            f"front section schema is {data.get('schema')!r}, expected "
            f"{SCHEMA_LITERAL!r} -- check blocked (fail closed)",
        )
    return data, None


# --------------------------------------------------------------------------- #
# Grounding: the measure ids a question may cite
# --------------------------------------------------------------------------- #
#
# v1 SCOPE (see phase-c-verification.md): grounding is enforced for MEASURE
# cites only -- ``cites.measures`` MUST be among the brief's declared approved
# contracts. DIMENSION-grounding-against-the-profile is deliberately OUT of v1:
# a brief cites a dimension as a semantic-model reference (dotted
# ``entity.attribute``), but the committed source-profile carries only bare
# source columns in a pipe table (see mappings/*/source-profile.md); resolving
# one to the other requires a THIRD artifact (the semantic model / mapping)
# that the frozen two-input rule forbids. Rather than fake a grounding it cannot
# verify -- which false-flagged EVERY real brief with the earlier dotted-bullet
# regex -- the checker does not ground-check dimension cites in v1. This is the
# same "check only what the inputs support" posture as the deferred
# visual<->question binding-map check. The frozen schema's dotted-dimension
# grammar vs the bare-column profile format is a recorded inconsistency for the
# owner (phase-c-verification.md), not something this checker guesses past.


def _grounded_measure_ids(data: dict[str, Any]) -> set[str]:
    """Contract ids from the brief's ``contracts`` block -- the set a
    ``cites.measures`` entry must be drawn from (grounded-only, v1)."""
    contracts = data.get("contracts") or []
    return {
        c["id"]
        for c in contracts
        if isinstance(c, dict) and isinstance(c.get("id"), str)
    }


# --------------------------------------------------------------------------- #
# The revision guard (stale-citation, same posture as dbt model citations)
# --------------------------------------------------------------------------- #


def _blob_sha(repo_root: Path, contract_path: Path) -> str | None:
    """The git blob sha of the contract's CURRENT content, via the hardened
    read-only probe. None when git is unavailable or the file is missing --
    the caller treats an unverifiable revision as a finding, never a pass."""
    if not contract_path.is_file():
        return None
    result = run_git(repo_root, "hash-object", str(contract_path))
    return result.stdout.strip() if result.returncode == 0 else None


def _check_contract_revisions(
    data: dict[str, Any], repo_root: Path, table: str
) -> list[NarrativeFinding]:
    findings: list[NarrativeFinding] = []
    for contract in data.get("contracts") or []:
        if not isinstance(contract, dict):
            continue
        cid = contract.get("id")
        declared = contract.get("revision")
        contract_path = repo_root / "mappings" / table / "contracts" / f"{cid}.yaml"
        actual = _blob_sha(repo_root, contract_path)
        if actual is None:
            findings.append(
                NarrativeFinding(
                    "stale_contract_revision",
                    str(cid),
                    f"contract {cid!r} cited by the brief cannot be located at "
                    f"{contract_path} to verify its revision (fail closed)",
                )
            )
        elif str(declared) != actual:
            findings.append(
                NarrativeFinding(
                    "stale_contract_revision",
                    str(cid),
                    f"contract {cid!r} revision in the brief ({declared}) does "
                    f"not match the committed contract's current blob ({actual}) "
                    f"-- the citation is STALE",
                )
            )
    return findings


# --------------------------------------------------------------------------- #
# Per-question schema checks
# --------------------------------------------------------------------------- #


def _cited_measures(question: dict[str, Any]) -> list[str]:
    cites = question.get("cites") or {}
    if not isinstance(cites, dict):
        return []
    return [m for m in (cites.get("measures") or []) if isinstance(m, str)]


def _check_stage(qid: str, stage: Any) -> list[NarrativeFinding]:
    if stage in _STAGES:
        return []
    return [
        NarrativeFinding(
            "invalid_stage",
            qid,
            f"question {qid} stage is {stage!r}; must be one of {_STAGES}",
        )
    ]


def _is_nonempty_str(value: Any) -> bool:
    """True for a string with non-whitespace content (a stated value)."""
    return isinstance(value, str) and bool(value.strip())


def _names_comparison(value: Any) -> bool:
    """True when ``value`` is a stated comparison, i.e. a non-empty string that
    is not the literal ``none`` -- the headline rule's condition, named so it is
    a single predicate rather than a complex inline conditional."""
    return _is_nonempty_str(value) and value.strip().lower() != "none"


def _check_callout(qid: str, question: dict[str, Any]) -> list[NarrativeFinding]:
    if _is_nonempty_str(question.get("callout")):
        return []
    return [
        NarrativeFinding("empty_callout", qid, f"question {qid} has an empty callout")
    ]


def _check_headline(
    qid: str, stage: Any, question: dict[str, Any]
) -> list[NarrativeFinding]:
    """Headline rule (FR-006): an overview question MUST name a comparison."""
    if stage != "overview":
        return []
    comparison = question.get("comparison")
    if _names_comparison(comparison):
        return []
    return [
        NarrativeFinding(
            "bare_total_headline",
            qid,
            f"overview question {qid} has comparison {comparison!r}; a headline "
            f"MUST name a comparison -- a bare total is a defect",
        )
    ]


def _check_framing(qid: str, question: dict[str, Any]) -> list[NarrativeFinding]:
    """The framing must be one of the eight cards; a guardrail-bearing framing
    must state a named ``guardrail.basis`` (FR-002a). Validating the literal
    first stops a typo from silently escaping the guardrail rule."""
    framing = question.get("framing")
    if framing not in _ALL_FRAMINGS:
        return [
            NarrativeFinding(
                "invalid_framing",
                qid,
                f"question {qid} framing is {framing!r}; must be one of the eight "
                f"framing cards {sorted(_ALL_FRAMINGS)}",
            )
        ]
    if framing not in _GUARDRAIL_FRAMINGS:
        return []
    guardrail = question.get("guardrail") or {}
    basis = guardrail.get("basis") if isinstance(guardrail, dict) else None
    if _is_nonempty_str(basis):
        return []
    return [
        NarrativeFinding(
            "missing_guardrail_basis",
            qid,
            f"question {qid} uses guardrail-bearing framing {framing!r} but states "
            f"no guardrail.basis -- a claim with no basis is a defect (the checker "
            f"asserts presence, not wisdom)",
        )
    ]


def _check_measure_grounding(
    qid: str, question: dict[str, Any], measure_ids: set[str]
) -> list[NarrativeFinding]:
    """Grounded-only (v1): every cited MEASURE must be a declared contract.
    Dimension cites are not ground-checked in v1 (see module note)."""
    return [
        NarrativeFinding(
            "ungrounded_cite",
            qid,
            f"question {qid} cites measure {m!r}, not among the brief's declared "
            f"approved contracts",
        )
        for m in _cited_measures(question)
        if m not in measure_ids
    ]


def _check_gap_not_framed(
    qid: str, question: dict[str, Any], gap_questions: set[str]
) -> list[NarrativeFinding]:
    decision = question.get("decision")
    if isinstance(decision, str) and decision.strip() in gap_questions:
        return [
            NarrativeFinding(
                "gap_framed_as_question",
                qid,
                f"question {qid} frames a decision also listed as a [GAP] -- you "
                f"cannot frame what the data cannot answer",
            )
        ]
    return []


def _check_question(
    question: dict[str, Any],
    measure_ids: set[str],
    gap_questions: set[str],
) -> list[NarrativeFinding]:
    qid = str(question.get("id", "<no id>"))
    stage = question.get("stage")
    findings: list[NarrativeFinding] = []
    findings += _check_stage(qid, stage)
    findings += _check_callout(qid, question)
    findings += _check_headline(qid, stage, question)
    findings += _check_framing(qid, question)
    findings += _check_measure_grounding(qid, question, measure_ids)
    findings += _check_gap_not_framed(qid, question, gap_questions)
    return findings


# --------------------------------------------------------------------------- #
# story_order structural checks
# --------------------------------------------------------------------------- #


def _check_story_order(
    data: dict[str, Any], question_stage: dict[str, Any]
) -> list[NarrativeFinding]:
    findings: list[NarrativeFinding] = []
    story = data.get("story_order")
    if not isinstance(story, dict) or any(k not in story for k in _STAGES):
        findings.append(
            NarrativeFinding(
                "story_order_incomplete",
                "story_order",
                f"story_order MUST contain all four stage keys {_STAGES}",
            )
        )
        return findings  # can't reason further without all keys

    if not (story.get("overview") or []):
        findings.append(
            NarrativeFinding(
                "empty_overview",
                "story_order.overview",
                "story_order.overview is empty -- a report with no overview is "
                "a defect",
            )
        )

    placed: dict[str, str] = {}
    for stage in _STAGES:
        findings += _place_stage(stage, story.get(stage), placed, question_stage)

    findings += [
        NarrativeFinding(
            "story_order_mismatch",
            qid,
            f"question {qid} (stage {stage!r}) is missing from story_order (orphan id)",
        )
        for qid, stage in question_stage.items()
        if qid not in placed
    ]
    return findings


def _place_stage(
    stage: str,
    ids: Any,
    placed: dict[str, str],
    question_stage: dict[str, Any],
) -> list[NarrativeFinding]:
    """Record every question id under ``stage`` into ``placed`` (mutated), and
    return findings for a non-list stage value, a duplicate placement, a phantom
    id, or a declared-stage mismatch."""
    if not isinstance(ids, list):
        return [
            NarrativeFinding(
                "story_order_not_a_list",
                f"story_order.{stage}",
                f"story_order.{stage} is {ids!r}; each stage value MUST be a list "
                f"of question ids (a scalar is a defect -- did you omit the "
                f"brackets?)",
            )
        ]
    findings: list[NarrativeFinding] = []
    for raw in ids:
        qid = str(raw)
        if qid in placed:
            findings.append(
                NarrativeFinding(
                    "story_order_mismatch",
                    qid,
                    f"question {qid} appears in more than one story_order stage "
                    f"({placed[qid]} and {stage})",
                )
            )
            continue
        placed[qid] = stage
        if qid not in question_stage:
            findings.append(
                NarrativeFinding(
                    "story_order_mismatch",
                    qid,
                    f"story_order.{stage} lists {qid}, which is not a declared "
                    f"question (phantom id)",
                )
            )
        elif question_stage[qid] != stage:
            findings.append(
                NarrativeFinding(
                    "story_order_mismatch",
                    qid,
                    f"question {qid} declares stage {question_stage[qid]!r} but "
                    f"story_order places it under {stage!r}",
                )
            )
    return findings


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #


def _gap_question_texts(data: dict[str, Any]) -> set[str]:
    return {
        g["question"].strip()
        for g in (data.get("gaps") or [])
        if isinstance(g, dict) and isinstance(g.get("question"), str)
    }


def _question_stage_map(questions: Any) -> dict[str, Any]:
    """``{id: stage}`` for every question carrying an id. A later duplicate id
    overwrites -- the collision itself is reported by ``_check_question_ids``,
    so this map is only used for story-order cross-referencing."""
    return {
        str(q["id"]): q.get("stage")
        for q in questions
        if isinstance(q, dict) and "id" in q
    }


def _check_question_ids(questions: Any) -> list[NarrativeFinding]:
    """Every question MUST carry a UNIQUE id (schema: the id is the stable
    binding-map reference). A missing id or a duplicate id is a defect -- a
    duplicate would otherwise silently collapse in the stage map and pass
    unchecked."""
    findings: list[NarrativeFinding] = []
    seen: set[str] = set()
    for index, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        if "id" not in q or not str(q.get("id")).strip():
            findings.append(
                NarrativeFinding(
                    "missing_question_id",
                    f"questions[{index}]",
                    f"question at index {index} has no id -- every question needs "
                    f"a stable id (it is the binding-map reference)",
                )
            )
            continue
        qid = str(q["id"])
        if qid in seen:
            findings.append(
                NarrativeFinding(
                    "duplicate_question_id",
                    qid,
                    f"question id {qid!r} is used by more than one question -- ids "
                    f"MUST be unique (rank and the binding-map reference are "
                    f"otherwise ambiguous)",
                )
            )
        seen.add(qid)
    return findings


def check_narrative(*, table: str, repo_root: Path) -> NarrativeCheckResult:
    """Validate ``mappings/<table>/narrative-brief.md`` against the frozen
    schema. READ-ONLY: opens nothing for write, sets no readiness stage. Returns
    evidence + findings only -- ``grants_approval`` is always False."""
    repo_root = Path(repo_root)
    brief_path = repo_root / "mappings" / table / "narrative-brief.md"

    data, failure = _load_front(brief_path)
    if failure is not None:
        return failure
    assert data is not None  # narrowing for type-checkers; _load_front's contract

    measure_ids = _grounded_measure_ids(data)
    gap_questions = _gap_question_texts(data)

    findings: list[NarrativeFinding] = []
    findings.extend(_check_contract_revisions(data, repo_root, table))

    questions = data.get("questions") or []
    findings.extend(_check_question_ids(questions))
    question_stage = _question_stage_map(questions)
    for question in questions:
        if isinstance(question, dict):
            findings.extend(_check_question(question, measure_ids, gap_questions))

    findings.extend(_check_story_order(data, question_stage))

    if "gaps" not in data:
        findings.append(
            NarrativeFinding(
                "missing_gaps_key",
                str(brief_path),
                "front section has no `gaps` key -- it is REQUIRED (an empty "
                "list is allowed, its absence is not)",
            )
        )

    evidence = (
        f"narrative brief: {brief_path}",
        f"{len(questions)} question(s) checked against {len(measure_ids)} "
        f"declared contract(s)",
        "this is EVIDENCE for the named human design review and grants NO "
        "approval; dimension-cite grounding and the visual<->question "
        "binding-map check are out of v1 scope (see phase-c-verification.md)",
    )
    return NarrativeCheckResult(
        status="blocked" if findings else "pass",
        findings=tuple(findings),
        evidence=evidence,
        grants_approval=False,
    )


# --------------------------------------------------------------------------- #
# Phase B (T010): the three-way binding-map check
# (visual -> contract -> decision-question)
# --------------------------------------------------------------------------- #
#
# The narrative BRIEF (above) declares ranked owner decision-questions with
# stable ids (Q1, Q2, ...). Phase B's dashboard-design upgrade authors a
# three-way binding map at ``mappings/<table>/design/
# visual-contract-binding-map.md`` with a machine-readable
# ``seshat.binding-map/v1`` front section, where every measure-bearing visual
# names the ONE approved contract it binds (the F011 leg, unchanged) AND the
# brief decision-question(s) it answers (the NEW three-way leg -- a list, since
# one visual may serve more than one owner decision, e.g. a basket-value card
# that is both a headline number and the basket-value answer). This checker reads
# that map and the brief it references and reports:
#
#   - ``orphan_visual``          (FR-005, orphan in EITHER direction): a visual
#                                whose ``contract`` is missing or not a declared
#                                approved contract, OR whose ``decision_questions``
#                                is empty or names an id the brief does not declare
#                                -- a visual not fully bound to (approved contract,
#                                owner decision) is a defect.
#   - ``unanswered_question``    (FR-005, the other direction): a brief
#                                decision-question that NO visual answers -- a
#                                ranked owner decision the design does not inform.
#   - ``page_missing_question``:  a declared page carrying no question-bearing
#                                visual -- a page must serve >=1 owner decision.
#   - ``bare_total_headline_visual`` (FR-006): a ``headline: true`` (KPI-card
#                                class) visual answering NO overview-stage
#                                question. The brief already forces every overview
#                                question to NAME a comparison (``_check_headline``);
#                                binding a headline visual to an overview question
#                                is therefore how "a headline carries a comparison"
#                                becomes checkable here without duplicating the
#                                brief's rule.
#
# Fail-closed (FR-008), consistent with the brief-check posture: a missing,
# unreadable, or schema-invalid map -- or an absent brief it references -- is a
# ``blocked`` finding naming the problem, never a silent pass over an absent map.
# Phase C left map-absence OUT of scope (the map did not exist yet); Phase B
# flips that: a design gated on the brief but shipping no committed map is not
# reviewable. READ-ONLY; ``grants_approval`` is structurally always False.


def _load_binding_map_front(
    map_path: Path,
) -> tuple[dict[str, Any] | None, NarrativeCheckResult | None]:
    """The parsed binding-map front section, or the fail-closed result naming why
    it could not be produced (missing / unreadable / no fence / malformed /
    non-mapping / wrong schema literal). Same fail-closed posture as the brief."""
    locator = str(map_path)
    if not map_path.is_file():
        return None, _blocked(
            "missing_binding_map",
            locator,
            f"no visual-contract-binding-map.md at {map_path} -- nothing to check "
            f"(fail closed); author the three-way map via dashboard-design first",
        )
    try:
        text = map_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None, _blocked(
            "unreadable_binding_map",
            locator,
            "visual-contract-binding-map.md is unreadable -- check blocked "
            "(fail closed)",
        )
    front = _extract_front_section(text)
    if front is None:
        return None, _blocked(
            "no_front_section",
            locator,
            "visual-contract-binding-map.md has no fenced ```yaml front section "
            "-- the machine-readable three-way map is required (fail closed)",
        )
    try:
        data = yaml.safe_load(front)
    except yaml.YAMLError as exc:
        return None, _blocked(
            "malformed_front_section",
            locator,
            f"visual-contract-binding-map.md front section is not valid YAML "
            f"({exc}) -- check blocked (fail closed)",
        )
    if not isinstance(data, dict):
        return None, _blocked(
            "malformed_front_section",
            locator,
            "visual-contract-binding-map.md front section is not a YAML mapping "
            "-- check blocked (fail closed)",
        )
    if data.get("schema") != BINDING_MAP_SCHEMA_LITERAL:
        return None, _blocked(
            "wrong_schema",
            locator,
            f"front section schema is {data.get('schema')!r}, expected "
            f"{BINDING_MAP_SCHEMA_LITERAL!r} -- check blocked (fail closed)",
        )
    return data, None


class _BriefGrounding(NamedTuple):
    """The two grounding sets a binding map must reach into: the brief's declared
    questions (``{id: stage}``) and its declared approved contract ids. A visual
    is an orphan unless BOTH its decision-question(s) AND its contract are in
    these sets (FR-005, orphan in either direction)."""

    question_stage: dict[str, Any]
    contract_ids: set[str]


def _load_brief_grounding(brief_path: Path) -> _BriefGrounding | NarrativeCheckResult:
    """The brief grounding (declared questions + declared contracts) the binding
    map is checked against, or a fail-closed result if the brief cannot be
    loaded. The map's question ids AND contract names MUST ground against the
    brief; an absent/malformed brief means neither can be verified -> fail
    closed."""
    data, failure = _load_front(brief_path)
    if failure is not None:
        # Keep the fail-closed posture and the original (brief-side) message.
        return failure
    assert data is not None
    return _BriefGrounding(
        question_stage=_question_stage_map(data.get("questions") or []),
        contract_ids=_grounded_measure_ids(data),
    )


def _visual_locator(visual: dict[str, Any], index: int) -> str:
    vid = visual.get("visual_id")
    return str(vid) if _is_nonempty_str(vid) else f"visuals[{index}]"


def _visual_questions(visual: dict[str, Any]) -> list[str]:
    """The decision-question id(s) a visual answers, as a list of non-empty
    strings. Accepts ``decision_questions`` (a list -- the canonical form; one
    visual may answer more than one owner decision, e.g. a basket-value card
    that serves both a headline question and a basket-value question) OR the
    scalar ``decision_question`` convenience (a single id). A visual with
    neither is an orphan (empty list)."""
    plural = visual.get("decision_questions")
    if isinstance(plural, list):
        return [q.strip() for q in plural if _is_nonempty_str(q)]
    singular = visual.get("decision_question")
    return [singular.strip()] if _is_nonempty_str(singular) else []


def _page_id(page: Any) -> str | None:
    """The id of a declared page. A page may be a bare string id, or a mapping
    ``{id: <str>, regions: [...]}`` (the layout carries regions per page); both
    forms are supported so the map can mirror the real single-page/regions
    layout."""
    if _is_nonempty_str(page):
        return page.strip()
    if isinstance(page, dict) and _is_nonempty_str(page.get("id")):
        return page["id"].strip()
    return None


def _check_visual_contract(
    visual: dict[str, Any], locator: str, contract_ids: set[str]
) -> list[NarrativeFinding]:
    """The CONTRACT leg (FR-005, orphan in either direction): the visual's
    ``contract`` MUST be present AND be one of the brief's declared approved
    contracts. This is the F011 two-way binding, now enforced on the
    machine-readable map section (the old markdown table got human review; this
    YAML did not)."""
    contract = visual.get("contract")
    if not _is_nonempty_str(contract):
        return [
            NarrativeFinding(
                "orphan_visual",
                locator,
                f"visual {locator} names no contract -- every visual MUST bind to "
                f"exactly one approved contract (orphan, FR-005)",
            )
        ]
    if contract.strip() not in contract_ids:
        return [
            NarrativeFinding(
                "orphan_visual",
                locator,
                f"visual {locator} binds contract {contract.strip()!r}, which is "
                f"not a declared approved contract in the brief -- the map cannot "
                f"bind a visual to a metric the brief never approved (orphan, "
                f"FR-005)",
            )
        ]
    return []


def _check_visual_binding(
    visual: dict[str, Any],
    index: int,
    grounding: _BriefGrounding,
) -> list[NarrativeFinding]:
    """Per-visual three-way checks: the ``contract`` must be a declared approved
    contract AND every ``decision_question`` must be a declared brief question id
    (orphan check in either direction, FR-005); a headline visual must answer at
    least one overview-stage question (FR-006)."""
    locator = _visual_locator(visual, index)
    question_stage = grounding.question_stage
    findings = _check_visual_contract(visual, locator, grounding.contract_ids)
    questions = _visual_questions(visual)
    if not questions:
        findings.append(
            NarrativeFinding(
                "orphan_visual",
                locator,
                f"visual {locator} names no decision_question -- a visual bound to "
                f"a contract but answering no owner decision is an orphan (FR-005)",
            )
        )
        return findings
    findings += [
        NarrativeFinding(
            "orphan_visual",
            locator,
            f"visual {locator} cites decision_question {dq!r}, which is not a "
            f"declared question in the brief -- the map cannot reach past the "
            f"brief's questions (orphan, FR-005)",
        )
        for dq in questions
        if dq not in question_stage
    ]
    grounded = [dq for dq in questions if dq in question_stage]
    if visual.get("headline") is True and not any(
        question_stage.get(dq) == "overview" for dq in grounded
    ):
        stages = {dq: question_stage.get(dq) for dq in grounded}
        findings.append(
            NarrativeFinding(
                "bare_total_headline_visual",
                locator,
                f"headline visual {locator} answers {grounded or questions} "
                f"(stages {stages}); a headline (KPI-card class) visual MUST answer "
                f"an overview question that names a comparison -- a bare total on "
                f"the headline is a defect (FR-006)",
            )
        )
    return findings


def _check_page_coverage(
    visuals: list[dict[str, Any]],
    declared_pages: list[Any],
    question_stage: dict[str, Any],
) -> list[NarrativeFinding]:
    """Every declared page MUST carry >=1 visual answering a declared brief
    question -- a page serving no owner decision is a coverage defect."""
    served: set[str] = set()
    for visual in visuals:
        page = _page_id(visual.get("page"))
        if page is not None and any(
            dq in question_stage for dq in _visual_questions(visual)
        ):
            served.add(page)
    return [
        NarrativeFinding(
            "page_missing_question",
            page_id,
            f"page {page_id!r} carries no visual bound to a decision-question -- a "
            f"page must serve at least one owner decision (coverage defect)",
        )
        for page_id in (_page_id(p) for p in declared_pages)
        if page_id is not None and page_id not in served
    ]


def _check_unanswered_questions(
    visuals: list[dict[str, Any]],
    question_stage: dict[str, Any],
) -> list[NarrativeFinding]:
    """The OTHER orphan direction (FR-005, "orphan in either direction"): every
    brief decision-question MUST be answered by >=1 visual. A ranked owner
    question the design serves NO visual for is an orphan question -- the analysis
    declared a decision it then does not inform."""
    answered = {
        dq
        for visual in visuals
        for dq in _visual_questions(visual)
        if dq in question_stage
    }
    return [
        NarrativeFinding(
            "unanswered_question",
            qid,
            f"brief decision-question {qid!r} (stage {question_stage[qid]!r}) is "
            f"answered by no visual -- a ranked owner decision the design does not "
            f"inform is an orphan question (FR-005)",
        )
        for qid in question_stage
        if qid not in answered
    ]


def check_binding_map(*, table: str, repo_root: Path) -> NarrativeCheckResult:
    """Validate the three-way binding map at ``mappings/<table>/design/
    visual-contract-binding-map.md`` against ``seshat.binding-map/v1`` and the
    brief it references. READ-ONLY: opens nothing for write, sets no readiness
    stage. Returns evidence + findings only -- ``grants_approval`` always False.

    Fail-closed on a missing/unreadable/schema-invalid map or an absent
    referenced brief (FR-008); never a silent pass over an absent map."""
    repo_root = Path(repo_root)
    map_path = (
        repo_root / "mappings" / table / "design" / "visual-contract-binding-map.md"
    )

    data, failure = _load_binding_map_front(map_path)
    if failure is not None:
        return failure
    assert data is not None

    brief_ref = data.get("brief")
    brief_path = (
        repo_root / brief_ref
        if _is_nonempty_str(brief_ref)
        else repo_root / "mappings" / table / "narrative-brief.md"
    )
    grounding = _load_brief_grounding(brief_path)
    if isinstance(grounding, NarrativeCheckResult):
        return grounding
    question_stage = grounding.question_stage

    visuals = [v for v in (data.get("visuals") or []) if isinstance(v, dict)]
    declared_pages = data.get("pages") or []

    findings: list[NarrativeFinding] = []
    for index, visual in enumerate(visuals):
        findings.extend(_check_visual_binding(visual, index, grounding))
    findings.extend(_check_page_coverage(visuals, declared_pages, question_stage))
    findings.extend(_check_unanswered_questions(visuals, question_stage))

    evidence = (
        f"three-way binding map: {map_path}",
        f"{len(visuals)} visual(s) checked against {len(question_stage)} "
        f"declared brief question(s) and {len(grounding.contract_ids)} declared "
        f"contract(s) at {brief_path}",
        "this is EVIDENCE for the named human design review and grants NO "
        "approval; it asserts the map's structure (visual -> contract -> "
        "decision-question), never the wisdom of the analysis",
    )
    return NarrativeCheckResult(
        status="blocked" if findings else "pass",
        findings=tuple(findings),
        evidence=evidence,
        grants_approval=False,
    )


def narrative_check_main(args: object) -> int:
    """CLI entry: ``seshat narrative-check``. Read-only: prints the check report
    (text or json) and exits non-zero on any finding -- it never writes a file
    and never grants any readiness stage.

    Default mode checks the narrative BRIEF; ``--binding-map`` (Phase B,
    design-stage mode) checks the three-way binding map instead. The map check is
    opt-in so a brief-stage caller (US1: a brief exists, no map yet) is not
    broken by map-absence fail-close.

    Exit: 0 = pass (structurally sound); 1 = blocked (findings, or a fail-closed
    input problem). A clean exit is EVIDENCE, never an approval."""
    import json as _json

    repo_root = Path(getattr(args, "report", ".") or ".")
    table = getattr(args, "table")  # type: ignore[arg-type]
    if getattr(args, "binding_map", False):
        result = check_binding_map(table=table, repo_root=repo_root)
    else:
        result = check_narrative(table=table, repo_root=repo_root)
    fmt = getattr(args, "format", "text")

    if fmt == "json":
        print(
            _json.dumps(
                {
                    "status": result.status,
                    "grants_approval": result.grants_approval,
                    "findings": [f._asdict() for f in result.findings],
                    "evidence": list(result.evidence),
                },
                indent=2,
            )
        )
    else:
        print(f"status: {result.status}")
        for finding in result.findings:
            print(
                f"[finding] {finding.dimension}: {finding.message} ({finding.locator})"
            )
        for line in result.evidence:
            print(f"evidence: {line}")
        print(
            "note: this is a read-only narrative-brief check; it grants no "
            "approval and never sets a readiness stage."
        )
    return 1 if result.status == "blocked" else 0
