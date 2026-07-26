"""Agent-facing next-action document (Seshat Agent-Driven v0.1).

``retail next --format agent`` / repo-level ``retail next --format json`` answer
the guarded-agent questions in ONE stable document: what stage is this project
in, what evidence exists, what is blocked, what is the next allowed action, what
is forbidden, and where must the agent stop.

This module is a COMPOSITION, not a second source of truth:

  - the per-table decision (next action / blocked / approval required /
    terminal pass / input defect) is ``seshat.run_next.build_run_next_response``
    (spec 080), reused verbatim;
  - the recorded evidence/status projection is
    ``seshat.status_surface.build_status_projection`` (spec 109), reused
    verbatim;
  - the gate ordering is the seven-stage spine already fixed in
    ``run_next._STAGE_ORDER``.

  - the offline adapter-adoption assessment surfaced at the stages where the
    choice is live is ``seshat.orchestration_assess.build_orchestration_assessment``
    (issue #401), reused verbatim -- also read-only, also no DB, no network.

Contract (same posture as every parent): read-only -- no writes, no DB, no
network; deterministic -- same committed state, byte-identical document; never
a numeric readiness value -- only the four categorical statuses plus named
evidence/blocker strings (hard rule #9, Principle V). When evidence is missing
the document degrades to the conservative evidence-first action (start at
Source Ready), never a fabricated stage.

The no-DB/no-network half of that contract is UNCHANGED by #485/A2, which added a
live-DB provenance comparison to ``run_next``. That comparison reads a committed
record plus the configured DSN *as a string* (the explicitly driver-free
``validate.resolve_dsn``); it opens no connection and no socket. Determinism is
therefore now relative to committed state AND the workspace connection
configuration -- repointing `.env` can change a document, which is precisely the
defect #485 reported.

Two fields are purely INFORMATIONAL guidance, added for issues #488 / #489:
``source_map_shape_signpost`` and ``orchestration_checkpoint``. They exist to make
a downstream requirement and an available option VISIBLE at the stage where the
decision is actually made. Neither is a gate: neither can block, neither appears
in ``blocking_reasons`` or ``forbidden_scope``, neither changes ``outcome`` or
``next_allowed_action``, and neither grants readiness or adopts anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seshat.run_next import (
    _STAGE_ORDER,
    build_run_next_response,
)
from seshat.status_surface import build_status_projection

_STAGE_TITLES: dict[str, str] = {
    "source_ready": "Source Ready (Stage 1)",
    "mapping_ready": "Mapping Ready (Stage 2)",
    "silver_ready": "Silver Ready (Stage 3)",
    "gold_ready": "Gold Ready (Stage 4)",
    "semantic_model_ready": "Semantic Model Ready (Stage 5)",
    "dashboard_ready": "Dashboard Ready (Stage 6)",
    "publish_ready": "Publish Ready (Stage 7)",
}

# One sentence per gate, in spine order: work forbidden until that gate passes.
_GATE_RULES: tuple[tuple[str, str], ...] = (
    (
        "mapping_ready",
        "No silver work (no silver.* SQL) before Mapping Ready passes.",
    ),
    (
        "silver_ready",
        "No gold work (no gold star/mart SQL) before Silver Ready passes.",
    ),
    (
        "gold_ready",
        "No semantic-model work before Gold Ready (live-validated) passes.",
    ),
    (
        "semantic_model_ready",
        "No dashboard work before Semantic Model Ready "
        "(approved metric contracts) passes.",
    ),
    (
        "dashboard_ready",
        "No publish/handoff work before Dashboard Ready passes.",
    ),
    (
        "publish_ready",
        "No live publish before Publish Ready passes; publish execution is "
        "the deferred F016 adapter.",
    ),
)

# Invariants that hold at every stage, including terminal pass.
_ALWAYS_FORBIDDEN: tuple[str, ...] = (
    "Never self-grant an approval; approvals are named-human actions.",
    "Never fabricate readiness; readiness is status + evidence + blockers, "
    "never a number.",
    "Never run the Power BI execution adapter (F016) from this surface.",
)

_BASE_VALIDATION_COMMANDS: tuple[str, ...] = (
    "python -m seshat.cli check --repo .",
    "python -m seshat.cli status --repo . --format json",
    "python -m seshat.cli next --repo . --format json",
)

_VALIDATION_EXTRAS_BY_STAGE: dict[str, tuple[str, ...]] = {
    "gold_ready": (
        "python -m seshat.cli validate --source-map "
        "mappings/<table>/source-map.yaml  # needs the db extra + a DSN; "
        "without them, report the deferred state -- never fake a pass",
    ),
    "semantic_model_ready": ("python -m seshat.cli semantic-check --repo .",),
}

_STOP_POINT_BY_STAGE: dict[str, str] = {
    "source_ready": (
        "Stop once the read-only source profile and readiness-status.yaml are "
        "recorded; mapping review is a human gate."
    ),
    "mapping_ready": (
        "Stop at the mapping gate: source-map.yaml must be reviewed and "
        "approved by a named human before any silver SQL."
    ),
    "silver_ready": (
        "Stop after authoring the silver migration SQL; do not execute it and "
        "do not begin gold work before Silver Ready passes."
    ),
    "gold_ready": (
        "Stop after authoring the gold SQL and preparing live-validate "
        "evidence; Gold Ready passes only on live validation."
    ),
    "semantic_model_ready": (
        "Stop at the metric-contract gate: the metric owner approves the "
        "contracts before any dashboard work."
    ),
    "dashboard_ready": (
        "Stop at the design-review gate: governance approves the dashboard "
        "design before publish preparation."
    ),
    "publish_ready": (
        "Stop before any publish: assemble the handoff pack only; live "
        "publish is the deferred F016 execution adapter."
    ),
}

_TERMINAL_STOP_POINT = (
    "All seven stages pass. Live publish stays with the deferred F016 "
    "execution adapter; nothing further from this surface."
)

# ---------------------------------------------------------------------------
# Issue #488 -- signpost the canonical source-map shape EARLY.
#
# `source-map.yaml`'s canonical shape is enforced only by `seshat validate`, at
# Gold Ready. A map hand-authored at Mapping Ready therefore passes its own gate,
# survives the whole silver/gold build, and fails for the FIRST time as a CLI
# error four stages later (#488's repro). A fail-closed shape rule at Mapping
# Ready cannot land: `mappings/demo_sample_orders/source-map.yaml` is a committed
# gate artifact whose readiness file records passes THROUGH Silver (source_ready,
# mapping_ready, silver_ready) -- yet its map has `gold_star` but NO `meta`, and
# its `gold_star.fact` is a bare STRING where the canonical shape has a mapping.
# So ANY required-shape (or even present-only structural) rule would fire on
# main's own artifact and could not be <no-finding>. The landable half is the
# signpost: name the shape while the map is still being written, so the mismatch
# is discovered at authoring time. Census pinned in
# tests/unit/test_issue_regressions_488_489_deferred.py.
#
# This is guidance, NOT a gate: it never blocks, never changes `forbidden_scope`,
# and never appears in `blocking_reasons`.
#
# MAPPING READY ONLY -- this is a governance boundary, not a UX choice
# (PR #506 review, P1). The signpost carries an imperative to AUTHOR/REPAIR
# source-map.yaml. That is correct at `mapping_ready`, where the artifact is
# legitimately still being written. It is NOT correct at any later stage: once
# Mapping Ready has PASSED, source-map.yaml is an artifact a named human signed
# off on, and `run_next` keeps directing Silver SQL to be authored from it. An
# unqualified "repair the map" imperative there would mutate the approved input
# with no gate reset and no re-approval -- so the approval on record would no
# longer describe what is on disk. `never_self_grant_approval` is not only
# circumvented by CLAIMING an approval; it is circumvented by silently changing
# WHAT WAS APPROVED. Post-approval repair therefore gets no route from this
# surface at all: it is a Mapping Ready RE-ENTRY, which is a human's decision to
# make, not guidance for `next` to offer.
# ---------------------------------------------------------------------------
_SHAPE_SIGNPOST_STAGES: tuple[str, ...] = ("mapping_ready",)


def _source_map_shape_signpost(stage: str | None) -> str | None:
    """The #488 shape signpost, emitted at ``mapping_ready`` ONLY, else ``None``.

    Quotes the ONE shared hint owned by the module that enforces the shape
    (``validate_targets``), so this early mention cannot drift from the late error
    that `seshat validate` prints. Deliberately silent at every post-approval
    stage -- see the governance note above.
    """
    if stage not in _SHAPE_SIGNPOST_STAGES:
        return None
    from seshat.validate_targets import CANONICAL_SOURCE_MAP_SHAPE_HINT

    return (
        f"Author source-map.yaml in {CANONICAL_SOURCE_MAP_SHAPE_HINT} A map that "
        "clears the Mapping Ready review in some other shape still builds silver "
        "and gold, then fails at Gold Ready when `seshat validate` reads it -- "
        "four stages after the shape was decided (issue #488). Decide the shape "
        "now, while the map is still yours to author: once this gate passes, the "
        "map is a signed input and changing it means re-entering Mapping Ready "
        "for a fresh named-human approval."
    )


_FRESH_NEXT_ACTION = (
    "No readiness evidence found under mappings/. Begin at Source Ready: "
    "run `seshat scaffold-source <table>` to write the blank canonical set "
    "(source-profile.md, readiness-status.yaml, source-map.yaml, "
    "assumptions.md, reconciliation-report.md), then fill the source profile "
    "and record mappings/<table>/readiness-status.yaml before any warehouse or "
    "dashboard work. Fill those blanks rather than authoring the files by "
    "hand -- source-map.yaml has a canonical shape later stages require."
)


# ---------------------------------------------------------------------------
# Issue #489 -- surface the dbt / Dagster adapter choice as an INFORMATIONAL
# checkpoint, at the stage where the choice is actually live.
#
# `seshat orchestration_assess` is already a complete recommend-then-decide
# assessor (categorical consider / not_recommended / already_adopted, never a
# numeric score, never adopts) -- but nothing surfaced it, so an agent went
# straight to hand-written SQL and the adapters were bypassed silently instead of
# declined on purpose. The owner ruled to surface it here.
#
# Hard invariants this checkpoint preserves:
#   - `next` NEVER adopts an adapter, grants readiness, or emits a numeric score.
#   - It NEVER blocks: the note is a separate additive field, never a
#     `blocking_reason`, never part of `forbidden_scope`, never `next_allowed_action`.
#   - The assessor is DB-FREE and NETWORK-FREE -- it globs committed
#     `mappings/*/readiness-status.yaml` and probes two project markers, nothing
#     else -- so wiring it in keeps this module's no-DB / no-network contract.
#   - `consider` is NEVER permission to skip authoring (coherent with the shipped
#     `retail-build-warehouse` precondition 5).
#
# Stage scoping follows the issue, and `docs/agent-mode.md` documents it in these
# exact words -- "Dagster at Source, dbt at Silver/Gold". This mapping IS that
# sentence; a test pins the two together so the tuple cannot drift from the
# documented contract.
#
# Dagster is the governed INGESTION adapter (landing file -> bronze), so its
# choice is live at Source ONLY. It deliberately does NOT extend to Mapping: by
# then Source has already passed and ingestion is done, so offering the ingestion
# opt-in there arrives one stage LATE and points the reader at a workflow that is
# no longer the active one. dbt builds shadow silver/gold, so its choice is live
# at Silver/Gold.
# ---------------------------------------------------------------------------
_ADAPTER_STAGE_SCOPE: dict[str, tuple[str, ...]] = {
    "dagster": ("source_ready",),
    "dbt": ("silver_ready", "gold_ready"),
}

_ADAPTER_ROLE: dict[str, str] = {
    "dagster": "governed ingestion (landing file -> bronze) and gated unattended runs",
    "dbt": "shadow silver/gold builds with parity evidence",
}

# The decision is the human's, and declining is a first-class answer. Stated on
# every checkpoint so a `consider` verdict can never read as either an adoption or
# a licence to skip the authoring the stage still requires.
_CHECKPOINT_DECISION_RULE = (
    "This is INFORMATIONAL: `seshat next` never adopts an adapter and never "
    "grants readiness -- you decide, and declining is a valid answer. It does not "
    "block this stage, and a `consider` verdict is NOT permission to skip "
    "authoring the stage's own artifacts."
)


def _adapters_in_scope(stage: str | None) -> list[str]:
    """Adapter names whose choice is live at ``stage``, in stable order."""
    return [name for name in ("dagster", "dbt") if stage in _ADAPTER_STAGE_SCOPE[name]]


def _verdicts() -> tuple[str, str]:
    """``(_CONSIDER, _ALREADY_ADOPTED)`` from the engine that defines them.

    Imported lazily and never re-typed as literals here: the verdict vocabulary has
    exactly one owner (``orchestration_assess``), and a copy would be free to drift
    from it. Lazy so this module's import stays as light as it was.
    """
    from seshat.orchestration_assess import _ALREADY_ADOPTED, _CONSIDER

    return _CONSIDER, _ALREADY_ADOPTED


def _scoped_headline(notes: list[dict[str, Any]]) -> str:
    """A one-line recommendation derived ONLY from the adapters shown below it.

    The assessor's own ``recommended_action`` is portfolio-wide -- correct for
    `seshat orchestration-assess`, wrong here: at a stage-scoped checkpoint it can
    name an adapter whose reasoning was filtered out, which is "recommendation
    without reasoning" -- the exact failure #489 filed, inverted. So the headline is
    built FROM the scoped blocks and can only ever name what is actually shown.

    Stays categorical and non-directive: it reports the verdicts already in the
    blocks, never a numeric score, and never an instruction to adopt.
    """
    consider_verdict, adopted_verdict = _verdicts()
    consider = [n["adapter"] for n in notes if n["recommendation"] == consider_verdict]
    adopted = [n["adapter"] for n in notes if n["recommendation"] == adopted_verdict]
    parts: list[str] = []
    if consider:
        parts.append(
            f"{', '.join(consider)} may be worth adopting for this stage -- "
            "weigh the signals below, then YOU decide"
        )
    if adopted:
        parts.append(f"{', '.join(adopted)} already present in this workspace")
    if not parts:
        shown = ", ".join(n["adapter"] for n in notes)
        parts.append(
            f"no adapter is recommended for this stage from committed state "
            f"({shown}); revisit as scope grows"
        )
    return "; ".join(parts) + "."


# A STOP is inherited by the guidance below it, never sat beside (PR #506, P1).
#
# An agent reads this document top to bottom. When the focused stage is blocked,
# `next_allowed_action` and `stop_point` both say STOP -- and an adapter block
# carrying `pip install ... / dagster init / dagster doctor` underneath that reads
# as "here is what to do next". Following it mutates the environment or the
# repository instead of halting, which is the same defect class as offering a
# repair route for an already-approved map: guidance that outranks a gate.
#
# So while blocked the VERDICT still shows (it is genuinely informational, and
# hiding it would lose a real signal), but every executable step is withheld and
# the choice is explicitly deferred until the block clears. Nothing runnable is
# ever rendered below a STOP.
_ADAPTER_STEPS_DEFERRED = (
    "Deferred while this stage is blocked: resolve the recorded blocking_reasons "
    "first. The opt-in steps are deliberately withheld here -- do not install, "
    "initialize, or run an adapter while a gate is blocked. Re-run `seshat next` "
    "once the block clears to see them."
)


def _adapter_note(
    name: str, block: dict[str, Any], *, blocked: bool = False
) -> dict[str, Any]:
    """One adapter's categorical verdict + the assessor's own reasoning, verbatim.

    Copies only the fields a reader needs to weigh the choice; the raw assessor
    document keeps its own `read_only_proof` and is not re-embedded.

    When ``blocked``, ``opt_in_command`` is replaced by the deferral sentence:
    the verdict and its reasoning stay (informational), but no runnable step is
    emitted below a STOP. ``opt_in_deferred`` marks that substitution so a
    non-text consumer can tell a withheld step from an absent one.
    """
    return {
        "adapter": name,
        "role": _ADAPTER_ROLE[name],
        "recommendation": block["recommendation"],
        "for": list(block.get("for", [])),
        "against": list(block.get("against", [])),
        "open_questions": list(block.get("open_questions", [])),
        "opt_in_command": (
            _ADAPTER_STEPS_DEFERRED if blocked else block["opt_in_command"]
        ),
        "opt_in_deferred": blocked,
        "already_present": bool(block.get("already_present")),
    }


# Emitted commands NEVER interpolate a filesystem path (PR #506 review, P2 x2).
#
# Two independent defects came from embedding one:
#   * quoting is not portable. This repo is Windows-primary, and there is no single
#     correct quoting for a path across POSIX sh, `cmd.exe` (which treats POSIX
#     single quotes as literal characters) and PowerShell. A path with a space, a
#     `$(...)`, or an apostrophe cannot be pre-quoted correctly for all three at
#     once -- so a "copyable" command carrying one is wrong on some supported shell.
#   * the SECOND emitted command has the same problem again. The `--repo` value has
#     to reach every command in the guidance, not just the first, or the reader
#     scaffolds a reference folder into an unrelated directory.
#
# Both classes vanish if no path is embedded: `--repo .` plus "run this from the
# repository root" is correct on every shell, needs no escaping, and cannot point
# somewhere unintended. The root is still named -- as DATA, in its own field
# (`repo_path`), where no shell ever parses it -- so a reader who is elsewhere knows
# exactly which directory to cd into. Naming the path was the point of the original
# finding; pre-quoting it into a command string was the mistake.
_RUN_FROM_REPO_ROOT = (
    "run from the repository root (the `repo_path` below); commands use `--repo .` "
    "so no path needs quoting on any shell"
)


def _orchestration_assessment(root: Path) -> dict[str, Any]:
    """Build the offline adapter assessment ONCE for a whole ``next`` call.

    Kept a separate call (rather than inlined in ``_compose``) because it globs
    ``mappings/*/readiness-status.yaml``: one call per DOCUMENT is linear, one call
    per TABLE would be quadratic. Read-only, no DB, no network -- see
    ``orchestration_assess``'s module contract.
    """
    from seshat.orchestration_assess import build_orchestration_assessment

    return build_orchestration_assessment(root)


def _orchestration_checkpoint(
    stage: str | None,
    assessment: dict[str, Any] | None,
    repo_path: str | None = None,
    *,
    blocked: bool = False,
) -> dict[str, Any] | None:
    """The #489 informational adapter checkpoint for ``stage``, or ``None``.

    ``None`` when no adapter choice is live at this stage, or when the caller did
    not supply an assessment (``build_table_next_document`` deliberately does not
    -- see its docstring).

    ``blocked`` means the focused stage's gate is closed and this document already
    says STOP. The verdict still renders (informational), but every executable
    opt-in step is withheld -- see ``_ADAPTER_STEPS_DEFERRED``.
    """
    if assessment is None:
        return None
    adapters = _adapters_in_scope(stage)
    if not adapters:
        return None
    blocks = assessment["adapters"]
    notes = [_adapter_note(name, blocks[name], blocked=blocked) for name in adapters]
    checkpoint = {
        "stage": stage,
        "decision_owner": assessment["decision_owner"],
        # Derived from `notes`, NOT from the assessor's portfolio-wide headline: a
        # stage-scoped checkpoint must never name an adapter whose reasoning it
        # filtered out. The portfolio-wide view stays available in full via
        # `full_assessment_command` below.
        "recommended_action": _scoped_headline(notes),
        "adapters": notes,
        "decision_rule": _CHECKPOINT_DECISION_RULE,
        "steps_deferred_by_block": blocked,
        "repo_path": repo_path,
    }
    if blocked:
        # Withhold the assess command too. It is read-only, but a runnable command
        # under a STOP still invites acting instead of halting, and "which commands
        # below a STOP are safe" is not a judgement to push onto the reader.
        return checkpoint
    # No interpolated path: `--repo .` is correct on every shell and cannot be
    # mis-quoted. The workspace this document describes is named separately, as
    # DATA, in `repo_path` -- see the note above _RUN_FROM_REPO_ROOT.
    # The INSTALLED console script, not `python -m seshat.cli`: the validated lane
    # is `pipx install seshat-bi` (docs/install/user-install.md,
    # docs/install/agent-install.md), which puts `seshat` on PATH inside an ISOLATED
    # environment -- the ambient `python` there cannot import `seshat` at all, so
    # `python -m ...` fails for exactly the users this guidance is for (PR #506
    # review, P2). `seshat` is declared in pyproject's [project.scripts].
    checkpoint["full_assessment_command"] = "seshat orchestration-assess --repo ."
    checkpoint["command_scope"] = _RUN_FROM_REPO_ROOT
    return checkpoint


def _stage_index(stage: str | None) -> int:
    """Spine position for ranking; terminal (``None``) sorts last."""
    if stage is None:
        return len(_STAGE_ORDER)
    return _STAGE_ORDER.index(stage)


def _forbidden_scope(stage: str | None, outcome: str) -> list[str]:
    """Every gate at or after the current stage is still closed; the
    invariants hold always. Deterministic given (stage, outcome)."""
    if outcome == "terminal_pass" or stage is None:
        gates: list[str] = []
    else:
        current = _stage_index(stage)
        gates = [
            sentence
            for gate_stage, sentence in _GATE_RULES
            if _stage_index(gate_stage) >= current
        ]
    return gates + list(_ALWAYS_FORBIDDEN)


def _validation_commands(stage: str | None) -> list[str]:
    commands = list(_BASE_VALIDATION_COMMANDS)
    commands.extend(_VALIDATION_EXTRAS_BY_STAGE.get(stage or "", ()))
    return commands


def _stop_point(response: dict[str, Any]) -> str:
    outcome = response["outcome"]
    stage = response["stage"]
    if outcome == "terminal_pass":
        return _TERMINAL_STOP_POINT
    if outcome == "stop_blocked":
        return (
            "Stopped now: resolve or escalate the recorded blocking_reasons; "
            "do not work around the block."
        )
    if outcome == "approval_required":
        authority = response.get("required_authority") or "named human"
        return (
            f"Stopped now: a named-human approval ({authority}) for stage "
            f"{stage!r} is required before any further stage work."
        )
    if outcome == "input_defect":
        return (
            "Stopped now: repair the malformed readiness-status.yaml before "
            "any pipeline work."
        )
    return _STOP_POINT_BY_STAGE.get(stage or "", _STOP_POINT_BY_STAGE["source_ready"])


def _next_allowed_action(response: dict[str, Any]) -> str:
    outcome = response["outcome"]
    stage = response["stage"]
    if outcome == "next_action":
        return str(response.get("action_text") or "")
    if outcome == "stop_blocked":
        return (
            f"STOP -- stage {stage!r} is blocked; resolve the recorded "
            "blocking_reasons before any other pipeline work."
        )
    if outcome == "approval_required":
        from seshat.rules.readiness_status import APPROVAL_SHAPE_HINT

        authority = response.get("required_authority") or "named human"
        # Name the shape the gate requires (issue #487). This is guidance for the
        # HUMAN who will decide -- it does not soften the gate, and the
        # never-self-grant instruction stays first.
        return (
            f"STOP -- obtain the named-human approval ({authority}) for "
            f"stage {stage!r}; never self-grant it. Once that human has "
            f"decided, {APPROVAL_SHAPE_HINT}."
        )
    if outcome == "terminal_pass":
        return "No pipeline action: all seven readiness stages pass for this table."
    return "Repair the readiness-status.yaml input defect before any pipeline work."


def _contract_next_override(
    root: Path, response: dict[str, Any], entry: dict[str, Any] | None
) -> str | None:
    """Surface the existing metric-owner seam after Gold without moving a stage."""
    stage = response.get("stage")
    if entry is None or stage not in {
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    }:
        return None
    from seshat.portfolio_watch import contract_binding_state

    scope_dir = _dir_name(entry["source_path"])
    if contract_binding_state(root, scope_dir) == "verified":
        return None
    return (
        "Run `kpi-contract-builder` to assess and draft the missing or unbound "
        "metric contracts, then obtain the named metric owner approval. Do not "
        "design a dashboard until the semantic contract gate is complete."
    )


def _live_validation_next_override(
    root: Path, response: dict[str, Any], entry: dict[str, Any] | None
) -> str | None:
    """Keep the live DB boundary explicit after Gold; do not connect from next."""
    stage = response.get("stage")
    terminal_pass = response.get("outcome") == "terminal_pass"
    post_gold_stage = stage in {
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    }
    if entry is None or not (terminal_pass or post_gold_stage):
        return None
    from seshat.portfolio_watch import (
        STATE_UNCOMMITTED_EVIDENCE,
        live_validation_state,
    )

    scope_dir = _dir_name(entry["source_path"])
    live_state = live_validation_state(root, scope_dir)
    if live_state == "verified":
        return None
    if live_state == STATE_UNCOMMITTED_EVIDENCE:
        # The run succeeded, but its only record is the git-ignored
        # .seshat/dagster/runs/ scratch. An untracked machine-local file must not
        # silence this caveat on a surface someone else reads as authoritative
        # (issue #493) -- so the caveat is DOWNGRADED, not silenced, and names
        # exactly why the supporting evidence is unreviewable.
        return (
            "CAUTION -- live validation passed locally, but the supporting "
            "evidence is machine-local and unreviewable: it exists only under "
            "the git-ignored `.seshat/dagster/runs/`, with no matching record "
            "committed at HEAD as "
            "`orchestration/dagster/run-evidence/<run-id>.md`. Run `seshat "
            "dagster evidence --run-id <run-id>`, then COMMIT the rendered "
            "record on its own -- rendering alone leaves it untracked, and a "
            "reviewer can only read what is committed. Until then, do not treat "
            "this table as live-validated for anyone but yourself."
        )
    if live_state in {"stale", "blocked"}:
        return (
            f"STOP -- live validation evidence is {live_state}. Re-run `retail "
            f"validate --source-map mappings/{scope_dir}/source-map.yaml` and "
            "resolve every live finding before any semantic-model, dashboard, or "
            "publish work."
        )
    return (
        "STOP -- run `retail validate --source-map mappings/"
        f"{scope_dir}/source-map.yaml`. [PENDING LIVE PROFILE]: install the db "
        "extra (`pipx inject seshat-bi psycopg2-binary` or `pip install "
        '"seshat-bi[db]"`), then set DATABASE_URL or ANALYTICS_DB_* in the '
        "gitignored .env. Do not claim Gold Ready until the live validation passes."
    )


def _control_stage(
    stage: str | None, contract_override: str | None, live_override: str | None
) -> str | None:
    """Stage whose closed gate governs every agent-control field."""
    if live_override is not None:
        return "gold_ready"
    if contract_override is not None:
        return "semantic_model_ready"
    return stage


def _readiness_state(
    response: dict[str, Any], entry: dict[str, Any] | None
) -> str | None:
    """The RECORDED four-status of the current stage, read from the same
    committed projection -- never derived. ``input_defect`` has no honest
    state, so it projects as ``None``.

    ONE exception, and it is the whole of issue #485: when the decision surface
    returned ``stop_blocked``, the recorded status must NOT override it. Echoing
    the committed ``pass`` here is exactly the defect the issue reports -- the
    reporter ran `next --format agent` and read ``readiness_state: pass`` for a
    database that had none of the claimed objects, because this function trusted
    the recorded value over the computed stop. A recorded `pass` that the gate has
    just refused to honour is not the honest state of the table; the stop is.
    """
    outcome = response["outcome"]
    if outcome == "terminal_pass":
        return "pass"
    if outcome == "input_defect":
        return None
    if outcome == "stop_blocked":
        # The gate stopped this table. Whatever the file records, the surface must
        # not report `pass` -- see the #485 note above.
        return "blocked"
    stage = response["stage"]
    if entry is not None and stage is not None:
        block = entry.get("stages", {}).get(stage)
        if isinstance(block, dict) and isinstance(block.get("status"), str):
            return block["status"]
    # No readiness file (or stage block unreadable): the conservative,
    # non-fabricated state is the journey's start.
    return "not_started"


def _evidence(entry: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Every recorded stage, verbatim from the committed projection, in spine
    order -- items are the readiness file's own evidence strings."""
    if entry is None:
        return []
    stages = entry.get("stages", {})
    return [
        {
            "stage": name,
            "status": stages[name]["status"],
            "items": list(stages[name]["evidence"]),
        }
        for name in _STAGE_ORDER
        if name in stages
    ]


def _summaries(
    triples: list[tuple[dict[str, Any] | None, dict[str, Any], str]],
) -> list[dict]:
    return [
        {
            "table": response["table"],
            "source_path": source_path,
            "outcome": response["outcome"],
            "stage": response["stage"],
        }
        for _entry, response, source_path in triples
    ]


def _rank(response: dict[str, Any]) -> int:
    """Focus ranking: a malformed file is the most urgent, then the earliest
    incomplete stage; a fully-passed table sorts last."""
    if response["outcome"] == "input_defect":
        return -1
    return _stage_index(response["stage"])


@dataclass(frozen=True)
class _PortfolioContext:
    """The portfolio-level facts only the whole-repo caller can supply.

    Both members are read ONCE per document by ``build_agent_next_document`` and
    threaded down, because both are portfolio-wide reads:
    ``summaries`` from the shared status projection, and ``assessment`` from
    ``orchestration_assess`` (which globs ``mappings/*``). Bundling them keeps the
    per-table ``build_table_next_document`` path -- which deliberately supplies
    NEITHER -- a single default, and keeps them out of ``_compose``'s signature
    individually.
    """

    summaries: tuple[dict, ...] = ()
    assessment: dict[str, Any] | None = None
    # The workspace this document describes, reported as DATA so a reader who is
    # elsewhere knows which directory to run the commands from. Never interpolated
    # into a command string -- see the note above ``_RUN_FROM_REPO_ROOT``. ``None``
    # on the per-table path, which emits no commands.
    repo_path: str | None = None


# Outcomes whose `next_allowed_action` and `stop_point` both say STOP. Derived from
# the SAME signals those two fields use, so the guidance below a STOP can never
# disagree with it (PR #506, P1). `input_defect` counts: a malformed readiness file
# must be repaired before any pipeline work, adapters included.
_STOP_OUTCOMES = frozenset({"stop_blocked", "approval_required", "input_defect"})


def _is_stopped(
    response: dict[str, Any], readiness_state: str | None, action: str = ""
) -> bool:
    """True when this document tells the reader to STOP.

    Three independent signals, any of which is a stop:

      * the run-next ``outcome`` (``stop_blocked`` / ``approval_required`` /
        ``input_defect``);
      * the RECORDED status of the focused stage -- a ``blocked`` status is a closed
        gate even where the outcome is phrased as a next action;
      * ``action`` -- the FINAL ``next_allowed_action`` string, which is the literal
        statement of the rule and therefore authoritative.

    The third signal is not redundant: ``_live_validation_next_override`` emits
    "STOP -- run `retail validate` ..." (or "STOP -- live validation evidence is
    stale") while ``outcome`` stays ``terminal_pass``/``next_action`` and
    ``readiness_state`` stays ``pass``. Neither of the first two signals sees that,
    yet ``_control_stage`` pulls control back to ``gold_ready`` -- so dbt was in
    scope and its install/init/doctor steps rendered directly beneath a STOP. Keying
    off the emitted string closes that route and every future one shaped like it: if
    the document says STOP, the guidance below it inherits the stop, no matter which
    branch produced the sentence. ``_contract_next_override`` does NOT start with
    STOP (it says "Run `kpi-contract-builder` ..."), so it correctly keeps its steps.
    """
    return (
        response.get("outcome") in _STOP_OUTCOMES
        or readiness_state == "blocked"
        or action.startswith("STOP")
    )


def _guidance_fields(
    control_stage: str | None,
    context: _PortfolioContext,
    *,
    stopped: bool = False,
) -> dict[str, Any]:
    """The two additive, purely INFORMATIONAL fields (issues #488 / #489).

    Both are keyed off ``control_stage`` -- the stage whose closed gate governs
    every other agent-control field -- so guidance and gate can never disagree.
    Neither can block, neither is a ``blocking_reason``, and neither is consulted
    by ``forbidden_scope`` / ``outcome`` / ``next_allowed_action``. Kept in one
    helper so that invariant is visible in a single place.

    ``stopped`` propagates the document's own STOP down into BOTH fields: the
    adapter verdict still renders without its executable steps, and the map-shape
    signpost -- whose text is an imperative to author the map and scaffold a
    reference folder, i.e. repository-mutating -- is withheld entirely. A signpost
    is only actionable while the map is actually being authored; below a STOP it
    would invite mutating the repo instead of resolving the blocker.
    """
    return {
        "source_map_shape_signpost": (
            None if stopped else _source_map_shape_signpost(control_stage)
        ),
        "orchestration_checkpoint": _orchestration_checkpoint(
            control_stage, context.assessment, context.repo_path, blocked=stopped
        ),
    }


def _compose(
    root: Path,
    response: dict[str, Any],
    entry: dict[str, Any] | None,
    context: _PortfolioContext = _PortfolioContext(),
) -> dict[str, Any]:
    stage = response["stage"]
    outcome = response["outcome"]
    contract_override = _contract_next_override(root, response, entry)
    live_override = _live_validation_next_override(root, response, entry)
    next_override = live_override or contract_override
    control_stage = _control_stage(stage, contract_override, live_override)
    control_outcome = "next_action" if next_override is not None else outcome
    control_response = {
        **response,
        "stage": control_stage,
        "outcome": control_outcome,
    }
    readiness_state = _readiness_state(response, entry)
    # The FINAL action string, computed once: it is both the emitted field and the
    # authoritative STOP signal the guidance below it must inherit.
    action = next_override or _next_allowed_action(response)
    return {
        "current_stage": stage,
        "readiness_state": readiness_state,
        "evidence": _evidence(entry),
        "blocking_reasons": list(response.get("blocking_reasons", [])),
        "next_allowed_action": action,
        "forbidden_scope": _forbidden_scope(control_stage, control_outcome),
        "validation_commands": _validation_commands(control_stage),
        "stop_point": _stop_point(control_response),
        **_guidance_fields(
            control_stage,
            context,
            stopped=_is_stopped(response, readiness_state, action),
        ),
        "table": response["table"],
        "outcome": outcome,
        "required_authority": response.get("required_authority"),
        "caveats": list(response.get("caveats", [])),
        "tables": list(context.summaries),
        "read_only_proof": True,
    }


def _fresh_repo_document() -> dict[str, Any]:
    """No committed readiness evidence at all: the conservative,
    evidence-first answer -- never a fabricated stage or state."""
    return {
        "current_stage": "source_ready",
        "readiness_state": "not_started",
        "evidence": [],
        "blocking_reasons": [],
        "next_allowed_action": _FRESH_NEXT_ACTION,
        "forbidden_scope": _forbidden_scope("source_ready", "next_action"),
        "validation_commands": _validation_commands("source_ready"),
        "stop_point": _STOP_POINT_BY_STAGE["source_ready"],
        # A workspace with no readiness evidence has nothing to assess: the
        # scaffolder has not run, so there is no adapter choice to weigh yet. The
        # keys stay PRESENT (stable shape) and null, never fabricated.
        "source_map_shape_signpost": None,
        "orchestration_checkpoint": None,
        "table": None,
        "outcome": "next_action",
        "required_authority": None,
        "caveats": [],
        "tables": [],
        "read_only_proof": True,
    }


def _dir_name(source_path: str) -> str:
    """The ``mappings/<dir>/`` directory name -- the identity
    ``build_run_next_response`` always resolves via its direct candidate path,
    even when the file records no string ``table`` field."""
    return source_path.rsplit("/", 2)[-2]


def _unprojected_status_paths(root: Path, entries: list[dict[str, Any]]) -> list[str]:
    """Committed readiness-status files the best-effort projection SKIPPED
    (unreadable / unparseable / non-mapping). They must still surface -- as
    ``input_defect``, never as an absent table -- or a broken committed file
    would silently read as a fresh journey."""
    projected = {entry["source_path"] for entry in entries}
    mappings_dir = root / "mappings"
    if not mappings_dir.is_dir():
        return []
    return [
        path.relative_to(root).as_posix()
        for path in sorted(mappings_dir.glob("*/readiness-status.yaml"))
        if path.relative_to(root).as_posix() not in projected
    ]


def _all_triples(
    root: Path, entries: list[dict[str, Any]]
) -> list[tuple[dict[str, Any] | None, dict[str, Any], str]]:
    """One ``(projection entry, run-next response, source path)`` triple per
    committed readiness-status file, including files the projection skipped
    (entry ``None``; their run-next outcome is ``input_defect``)."""
    triples: list[tuple[dict[str, Any] | None, dict[str, Any], str]] = [
        (
            entry,
            build_run_next_response(root, _dir_name(entry["source_path"])),
            entry["source_path"],
        )
        for entry in entries
    ]
    for source_path in _unprojected_status_paths(root, entries):
        triples.append(
            (
                None,
                build_run_next_response(root, _dir_name(source_path)),
                source_path,
            )
        )
    return triples


def _resolved_source_path(root: Path, table: str) -> str | None:
    """The repo-relative path of the readiness file run-next itself resolves
    for ``table`` (its ``_find_status_data`` matches dir name / recorded
    table / source_id -- reused, not re-derived)."""
    from seshat.run_next import _find_status_data

    status_path, _data, _error = _find_status_data(root, table)
    if status_path is None:
        return None
    return status_path.relative_to(root).as_posix()


def _entry_by_source_path(
    entries: list[dict[str, Any]], source_path: str | None
) -> dict[str, Any] | None:
    if source_path is None:
        return None
    return next((e for e in entries if e["source_path"] == source_path), None)


def _entry_by_name(
    entries: list[dict[str, Any]], names: set[str | None]
) -> dict[str, Any] | None:
    return next(
        (e for e in entries if {e.get("table"), _dir_name(e["source_path"])} & names),
        None,
    )


def _entry_matching(
    root: Path,
    entries: list[dict[str, Any]],
    table: str,
    response: dict[str, Any],
) -> dict[str, Any] | None:
    """Find the projection entry behind a --table response: authoritatively by
    the source path of the file run-next resolved, else by name."""
    by_path = _entry_by_source_path(entries, _resolved_source_path(root, table))
    if by_path is not None:
        return by_path
    return _entry_by_name(entries, {response.get("table"), table})


def build_table_next_document(repo_root: Path | str, table: str) -> dict[str, Any]:
    """Single-table next-action document WITHOUT the portfolio summaries.

    Same composed shape as :func:`build_agent_next_document`, but it reads
    only this table's readiness file (one run-next response) instead of
    re-projecting every table -- O(1) file reads, which keeps portfolio-wide
    consumers (the shared readiness projection, spec 120) linear instead of
    quadratic. ``tables`` is empty and the entry-derived fields
    (``readiness_state``/``evidence``) degrade conservatively; callers that
    need those use the full document.

    For the same linearity reason it does NOT build the orchestration assessment:
    that assessment is a portfolio-wide, ``mappings/*``-globbing read, so computing
    it per table would restore the very O(n^2) behaviour this function exists to
    avoid. ``orchestration_checkpoint`` is therefore ``None`` here; the
    portfolio-level ``build_agent_next_document`` computes it ONCE and supplies it.
    """
    root = Path(repo_root)
    response = build_run_next_response(root, table)
    source_path = _resolved_source_path(root, table)
    entry = {"source_path": source_path} if source_path is not None else None
    # Default (empty) portfolio context: no summaries, and deliberately NO
    # orchestration assessment -- see the linearity note above.
    return _compose(root, response, entry)


def build_agent_next_document(
    repo_root: Path | str, table: str | None = None
) -> dict[str, Any]:
    """Build the agent-facing next-action document for ``repo_root``.

    With ``table``, the document focuses that table (missing file degrades to
    the conservative Source Ready start, exactly as ``build_run_next_response``
    does). Without it, the focus is the table with the most urgent run-next
    outcome -- a malformed committed readiness file first, then the earliest
    incomplete stage (ties broken by source path, so the answer is
    deterministic); a repo with no readiness files at all produces the
    conservative evidence-first document. Read-only in every path.
    """
    root = Path(repo_root)
    projection = build_status_projection(root)
    entries: list[dict[str, Any]] = projection["tables"]
    triples = _all_triples(root, entries)

    if table is None and not triples:
        return _fresh_repo_document()

    # Both portfolio-level reads happen ONCE per document, here -- after the
    # fresh-repo short-circuit, which needs neither.
    context = _PortfolioContext(
        summaries=tuple(_summaries(triples)),
        assessment=_orchestration_assessment(root),
        repo_path=root.as_posix(),
    )

    if table is not None:
        response = build_run_next_response(root, table)
        entry = _entry_matching(root, entries, table, response)
        return _compose(root, response, entry, context)

    focus_entry, focus_response, _ = min(
        triples, key=lambda triple: (_rank(triple[1]), triple[2])
    )
    return _compose(root, focus_response, focus_entry, context)
