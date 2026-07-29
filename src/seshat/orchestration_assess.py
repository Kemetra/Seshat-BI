"""Read-only orchestration-adoption assessment (issue #401).

The readiness spine already refuses to auto-decide business questions -- it
recommends, and a named human approves. Adopting an adapter (dbt for
shadow-parity transformation, dagster for gated unattended runs, the Power BI
MCP read-only diagnostics family) is the same shape of question: a real choice
with trade-offs and no universally-correct
answer. This module gives it the same treatment -- **assess -> recommend -> the
human decides** -- so the customer with one direct-built table isn't pushed into
ceremony they don't need, and the customer who would benefit gets a signal.

What this engine can and cannot know from committed state:

  - DERIVABLE (offline, no DB, no network): how many tables are onboarded
    (``mappings/*/readiness-status.yaml``), whether every onboarded table has
    already reached ``gold_ready``, whether a dbt / dagster project is already
    present, whether a PBIP semantic model is committed (bounded probe), and how
    ``.mcp.json`` CLASSIFIES via ``pbi_mcp.detect.classify_mcp_config`` -- its mere
    presence is not Power BI adoption.
  - NOT DERIVABLE: whether the customer needs *scheduled / unattended* runs,
    whether there are cross-table run dependencies, or whether the team already
    speaks dbt. Those are INTENTIONS. This engine surfaces them as
    ``open_questions`` for the human, never as a fabricated verdict.

Hard invariants (mirroring ``status_surface`` / ``blocker_explainer``):
  - Read-only: globs and reads committed YAML; writes nothing, opens no DB
    connection, makes no network call. It NEVER installs or runs an adapter.
  - Recommend, never decide: ``decision_owner`` is always ``"human"``; the
    per-adapter ``recommendation`` is a categorical hint, not an approval.
  - Never a numeric score: only categorical verdicts and named string signals
    (hard rule #9, Principle V).
  - Best-effort: a malformed committed status file is skipped, not fatal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# The canonical project roots the governed scaffolders write (governed_projects.py):
# ``seshat dbt`` needs ``<root>/dbt/dbt_project.yml``; the dagster adapter needs
# ``<root>/orchestration/dagster/pyproject.toml``. Presence of either marker is the
# offline "already adopted" signal.
_DBT_PROJECT_MARKER = ("dbt", "dbt_project.yml")
_DAGSTER_PROJECT_MARKER = ("orchestration", "dagster", "pyproject.toml")

# Full opt-in sequence: install the extra, MATERIALIZE the governed project
# (`seshat dbt init` -- doctor's `_verify_required_paths` needs dbt_project.yml /
# selectors.yml, absent in a marker-free workspace), THEN check prerequisites.
# Omitting `dbt init` would make the very next `dbt doctor` fail on missing
# project files (#401 review).
_DBT_OPT_IN = "pip install 'seshat-bi[dbt]'  (then: seshat dbt init; seshat dbt doctor)"
_DAGSTER_OPT_IN = "seshat dagster init  (then: seshat dagster doctor)"

# The Power BI MCP opt-in is the READ-ONLY doctor family and nothing else. ADR
# 0018 is Proposed and NOT ratified, so F016 execution stays parked; advertising
# any state-changing mode here would be advising a capability the governing ADR
# has not authorized (Principle V, never_self_grant_approval).
_PBI_MCP_OPT_IN = (
    "seshat pbi-mcp doctor  (then: pbi-mcp generate-config; pbi-mcp preflight "
    "-- the read-only family)"
)

# `.mcp.json` presence says NOTHING about Power BI: the file may hold only an
# unrelated MCP server, or be malformed. `pbi_mcp.detect` already owns both
# questions -- `classify_mcp_config` returns `absent` when no Power BI-shaped
# server exists, and `_pbip_project_present` is a BOUNDED probe (three levels,
# never a full-tree walk). Reuse both rather than re-deriving them here.
_MCP_CONFIG = ".mcp.json"

# Config verdicts that do NOT evidence adoption of a Power BI server.
_CONFIG_NOT_ADOPTED = ("absent", "unparseable")
# Config verdicts that ARE adoption but request a state-changing mode.
_CONFIG_STATE_CHANGING = ("write-mode", "forbidden-flag")

# The categorical recommendation vocabulary. There is NO numeric axis, and there
# is deliberately no "recommended" tier: an adapter's value driver (multi-model
# lineage, scheduled/unattended runs) always turns on an intention the tool cannot
# read from committed state, so a state-derived signal is capped at "consider" --
# a weigh-this hint, never an assertion that the customer must adopt.
_CONSIDER = "consider"
_NOT_RECOMMENDED = "not_recommended"
_ALREADY_ADOPTED = "already_adopted"


@dataclass(frozen=True)
class _WorkspaceSignals:
    """The offline, committed-state facts the recommendation is derived from."""

    table_count: int
    gold_ready_count: int
    dbt_present: bool
    dagster_present: bool
    # Defaulted so any pre-existing constructor call stays valid.
    pbip_present: bool = False
    # The categorical `.mcp.json` verdict from pbi_mcp.detect, NOT a bool:
    # `absent` / `unparseable` do not evidence Power BI adoption.
    mcp_config: str = "absent"

    @property
    def all_tables_gold(self) -> bool:
        return self.table_count > 0 and self.gold_ready_count == self.table_count


@dataclass(frozen=True)
class _AdapterAssessment:
    """One adapter's recommend-then-decide block."""

    recommendation: str
    reasons_for: tuple[str, ...]
    reasons_against: tuple[str, ...]
    open_questions: tuple[str, ...]
    opt_in_command: str
    already_present: bool = False

    def to_dict(self) -> dict:
        return {
            "recommendation": self.recommendation,
            "for": list(self.reasons_for),
            "against": list(self.reasons_against),
            "open_questions": list(self.open_questions),
            "opt_in_command": self.opt_in_command,
            "already_present": self.already_present,
        }


def _load_yaml_mapping(path: Path) -> dict | None:
    """Read + parse one readiness-status.yaml. ``None`` (skip, not fatal) on any
    read/parse/shape failure -- RS1 is the fail-loud gate for a malformed file;
    this projection stays best-effort (mirrors ``status_surface``)."""
    import yaml  # lazy: keep this module's import path stdlib-light

    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


# Stages at or beyond gold_ready. A table that reached one of these later stages
# has, by construction, PASSED gold_ready earlier in the spine.
_GOLD_OR_LATER = frozenset(
    {"gold_ready", "semantic_model_ready", "dashboard_ready", "publish_ready"}
)


def _stage_passed_at_or_after_gold(stage_name: object, block: object) -> bool:
    """True iff ``stage_name`` is at/after gold AND its status block is ``pass``."""
    return (
        stage_name in _GOLD_OR_LATER
        and isinstance(block, dict)
        and block.get("status") == "pass"
    )


def _is_gold_ready(data: dict) -> bool:
    """A table has reached gold ONLY when a stage at/after ``gold_ready`` records a
    ``pass`` status -- read verbatim, never derived.

    ``current_stage`` alone is NOT sufficient: it is a truthful stage LABEL, and a
    table can sit at ``current_stage: gold_ready`` while that stage is still
    ``blocked``/``warning`` (e.g. the committed ``demo_sample_orders`` example).
    Counting the bare label would falsely report a not-yet-validated build as
    Gold-validated and drive a wrong "orchestration not required" headline (#401
    review). Gold is reached ONLY when an at/after-gold stage records ``pass`` --
    NEVER from a ``current_stage`` label alone. A record that omits/mistypes
    ``stages`` but keeps ``current_stage: gold_ready`` carries NO recorded pass or
    evidence, so counting it would fabricate a readiness claim (the kit's
    never-fabricate posture): it returns False. Every committed/template readiness
    record carries a ``stages`` block, so this only ever undercounts a malformed
    record toward "consider orchestration" -- never a false "you don't need it".
    """
    stages = data.get("stages")
    if not isinstance(stages, dict):
        return False
    return any(_stage_passed_at_or_after_gold(n, b) for n, b in stages.items())


def _read_signals(root: Path) -> _WorkspaceSignals:
    """Collect the offline committed-state signals for ``root``. No DB, no net."""
    mappings_dir = root / "mappings"
    table_count = 0
    gold_ready_count = 0
    if mappings_dir.is_dir():
        for status_path in sorted(mappings_dir.glob("*/readiness-status.yaml")):
            data = _load_yaml_mapping(status_path)
            if data is None:
                continue  # malformed -> skipped, not fatal
            table_count += 1
            if _is_gold_ready(data):
                gold_ready_count += 1
    return _WorkspaceSignals(
        table_count=table_count,
        gold_ready_count=gold_ready_count,
        dbt_present=root.joinpath(*_DBT_PROJECT_MARKER).is_file(),
        dagster_present=root.joinpath(*_DAGSTER_PROJECT_MARKER).is_file(),
        pbip_present=_has_semantic_model(root),
        mcp_config=_mcp_config_verdict(root),
    )


def _has_semantic_model(root: Path) -> bool:
    """True when a committed PBIP project is present within three levels of ``root``.

    Delegates to ``pbi_mcp.detect``'s BOUNDED probe (which accepts both a
    ``*.pbip`` pointer and a ``*.SemanticModel`` directory) rather than walking
    the whole tree.
    """
    from .pbi_mcp.detect import _pbip_project_present

    try:
        return _pbip_project_present(root)
    except OSError:
        return False


def _mcp_config_verdict(root: Path) -> str:
    """Classify ``.mcp.json`` through the shipped authority, not by presence."""
    from .pbi_mcp.detect import classify_mcp_config

    try:
        return classify_mcp_config(root / _MCP_CONFIG)
    except OSError:
        return "unparseable"


# ---------------------------------------------------------------------------
# Per-adapter heuristics. Each returns categorical signals only.
# ---------------------------------------------------------------------------


@dataclass
class _Signal:
    """Mutable accumulator used only while composing one adapter block."""

    for_: list[str] = field(default_factory=list)
    against: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


def _assess_dbt(s: _WorkspaceSignals) -> _AdapterAssessment:
    """dbt (shadow-parity transformation) is worth CONSIDERING once there are
    multiple models to keep in lineage + test + cut over. With one table and a
    working direct build it is ceremony, not value -- say so plainly. Whether the
    team already speaks dbt is an intention only the human can answer."""
    if s.dbt_present:
        return _AdapterAssessment(
            recommendation=_ALREADY_ADOPTED,
            reasons_for=("A governed dbt project is already present at dbt/.",),
            reasons_against=(),
            open_questions=(),
            opt_in_command=_DBT_OPT_IN,
            already_present=True,
        )
    acc = _Signal()
    if s.table_count >= 2:
        acc.for_.append(
            f"{s.table_count} tables onboarded -- lineage, tests, and a "
            "shadow-parity cutover start paying off across models."
        )
        recommendation = _CONSIDER
    else:
        acc.against.append(
            "Single table (or none) onboarded -- a one-shot direct SQL build "
            "needs no lineage graph; dbt would be ceremony here."
        )
        recommendation = _NOT_RECOMMENDED
    acc.questions.append(
        "Does your team already speak dbt / expect dbt tests + docs? "
        "(the tool can't read intent -- you decide)"
    )
    return _AdapterAssessment(
        recommendation=recommendation,
        reasons_for=tuple(acc.for_),
        reasons_against=tuple(acc.against),
        open_questions=tuple(acc.questions),
        opt_in_command=_DBT_OPT_IN,
    )


def _assess_dagster(s: _WorkspaceSignals) -> _AdapterAssessment:
    """dagster (gated, unattended medallion runs) is about SCHEDULING and
    cross-table run orchestration -- both intentions the tool cannot read from
    committed state. So dagster is never asserted as ``recommended`` from state
    alone: at most ``consider`` (once there are multiple tables that could form a
    run graph), always with the scheduling question left explicitly open."""
    if s.dagster_present:
        return _AdapterAssessment(
            recommendation=_ALREADY_ADOPTED,
            reasons_for=(
                "A governed dagster project is already present at "
                "orchestration/dagster/.",
            ),
            reasons_against=(),
            open_questions=(),
            opt_in_command=_DAGSTER_OPT_IN,
            already_present=True,
        )
    acc = _Signal()
    if s.table_count >= 2:
        acc.for_.append(
            f"{s.table_count} tables -- a multi-step medallion run graph is "
            "possible; orchestration can run it unattended behind the gates."
        )
        recommendation = _CONSIDER
    else:
        # NB: the adapter DOES build a multi-asset graph per table, so the honest
        # reason is not "no graph" -- it is that a single direct build has no
        # CROSS-table run dependency to coordinate; orchestration's remaining draw
        # (scheduled / unattended runs) is the open question surfaced below, not a
        # derivable need (#401 review -- don't claim a false "no graph exists").
        acc.against.append(
            "Single table (or none) -- a direct build has no cross-table run "
            "dependency to coordinate; the only remaining draw is scheduled / "
            "unattended runs, which is the open question below (you decide)."
        )
        recommendation = _NOT_RECOMMENDED
    acc.questions.append(
        "Do you need scheduled / unattended runs, or cross-table run "
        "dependencies? (the tool can't read intent -- you decide)"
    )
    return _AdapterAssessment(
        recommendation=recommendation,
        reasons_for=tuple(acc.for_),
        reasons_against=tuple(acc.against),
        open_questions=tuple(acc.questions),
        opt_in_command=_DAGSTER_OPT_IN,
    )


def _assess_pbi_mcp(s: _WorkspaceSignals) -> _AdapterAssessment:
    """The Power BI MCP adapter's recommend-then-decide block (read-only family).

    Capped at ``consider`` for the same reason dbt and dagster are: whether the
    analyst wants to inspect a LIVE model, and which model is the intended target,
    are INTENTIONS this projection cannot read from committed state.
    """
    if s.mcp_config not in _CONFIG_NOT_ADOPTED:
        # Adopted. If the committed config requests a state-changing mode, say so:
        # warning about the READER'S OWN config is the opposite of advertising it,
        # and ADR 0018 (Proposed, not ratified) has authorized nothing.
        caution: tuple[str, ...] = ()
        if s.mcp_config in _CONFIG_STATE_CHANGING:
            caution = (
                f"{_MCP_CONFIG} classifies as '{s.mcp_config}': it does not pin the "
                "read-only posture. ADR 0018 is Proposed and NOT ratified, so run "
                "`seshat pbi-mcp doctor` and pin read-only before relying on it",
            )
        return _AdapterAssessment(
            recommendation=_ALREADY_ADOPTED,
            reasons_for=(
                f"{_MCP_CONFIG} already configures a Power BI MCP server "
                f"(classified '{s.mcp_config}')",
            ),
            reasons_against=caution,
            open_questions=(),
            opt_in_command=_PBI_MCP_OPT_IN,
            already_present=True,
        )

    if not s.pbip_present:
        return _AdapterAssessment(
            recommendation=_NOT_RECOMMENDED,
            reasons_for=(),
            reasons_against=(
                "no committed PBIP semantic model was found, so the read-only "
                "diagnostics would have nothing to inspect",
            ),
            open_questions=(),
            opt_in_command=_PBI_MCP_OPT_IN,
        )

    return _AdapterAssessment(
        recommendation=_CONSIDER,
        reasons_for=(
            "a committed PBIP semantic model exists, so the read-only "
            "diagnostics have a concrete target",
        ),
        reasons_against=(
            "the read-only family only INSPECTS; it changes nothing, so it earns "
            "its keep only if you actually need the diagnostics",
        ),
        open_questions=(
            "Do you need to inspect a LIVE model (Desktop / Fabric), or is the "
            "committed TMDL enough?",
            "Which semantic model is the intended target?",
        ),
        opt_in_command=_PBI_MCP_OPT_IN,
    )


def _is_single_gold_no_adapter(s: _WorkspaceSignals) -> bool:
    """The strongest "orchestration not required" case: exactly one governed table,
    already Gold-validated, with neither adapter present. Named so the headline's
    conditional stays simple (one predicate, not a 4-way boolean chain)."""
    return (
        s.table_count == 1
        and s.all_tables_gold
        and not s.dbt_present
        and not s.dagster_present
    )


def _recommended_action(
    s: _WorkspaceSignals,
    dbt: _AdapterAssessment,
    dagster: _AdapterAssessment,
    pbi_mcp: _AdapterAssessment | None = None,
) -> str:
    """One plain-language headline. Strongly asserts the derivable
    "neither needed" case (the C086 case) with a concrete revisit trigger; stays
    a recommendation, never a decision, everywhere else."""
    pbi_advised = pbi_mcp is not None and pbi_mcp.recommendation == _CONSIDER
    if s.table_count == 0 and not pbi_advised:
        return (
            "No tables onboarded yet -- orchestration is NOT required; revisit "
            "this after your first table reaches Gold and you add a second."
        )
    if _is_single_gold_no_adapter(s) and not pbi_advised:
        return (
            "Single governed table, direct build already Gold-validated -> "
            "orchestration NOT required; revisit when you add a 2nd table or "
            "need scheduled runs."
        )
    candidates = (("dbt", dbt), ("dagster", dagster))
    if pbi_mcp is not None:
        candidates = candidates + (("the Power BI MCP read-only family", pbi_mcp),)
    considered = [name for name, a in candidates if a.recommendation == _CONSIDER]
    onboarded = f"{s.table_count} table{'' if s.table_count == 1 else 's'} onboarded"
    if considered:
        return (
            f"{onboarded} -- {', '.join(considered)} may be "
            "worth adopting; review the signals below, then YOU decide "
            "(the tool never adopts on your behalf); revisit as the portfolio grows."
        )
    return (
        f"{onboarded} -- no orchestration adapter is "
        "recommended from committed state; revisit as scope grows."
    )


def build_orchestration_assessment(repo_root: Path | str = ".") -> dict:
    """Build the read-only orchestration-adoption assessment for ``repo_root``.

    Returns a recommend-then-decide document: the derived workspace signals, a
    per-adapter block (signals for/against, open questions the human must answer,
    and the concrete opt-in command), a categorical top-level recommendation, and
    a one-line recommended action. Never writes, never a numeric score, never an
    adoption decision (``decision_owner`` is always ``"human"``).
    """
    root = Path(repo_root)
    signals = _read_signals(root)
    dbt = _assess_dbt(signals)
    dagster = _assess_dagster(signals)
    pbi_mcp = _assess_pbi_mcp(signals)
    # "Core only" is not a fourth adapter -- it is the honest answer when none of
    # the three is worth weighing. Derived, so it can never disagree with the
    # per-adapter blocks it is computed from.
    advised = {dbt.recommendation, dagster.recommendation, pbi_mcp.recommendation}
    core_only_sufficient = not (advised & {_CONSIDER, _ALREADY_ADOPTED})
    return {
        "table_count": signals.table_count,
        "gold_ready_count": signals.gold_ready_count,
        "decision_owner": "human",
        "recommendation": {
            "dbt": dbt.recommendation,
            "dagster": dagster.recommendation,
            "pbi_mcp": pbi_mcp.recommendation,
        },
        "core_only_sufficient": core_only_sufficient,
        "recommended_action": _recommended_action(signals, dbt, dagster, pbi_mcp),
        "adapters": {
            "dbt": dbt.to_dict(),
            "dagster": dagster.to_dict(),
            "pbi_mcp": pbi_mcp.to_dict(),
        },
        "read_only_proof": True,
    }
