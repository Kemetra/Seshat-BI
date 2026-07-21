"""Read-only orchestration-adoption assessment (issue #401).

The readiness spine already refuses to auto-decide business questions -- it
recommends, and a named human approves. Adopting an orchestration adapter (dbt
for shadow-parity transformation, dagster for gated unattended runs) is the same
shape of question: a real choice with trade-offs and no universally-correct
answer. This module gives it the same treatment -- **assess -> recommend -> the
human decides** -- so the customer with one direct-built table isn't pushed into
ceremony they don't need, and the customer who would benefit gets a signal.

What this engine can and cannot know from committed state:

  - DERIVABLE (offline, no DB, no network): how many tables are onboarded
    (``mappings/*/readiness-status.yaml``), whether every onboarded table has
    already reached ``gold_ready``, and whether a dbt / dagster project is
    already present in the workspace.
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

_DBT_OPT_IN = "pip install 'seshat-bi[dbt]'  (then: seshat dbt doctor)"
_DAGSTER_OPT_IN = "seshat dagster init  (then: seshat dagster doctor)"

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


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


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


def _is_gold_ready(data: dict) -> bool:
    """A table has reached gold when its ``gold_ready`` stage status is ``pass``
    (or ``current_stage`` is at/after gold). Read verbatim -- never derived."""
    stages = data.get("stages")
    if isinstance(stages, dict):
        block = stages.get("gold_ready")
        if isinstance(block, dict) and block.get("status") == "pass":
            return True
    return _as_str(data.get("current_stage")) in {
        "gold_ready",
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    }


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
    )


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
        acc.against.append(
            "Single table (or none) -- there is no multi-step run graph to "
            "orchestrate; a direct build is enough."
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


def _recommended_action(
    s: _WorkspaceSignals, dbt: _AdapterAssessment, dagster: _AdapterAssessment
) -> str:
    """One plain-language headline. Strongly asserts the derivable
    "neither needed" case (the C086 case) with a concrete revisit trigger; stays
    a recommendation, never a decision, everywhere else."""
    if s.table_count == 0:
        return (
            "No tables onboarded yet -- orchestration is NOT required; revisit "
            "this after your first table reaches Gold and you add a second."
        )
    if (
        s.table_count == 1
        and s.all_tables_gold
        and not s.dbt_present
        and not s.dagster_present
    ):
        return (
            "Single governed table, direct build already Gold-validated -> "
            "orchestration NOT required; revisit when you add a 2nd table or "
            "need scheduled runs."
        )
    considered = [
        name
        for name, a in (("dbt", dbt), ("dagster", dagster))
        if a.recommendation == _CONSIDER
    ]
    if considered:
        return (
            f"{s.table_count} tables onboarded -- {', '.join(considered)} may be "
            "worth adopting; review the signals below, then YOU decide "
            "(the tool never adopts on your behalf); revisit as the portfolio grows."
        )
    return (
        f"{s.table_count} tables onboarded -- no orchestration adapter is "
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
    return {
        "table_count": signals.table_count,
        "gold_ready_count": signals.gold_ready_count,
        "decision_owner": "human",
        "recommendation": {
            "dbt": dbt.recommendation,
            "dagster": dagster.recommendation,
        },
        "recommended_action": _recommended_action(signals, dbt, dagster),
        "adapters": {"dbt": dbt.to_dict(), "dagster": dagster.to_dict()},
        "read_only_proof": True,
    }
