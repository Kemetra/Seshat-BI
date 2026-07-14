"""Friendly PR Reviewer -- plain-language PR summary (spec 130).

A PRESENTATION layer over ALREADY-SHIPPED, ALREADY-AUTHORITATIVE governance
results. This module creates no truth: it renders, in plain language, what the
shipped engines already decided. It is explicitly DISTINCT from the shipped
``pr-readiness-reviewer`` skill (F025, ``.claude/skills/pr-readiness-reviewer/``),
which owns the merge-safety VERDICT (a ``merge_ready`` boolean). This module
never renders a ``merge_ready`` boolean and never duplicates that verdict
surface -- it only explains what changed and what it means.

Consumed seams (read by field, never re-derived, never mutated):
  - ``review_integration.build_review_result`` -- the review envelope:
    ``outcome`` (only ever ``"ok"`` or ``"blocked"`` -- there is no
    ``input_defect`` outcome value; an absent/unproducible envelope is a
    separate honesty branch, handled here as ``envelope is None``),
    ``checks_run``, ``changed_files``, ``changed_readiness_state``,
    ``affected_stages``, ``findings[]``, ``blocking_findings[]``,
    ``next_actions[]``, ``run_boundary``, ``result_digest``.
  - ``sarif.finding_fingerprint`` -- sha256(rule_id + severity + locator +
    message); the canonical new-vs-existing identity key. ``classify_changes``
    calls this function directly rather than reimplementing the hash.
  - ``readiness_classify.classify`` / ``rank_of`` / ``CATEGORY_RANK`` -- the
    refutation-first category rank (approval > grain > live_validation >
    artifact > readiness), reused BOTH to pick exactly one next action
    (``pick_next_action``) and to route a blocked stage to its required
    authority/surface (``render_summary``'s authority lookup).
  - ``readiness_evidence._scrub`` -- read for context only, NOT lifted. It
    redacts a DSN only when the caller already holds the literal DSN string
    (a shape it does not detect); this module has no DSN, so a bare
    DSN/connection-string URL in a finding message is NOT masked here (a
    documented v1 non-coverage -- see ``mask()``).
  - ``interview_review._mask`` -- the PRIVATE PII/secret masker is NOT
    imported. Its four detectable SHAPES (email, SSN/national-ID-like number,
    long digit run, ``key: value`` secret assignment) are reproduced here as a
    new, self-contained, public, testable ``mask()`` function (same shapes,
    same replacement token, cited below) -- this is not a new redaction
    engine, it is the same shapes lifted into a public function.
  - ``readiness-status.yaml`` shape (``current_stage``, per-stage ``status``,
    ``approvals[]``, ``blocking_reasons[]``) -- read as an already-parsed
    mapping (this module does no YAML I/O itself; a caller loads the file).

Invariants (Principle VIII; B1/B3 import-boundary guards):
  - Read-only: no file writes, no readiness-stage moves, no approvals granted.
  - No network: no HTTP, no GitHub API call, no DB connection.
  - No clock: no ``datetime.now()`` / ``time.time()`` read anywhere in this
    module; a timestamp is always an explicit caller-supplied argument.
  - No score: no numeric merge/confidence/health/maturity/completeness score
    or percentage anywhere. Every status is a verbatim categorical token.
  - stdlib-only: this module imports only the Python standard library plus
    sibling in-repo modules (``.core``, ``.sarif``, ``.readiness_classify``)
    that are themselves stdlib-only. No ``yaml``, no ``requests``, no ``gh``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .core import Finding, Severity
from .readiness_classify import classify, rank_of
from .sarif import finding_fingerprint

SCHEMA_VERSION = "1.0"

# The stable, documented sticky-comment marker (FR-014). Never changes across
# a schema_version bump within v1; a future incompatible bump would mint a new
# marker string, not silently repurpose this one.
MARKER = "<!-- seshat:friendly-pr-summary:v1 -->"

# The sentinel line rendered when no next action could be selected (FR-017,
# "no next action was produced by the review"). A plain string, not ``None``,
# so the frozen ``FriendlySummary.next_action`` field is always a str.
NO_NEXT_ACTION = "no next action was produced by the review"

# A stable, documented cap on findings rendered per blocker/change group
# (Edge Cases: "a very large finding set"). Truncation is ALWAYS noted with a
# count of what was omitted -- never a silent drop that could hide a blocker.
MAX_GROUP_LINES = 20

# Readiness stages that require a named human approval before they may read
# `pass` (mirrors the stage set `blocker_explainer._APPROVAL_REQUIRED` checks
# against -- duplicated here as a small, public, non-secret config, not the
# private redaction/classification logic the reuse-only rule protects).
_APPROVAL_REQUIRED_STAGES: frozenset[str] = frozenset(
    {"mapping_ready", "semantic_model_ready", "dashboard_ready", "publish_ready"}
)

# --- mask(): reproduces the interview_review._mask / readiness_evidence
# _MASK_SHAPES four PII/secret SHAPES verbatim (email, SSN/national-ID-like,
# long digit run, `key: value` secret assignment). Cited, not imported, per
# the spec's explicit design decision (a new, self-contained, public masker).
_MASK_SHAPES: tuple[re.Pattern[str], ...] = (
    re.compile(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"\b\d{3}[ .-]\d{2}[ .-]\d{4}\b"),  # SSN-like
    re.compile(r"\b(?:\d[ -]?){12,19}\b"),  # long digit run
    re.compile(
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|token)\b\s*[:=]\s*\S+"
    ),  # secret assignment
)


def mask(text: str) -> str:
    """Redact the four ``_mask``-detected PII/secret shapes in ``text``.

    Shapes: email address, SSN/national-ID-like number, a long digit run, and
    a ``key: value`` secret assignment (``password:``, ``token:``, ...).
    Leaves clean text unchanged; is idempotent (masking already-masked text is
    a no-op, since ``[REDACTED]`` matches none of the four shapes).

    v1 non-coverage (documented, not a bug -- FR-009): a bare DSN/connection-
    string URL (``scheme://user:pass@host/db``) embedded in a finding message
    is NOT masked. ``interview_review._mask`` has no connection-URL shape, and
    ``readiness_evidence._scrub`` only redacts a DSN when the caller already
    holds the literal DSN string, which this DB-less presentation layer never
    does. Adding a DSN/URL detector would be a NEW redaction primitive
    (contradicting the reuse-only rule); v1 deliberately does not add one. A
    DSN URL in a finding message is a documented residual-risk gap.
    """
    out = text
    for pattern in _MASK_SHAPES:
        out = pattern.sub("[REDACTED]", out)
    return out


def pick_next_action(next_actions: Sequence[str]) -> str | None:
    """Select EXACTLY ONE action from ``next_actions`` by the shipped
    refutation-first category rank (``readiness_classify``: approval > grain >
    live_validation > artifact > readiness). Returns ``None`` on an empty
    list -- never invents an action, never returns more than one. Ties within
    the same category break alphabetically for full determinism regardless of
    input order.
    """
    if not next_actions:
        return None
    ranked = sorted(
        next_actions,
        key=lambda action: (rank_of(classify(action)[0]), action),
    )
    return ranked[0]


def _coerce_finding(item: Finding | Mapping[str, Any]) -> Finding:
    """Coerce a ``Finding`` or its ``to_dict()`` mapping shape into a
    ``Finding`` so ``sarif.finding_fingerprint`` (which requires a ``Finding``)
    can be called on either representation."""
    if isinstance(item, Finding):
        return item
    severity_value = item.get("severity")
    severity = (
        severity_value
        if isinstance(severity_value, Severity)
        else Severity(str(severity_value))
    )
    return Finding(
        rule_id=str(item.get("rule_id", "")),
        severity=severity,
        message=str(item.get("message", "")),
        locator=str(item.get("locator", "")),
    )


@dataclass(frozen=True)
class StageStatus:
    """One readiness stage's status, taken VERBATIM from readiness/envelope
    truth -- never computed or upgraded. ``source`` names where the status
    came from (or why it is ``unknown``)."""

    schema_version: str
    stage: str
    status: str
    source: str


@dataclass(frozen=True)
class BlockerGroup:
    """One change-classification group (``new`` / ``resolved`` /
    ``carried_over`` / ``present``) of masked, plain-language finding lines."""

    schema_version: str
    label: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class ChangeClassification:
    """Three disjoint fingerprint sets from (base fingerprint set, head
    finding set): ``new`` (head-only), ``resolved`` (base-only),
    ``carried_over`` (in both). Together ``new | carried_over`` covers every
    head fingerprint and ``resolved | carried_over`` covers every base
    fingerprint (SC-002)."""

    schema_version: str
    new: tuple[str, ...]
    resolved: tuple[str, ...]
    carried_over: tuple[str, ...]


@dataclass(frozen=True)
class FriendlySummary:
    """The rendered plain-language PR summary. No numeric field anywhere; a
    missing required input is recorded in ``undetermined`` (never silently
    assumed ``pass``); a disagreement between two consumed sources is
    recorded in ``conflicts`` (surfaced, never resolved). ``text`` is the
    full assembled plain-language document (deterministic, byte-identical
    across repeated calls on the same inputs)."""

    schema_version: str
    outcome: str
    affected_artifacts: tuple[str, ...]
    stage_statuses: tuple[StageStatus, ...]
    blocker_groups: tuple[BlockerGroup, ...]
    warnings: tuple[str, ...]
    required_authority: tuple[str, ...]
    next_action: str
    undetermined: tuple[str, ...]
    conflicts: tuple[str, ...]
    timestamp: str | None
    text: str


@dataclass(frozen=True)
class StickyComment:
    """The rendered sticky-comment envelope: a stable marker + the masked
    comment body. Posting is a separate, opt-in wrapper outside this pure,
    tested core."""

    schema_version: str
    marker: str
    body: str


def classify_changes(
    base_fingerprints: Iterable[str],
    head_findings: Iterable[Finding | Mapping[str, Any]],
) -> ChangeClassification:
    """Classify every head finding against a base fingerprint set into three
    disjoint groups keyed on ``sarif.finding_fingerprint`` (rule_id + severity
    + locator + message) -- the same identity GitHub's SARIF
    ``partialFingerprints`` uses for new-vs-existing. Head fingerprints are
    computed by calling the shipped fingerprint function directly; no new
    hashing is invented.
    """
    base = frozenset(base_fingerprints)
    head_fps = frozenset(
        finding_fingerprint(_coerce_finding(item)) for item in head_findings
    )
    return ChangeClassification(
        schema_version=SCHEMA_VERSION,
        new=tuple(sorted(head_fps - base)),
        resolved=tuple(sorted(base - head_fps)),
        carried_over=tuple(sorted(head_fps & base)),
    )


def _cap(lines: list[str]) -> list[str]:
    if len(lines) <= MAX_GROUP_LINES:
        return lines
    shown = lines[:MAX_GROUP_LINES]
    omitted = len(lines) - MAX_GROUP_LINES
    shown.append(
        f"... and {omitted} more (capped at {MAX_GROUP_LINES} for readability; "
        "see the full review envelope for the rest -- not hidden, only capped)"
    )
    return shown


def _describe_locator(locator: str) -> str:
    """Describe a finding locator in words. A non-file locator (the same
    convention ``sarif._location`` uses to skip a SARIF physical location --
    a value starting with ``(`` or ``<``, e.g. a git-metadata check) is
    described in words rather than presented as a file:line pointer."""
    if locator.startswith("(") or locator.startswith("<"):
        return f"a non-file check ({locator})"
    return f"`{locator}`"


def _finding_line(finding: Mapping[str, Any]) -> str:
    rule_id = finding.get("rule_id", "?")
    message = finding.get("message", "")
    locator = str(finding.get("locator", ""))
    return f"[{rule_id}] {message} -- {_describe_locator(locator)}"


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _stage_blocking_reasons(readiness: Mapping[str, Any], stage: str) -> list[str]:
    stages = readiness.get("stages")
    reasons: list[str] = []
    if isinstance(stages, Mapping):
        block = stages.get(stage)
        if isinstance(block, Mapping):
            reasons.extend(_as_str_list(block.get("blocking_reasons")))
    if not reasons and readiness.get("current_stage") == stage:
        reasons.extend(_as_str_list(readiness.get("blocking_reasons")))
    return reasons


def _authority_lines(
    readiness: Mapping[str, Any] | None,
    stage_statuses: tuple[StageStatus, ...],
) -> tuple[list[str], list[str]]:
    """Name the required approval authority for every ``blocked`` stage.
    Returns (authority lines, undetermined lines). Never self-names as the
    authority; never invents an owner not present in ``approvals[]``."""
    blocked = [ss for ss in stage_statuses if ss.status == "blocked"]
    if not blocked:
        return [], []
    if not isinstance(readiness, Mapping):
        return [], [
            "required approval authority: readiness-status.yaml is absent -- "
            "cannot name an authority for the blocked stage(s)"
        ]

    approvals = readiness.get("approvals")
    approvals_list = approvals if isinstance(approvals, list) else []
    lines: list[str] = []
    for ss in blocked:
        reasons = _stage_blocking_reasons(readiness, ss.stage)
        if not reasons:
            lines.append(
                f"{ss.stage}: blocked, but readiness-status.yaml names no "
                "blocking_reasons[] to route to an authority"
            )
            continue
        category, _explanation, next_surface = classify(reasons[0])
        owner_note = ""
        if category == "approval":
            match = next(
                (
                    a
                    for a in approvals_list
                    if isinstance(a, Mapping)
                    and a.get("stage") == ss.stage
                    and isinstance(a.get("owner"), str)
                    and a["owner"].strip()
                ),
                None,
            )
            if match is not None:
                owner_note = (
                    f" -- approvals[] names {mask(str(match['owner']))} on "
                    "record, but the stage is still blocked (a fresh named "
                    "human approval is required)"
                )
            else:
                owner_note = (
                    " -- no owner is recorded yet in approvals[]; a named "
                    "human must approve (this summary cannot self-grant it)"
                )
        lines.append(
            f"{ss.stage}: route to {next_surface} (category: {category}){owner_note}"
        )
    return lines, []


def render_summary(
    envelope: Mapping[str, Any] | None,
    readiness: Mapping[str, Any] | None,
    base_fingerprints: Iterable[str] | None = None,
    *,
    timestamp: str | None = None,
) -> FriendlySummary:
    """Build the plain-language PR summary from ONE review envelope + the
    committed readiness truth. Pure, deterministic, no clock (any timestamp
    is this explicit argument), no score, no ``merge_ready`` boolean. Every
    line traces to a field of ``envelope`` / ``readiness`` / a fingerprint.
    """
    undetermined: list[str] = []
    conflicts: list[str] = []
    lines: list[str] = ["# Friendly PR Summary"]
    if timestamp is not None:
        lines.append(f"(as of {timestamp})")
    lines.append("")
    lines.append(
        "This is a plain-language NARRATIVE over already-shipped review "
        "results, not a merge-safety verdict (see F025 pr-readiness-reviewer "
        "for that). It renders no merge-ready boolean and no score."
    )

    if envelope is None:
        undetermined.append(
            "review envelope: absent or could not be produced (e.g. a bad "
            "commit range) -- no change story can be rendered from it"
        )
        lines.append("")
        lines.append(
            "## The review could not be produced\n\n"
            "The review envelope is absent. No change story is rendered "
            "from it; nothing here is invented."
        )
        return FriendlySummary(
            schema_version=SCHEMA_VERSION,
            outcome="unproducible",
            affected_artifacts=(),
            stage_statuses=(),
            blocker_groups=(),
            warnings=(),
            required_authority=(),
            next_action=NO_NEXT_ACTION,
            undetermined=tuple(undetermined),
            conflicts=(),
            timestamp=timestamp,
            text="\n".join(lines) + "\n",
        )

    outcome = str(envelope.get("outcome", "unknown"))
    if outcome == "blocked":
        lines.append("\nOverall: this change is currently BLOCKED.")
    elif outcome == "ok":
        lines.append("\nOverall: this change is NOT blocked.")
    else:
        lines.append(
            f"\nOverall: outcome reported as '{outcome}' (verbatim from the "
            "review envelope)."
        )

    affected_stages = _as_str_list(envelope.get("affected_stages"))
    changed_files = _as_str_list(envelope.get("changed_files"))
    changed_readiness_state = _as_str_list(envelope.get("changed_readiness_state"))
    all_findings = [
        f for f in (envelope.get("findings") or []) if isinstance(f, Mapping)
    ]

    artifact_lines: list[str] = []
    if affected_stages:
        artifact_lines.append(
            "This change touches the following readiness stage(s): "
            + ", ".join(affected_stages)
            + "."
        )
    else:
        artifact_lines.append(
            "No readiness stage was identified as affected by this change."
        )
    if changed_files:
        artifact_lines.append(f"{len(changed_files)} file(s) changed.")
    if changed_readiness_state:
        artifact_lines.append(
            "The change includes an update to readiness-status.yaml for: "
            + ", ".join(changed_readiness_state)
            + "."
        )
    if not all_findings:
        artifact_lines.append("This change introduced no governance findings.")
    lines.append("\n## What changed\n")
    lines.extend(artifact_lines)

    # --- per-stage status, verbatim, never upgraded --------------------
    stage_statuses: list[StageStatus] = []
    readiness_is_mapping = isinstance(readiness, Mapping)
    readiness_stages: Mapping[str, Any] = {}
    if readiness_is_mapping:
        stages_field = readiness.get("stages")
        if isinstance(stages_field, Mapping):
            readiness_stages = stages_field

    for stage in affected_stages:
        if not readiness_is_mapping:
            stage_statuses.append(
                StageStatus(
                    SCHEMA_VERSION, stage, "unknown", "readiness-status.yaml: absent"
                )
            )
            continue
        block = readiness_stages.get(stage) if readiness_stages else None
        if isinstance(block, Mapping) and isinstance(block.get("status"), str):
            stage_statuses.append(
                StageStatus(
                    SCHEMA_VERSION, stage, block["status"], "readiness-status.yaml"
                )
            )
        else:
            stage_statuses.append(
                StageStatus(
                    SCHEMA_VERSION,
                    stage,
                    "unknown",
                    "readiness-status.yaml: stage entry absent",
                )
            )
            undetermined.append(
                f"readiness stage status for '{stage}': not present in "
                "readiness-status.yaml -- reported unknown, never assumed pass"
            )
    if affected_stages and not readiness_is_mapping:
        undetermined.append(
            "readiness stage status: readiness-status.yaml is absent -- "
            "affected stage(s) reported unknown, never assumed pass"
        )

    lines.append("\n## Readiness stage status\n")
    if stage_statuses:
        for ss in stage_statuses:
            lines.append(f"- {ss.stage}: {ss.status} (source: {ss.source})")
    else:
        lines.append("- no affected stage was named by the review envelope")

    # --- two sources disagree: envelope outcome vs a stage already `pass` --
    if outcome == "blocked":
        for ss in stage_statuses:
            if ss.status == "pass":
                conflicts.append(
                    f"conflict: readiness-status.yaml reports stage "
                    f"'{ss.stage}' as 'pass', but the review envelope outcome "
                    "is 'blocked' with findings affecting it -- surfaced, "
                    "not resolved (a human judgment call)"
                )

    # --- blockers / change classification -------------------------------
    lines.append("\n## Findings\n")
    blocker_groups: list[BlockerGroup] = []
    if base_fingerprints is not None:
        base_set = list(base_fingerprints)
        classification = classify_changes(base_set, all_findings)
        head_by_fp = {finding_fingerprint(_coerce_finding(f)): f for f in all_findings}
        new_lines = _cap(
            [
                mask(_finding_line(head_by_fp[fp]))
                for fp in classification.new
                if fp in head_by_fp
            ]
        )
        carried_lines = _cap(
            [
                mask(_finding_line(head_by_fp[fp]))
                for fp in classification.carried_over
                if fp in head_by_fp
            ]
        )
        resolved_lines = _cap(
            [
                f"a finding present at the base branch (fingerprint "
                f"{fp[:12]}...) is no longer present at head -- RESOLVED by "
                "this PR"
                for fp in classification.resolved
            ]
        )
        blocker_groups = [
            BlockerGroup(SCHEMA_VERSION, "new", tuple(new_lines)),
            BlockerGroup(SCHEMA_VERSION, "resolved", tuple(resolved_lines)),
            BlockerGroup(SCHEMA_VERSION, "carried_over", tuple(carried_lines)),
        ]
        lines.append("### NEW in this PR")
        if new_lines:
            lines.extend(f"- {line}" for line in new_lines)
        else:
            lines.append("- none")
        lines.append("\n### RESOLVED by this PR")
        if resolved_lines:
            lines.extend(f"- {line}" for line in resolved_lines)
        else:
            lines.append("- none")
        lines.append("\n### Pre-existing / carried over")
        if carried_lines:
            lines.extend(f"- {line}" for line in carried_lines)
        else:
            lines.append("- none")
    else:
        undetermined.append(
            "new-vs-pre-existing distinction: could not be determined -- no "
            "base fingerprint set was supplied; findings are listed as "
            "'present', never defaulted to 'new'"
        )
        present_lines = _cap([mask(_finding_line(f)) for f in all_findings])
        blocker_groups = [BlockerGroup(SCHEMA_VERSION, "present", tuple(present_lines))]
        lines.append(
            "new-vs-pre-existing could not be determined (no base "
            "fingerprint set was supplied); findings are listed as 'present':"
        )
        for line in present_lines:
            lines.append(f"- {line}")
        if not present_lines:
            lines.append("- none")

    warning_lines = _cap(
        [mask(_finding_line(f)) for f in all_findings if f.get("severity") == "warning"]
    )
    lines.append("\n## Worth a look (not blocking)\n")
    if warning_lines:
        lines.extend(f"- {line}" for line in warning_lines)
    else:
        lines.append("- none")

    # --- required approval authority ------------------------------------
    authority_lines, authority_gaps = _authority_lines(readiness, tuple(stage_statuses))
    undetermined.extend(authority_gaps)
    lines.append("\n## Required approval authority\n")
    if authority_lines:
        lines.extend(f"- {line}" for line in authority_lines)
    else:
        lines.append("- no blocked stage requires naming an authority here")

    # --- exactly one next action ------------------------------------------
    next_actions = _as_str_list(envelope.get("next_actions"))
    chosen = pick_next_action(next_actions)
    if chosen is None:
        undetermined.append(f"next action: {NO_NEXT_ACTION}")
        next_action_text = NO_NEXT_ACTION
    else:
        next_action_text = chosen
    lines.append("\n## Next action (exactly one)\n")
    lines.append(f"- {mask(next_action_text)}")

    if conflicts:
        lines.append("\n## Conflicts (surfaced, not resolved)\n")
        lines.extend(f"- {c}" for c in conflicts)

    if undetermined:
        lines.append("\n## Could not determine\n")
        lines.extend(f"- {u}" for u in undetermined)

    text = "\n".join(lines) + "\n"
    return FriendlySummary(
        schema_version=SCHEMA_VERSION,
        outcome=outcome,
        affected_artifacts=tuple(artifact_lines),
        stage_statuses=tuple(stage_statuses),
        blocker_groups=tuple(blocker_groups),
        warnings=tuple(warning_lines),
        required_authority=tuple(authority_lines),
        next_action=next_action_text,
        undetermined=tuple(undetermined),
        conflicts=tuple(conflicts),
        timestamp=timestamp,
        text=mask(text),
    )


def compose_comment(summary: FriendlySummary) -> StickyComment:
    """Compose the sticky-comment body: the stable ``MARKER`` + the summary
    text, masked with extra force (this is the public-egress surface).
    Pure and deterministic; posting the comment is a separate opt-in wrapper.
    """
    body = f"{MARKER}\n{mask(summary.text)}"
    return StickyComment(schema_version=SCHEMA_VERSION, marker=MARKER, body=body)


def find_existing(comment_bodies: Sequence[str]) -> tuple[str, int | None]:
    """Decide "update" (target the first same-marker comment) vs "create"
    (no marker match). Never returns "create" when a marker match exists, so
    a re-run never posts a second sticky comment."""
    for index, body in enumerate(comment_bodies):
        if MARKER in body:
            return ("update", index)
    return ("create", None)
