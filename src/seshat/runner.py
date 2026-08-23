from __future__ import annotations

import json
from collections.abc import Mapping
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable

from seshat.gitutil import GIT_HARDENING as _GIT_HARDENING
from seshat.gitutil import run_subprocess

from .core import Finding, RegisteredRule, RuleContext, RuleTier, Severity
from .rule_coverage import (
    ContextInput,
    CoverageRecord,
    CoverageState,
    Requirement,
    coverage_for,
)

# The Spec A tier gate is itself the ratified ruling that authorizes a KIT_SELF
# rule's absence in a foreign repo ("absence is not drift", kit_lint FR-006). It is
# therefore a legitimate `basis` -- cited, not self-granted. Without a citation like
# this, Requirement forbids not-applicable outright.
_TIER_GATE_BASIS = (
    "Spec A tier gate: KIT_SELF rule in a non-bootstrapped repo "
    "(kit_lint FR-006, 'absence is not drift')"
)

# git's "not a git repository" sentinel exit code (the expected non-repo case).
_GIT_NOT_A_REPO = 128

# This runner shells out to git with cwd=repo_root, which may be an
# EXTERNALLY-AUTHORED tree (e.g. a downloaded PBIP project reached via the
# adoption seams). Git reads that tree's own `.git/config`, so an
# attacker-supplied `core.fsmonitor` command runs on `git ls-files` -> RCE.
# `safe.directory` does not help (the victim owns the files). The hardening flags
# come from the single `gitutil.GIT_HARDENING` definition, imported above.


def _git_ls_files(repo_root: Path) -> tuple[str, ...]:
    """Return repo-relative POSIX paths for every tracked file.

    Dispatches on the git exit code so a governance gate never passes
    vacuously on a broken git:

    * ``0``   -> the tracked-file list.
    * ``128`` -> ``repo_root`` is not a git repository (e.g. a bare tmp dir in
      tests); return ``()`` — the expected non-repo case.
    * any other non-zero code -> ``RuntimeError`` so CI misconfiguration fails
      LOUD (red) rather than silently green.
    """
    result = run_subprocess(
        ["git", *_GIT_HARDENING, "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode == _GIT_NOT_A_REPO:
        return ()
    if result.returncode != 0:
        raise RuntimeError(
            f"git ls-files failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    # A newly initialized first-success workspace has no index yet. In that narrow
    # state, evaluate its non-ignored files so `git init` followed by `seshat check`
    # can verify the generated baseline before its first commit. Once anything is
    # tracked, the normal committed-files-only governance boundary is unchanged.
    tracked = tuple(line for line in result.stdout.splitlines() if line)
    if tracked:
        return tracked
    untracked = run_subprocess(
        ["git", *_GIT_HARDENING, "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if untracked.returncode != 0:
        raise RuntimeError(
            "git ls-files --others failed "
            f"(exit {untracked.returncode}): {untracked.stderr.strip()}"
        )
    return tuple(line for line in untracked.stdout.splitlines() if line)


def build_context(
    repo_root: Path,
    commit_range: str | None = None,
    commit_message: str | None = None,
) -> RuleContext:
    """Build the read-only context every rule receives.

    ``commit_range`` and ``commit_message`` are the contract-v2 invocation
    fields: populated by the CLI flags ``--commit-range`` / ``--commit-msg-file``
    and consumed by P2. Both default to ``None`` (no commit context), which is
    the local ``retail check`` mode.
    """
    return RuleContext(
        repo_root=repo_root,
        tracked_files=_git_ls_files(repo_root),
        commit_range=commit_range,
        commit_message=commit_message,
    )


def _format(finding: Finding) -> str:
    return (
        f"[{finding.severity.value}] {finding.rule_id} "
        f"{finding.message} ({finding.locator})"
    )


def _skip_finding(registered: RegisteredRule) -> Finding:
    """The INFO finding emitted in place of a skipped KIT_SELF rule (Spec A).

    Says "not the kit's own repo" rather than "not kit-bootstrapped": since issue
    #486 the tier keys on kit identity, and a repo that ran ``seshat init`` IS
    bootstrapped while still correctly skipping here -- the old wording described
    that repo inaccurately.
    """
    return Finding(
        rule_id=registered.id,
        severity=Severity.INFO,
        message="skipped (kit-self rule; not the kit's own repo)",
        locator="(foreign repo)",
    )


def _rule_findings(
    registered: RegisteredRule, ctx: RuleContext, *, bootstrapped: bool
) -> list[Finding]:
    """Findings for one rule, honoring the drop-in tier gate (Spec A).

    A KIT_SELF rule in a non-bootstrapped repo does NOT execute -- it yields a
    single INFO skip finding instead of ERROR-ing on a kit manifest the foreign
    repo cannot have. Every other case runs the rule normally.
    """
    if registered.tier is RuleTier.KIT_SELF and not bootstrapped:
        return [_skip_finding(registered)]
    return list(registered.rule(ctx))


def _collect(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> list[Finding]:
    """Run every rule once and gather findings in rule order, for ``run_json``.

    This is a fresh invocation of every rule (``run`` invokes them separately and
    inline). Rules are pure by contract (``core.Rule``: "context in, findings out,
    no side effects"), so a second invocation yields the same findings — that purity
    is what keeps the text and JSON outputs in agreement. ``bootstrapped`` gates the
    KIT_SELF tier skip (Spec A); defaults True so existing callers are unchanged.
    """
    return [
        finding
        for registered in rules
        for finding in _rule_findings(registered, ctx, bootstrapped=bootstrapped)
    ]


def collect_findings(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> list[Finding]:
    """Public in-memory finding seam for read-only protocol integrations."""
    return _collect(rules, ctx, bootstrapped=bootstrapped)


def _exit_code(findings: list[Finding]) -> int:
    """1 if any ERROR finding is present, else 0 (WARNING/INFO never fail)."""
    return 1 if any(f.severity is Severity.ERROR for f in findings) else 0


def _artifact_missing(repo_root: Path, path: str) -> bool:
    """Is this one artifact absent, or present but unopenable?

    Unreadable counts as missing on purpose. A permission denial, or a directory
    where a file was required, means the rule could not do its job, and calling
    that a pass would rebuild the exact silence the census exists to expose.
    """
    candidate = repo_root / path
    if not candidate.exists():
        return True
    try:
        with candidate.open("rb"):
            return False
    except OSError:
        return True


def _corpus_empty(tracked_files: tuple[str, ...], requirement: Requirement) -> bool:
    """Does NO tracked file match this glob (after the declared exclusions)?

    An empty corpus is the interesting case: a rule that iterates a file class and
    finds none returns no findings while having verified nothing. Matched against
    the tracked-file list rather than the working tree, because that list is what
    the rules themselves iterate.

    ``exclude`` mirrors the exemptions the rule's own iterator applies (committed
    ``tests/`` fixtures, a blank template). Without it a repo whose only matches
    are fixtures would be credited as ``evaluated`` for a rule that skipped every
    one of them -- a declaration that lies is worse than no declaration.
    """
    pattern = requirement.pattern or ""
    return not any(
        fnmatch(candidate, pattern) and not _excluded(candidate, requirement.exclude)
        for candidate in tracked_files
    )


def _excluded(candidate: str, exclude: tuple[str, ...]) -> bool:
    return any(fnmatch(candidate, pattern) for pattern in exclude)


def _commit_subject_missing(ctx: RuleContext) -> bool:
    """Did this invocation hand P2 any commit subject to judge?

    Delegates to P2's OWN subject resolution rather than re-deriving the three
    modes (commit-msg hook / explicit range / local HEAD~1 fallback). Two
    implementations of "is there a subject" would eventually disagree, and a
    census that disagrees with its rule is exactly the false assurance being
    removed. Imported lazily: the runner is generic infrastructure and must not
    import a rule module at load time.

    A malformed range is NOT missing input -- P2 reports it as an ERROR itself, so
    the rule spoke.
    """
    from .rules.git_meta import load_commit_subjects

    subjects, findings = load_commit_subjects(ctx)
    return not subjects and not findings


def _context_input_missing(ctx: RuleContext, which: ContextInput) -> bool:
    """Resolve an invocation-field requirement. Unknown field = fail loud."""
    if which is ContextInput.COMMIT_SUBJECTS:
        return _commit_subject_missing(ctx)
    raise RuntimeError(  # pragma: no cover -- closed enum; guards a future member
        f"no coverage resolver for context input {which!r}; add one rather than "
        "letting an unresolvable requirement read as present"
    )


def _missing_for(ctx: RuleContext) -> Callable[[Requirement], bool]:
    """Resolve any LEAF requirement form against the real repo/invocation.

    Groups never reach here: ``rule_coverage`` resolves the alternation and hands
    this predicate one alternative at a time.
    """

    def missing(requirement: Requirement) -> bool:
        if requirement.context is not None:
            return _context_input_missing(ctx, requirement.context)
        if requirement.pattern is not None:
            return _corpus_empty(ctx.tracked_files, requirement)
        return _artifact_missing(ctx.repo_root, requirement.path or "")

    return missing


def coverage_census(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> tuple[CoverageRecord, ...]:
    """One coverage record per rule: did this rule actually run?

    Answers a question findings alone cannot. An empty finding list is ambiguous --
    it means "checked and clean" OR "input absent, never checked" -- and this census
    separates the two. It performs no rule execution and cannot change a verdict.

    A KIT_SELF rule gated off by ``bootstrapped=False`` is ``not-applicable``, citing
    the Spec A tier gate as its basis rather than being silently dropped.
    """
    missing = _missing_for(ctx)
    records: list[CoverageRecord] = []
    for registered in rules:
        if registered.tier is RuleTier.KIT_SELF and not bootstrapped:
            records.append(
                CoverageRecord(
                    rule_id=registered.id,
                    state=CoverageState.NOT_APPLICABLE,
                    reason="skipped by the drop-in tier gate (kit-self rule)",
                    basis=_TIER_GATE_BASIS,
                )
            )
            continue
        records.append(coverage_for(registered, missing=missing))
    return tuple(records)


def explain_renderer(
    guidance: Mapping[str, Mapping[str, str]],
) -> Callable[[Finding], str]:
    """A finding -> annotation renderer bound to one guidance mapping.

    Passing ``run`` a single optional renderer (rather than an ``explain`` flag plus
    its data) keeps the annotation decision in ONE argument and the rendering out of
    the emit loop: ``run`` prints whatever string comes back and never branches on
    whether guidance exists.
    """

    def render(finding: Finding) -> str:
        return "\n".join(_explain_lines(finding, guidance))

    return render


def _explain_lines(
    finding: Finding, guidance: Mapping[str, Mapping[str, str]]
) -> list[str]:
    """The indented ``means``/``fix`` continuation lines for one finding, if authored.

    ADDITIVE and display-only: an id with no authored entry, an entry with neither
    field, and an entry of the WRONG SHAPE all yield nothing, so the finding renders
    exactly as it does without the flag rather than asserting guidance nobody wrote.

    The shape check is not defensive padding: valid YAML can hold a half-edited entry
    (``rules: {D8: "unfinished"}``), which is a string, not a mapping. Reaching
    ``.get`` on it raised ``AttributeError`` out of a display-only path and crashed
    the whole check run (PR #706 review).
    """
    entry = guidance.get(finding.rule_id)
    if not isinstance(entry, Mapping):
        return []
    labelled = (("means", entry.get("means")), ("fix", entry.get("fix")))
    return [
        f"    {label}: {str(text).strip()}"
        for label, text in labelled
        if str(text or "").strip()
    ]


def run(
    rules: tuple[RegisteredRule, ...],
    ctx: RuleContext,
    *,
    bootstrapped: bool = True,
    annotate: Callable[[Finding], str] | None = None,
) -> int:
    """Default human-readable output: one ``_format`` line per finding.

    This is the default ``retail check`` output and its text shape is a contract
    (CI diffs against it). It iterates inline rather than reusing ``_collect`` so
    its behavior stays exactly what it was before B2; the JSON output is a
    SEPARATE path (``run_json``). ``bootstrapped`` gates the KIT_SELF tier skip
    (Spec A); it defaults True so the kit's own (bootstrapped) repo is unchanged.

    ``annotate`` (see ``explain_renderer``) APPENDS text under each finding and is
    the ``--explain`` seam. It never rewrites the finding line and never touches the
    exit code, so the text contract above still holds line-for-line. Its guidance is
    read for RENDERING ONLY -- ``docs/rules/rule-fixes.yaml`` states that ``seshat
    check`` does not consult it, because reader guidance must not become gate input.
    """
    exit_code = 0
    for registered in rules:
        for finding in _rule_findings(registered, ctx, bootstrapped=bootstrapped):
            print(_format(finding))
            annotation = annotate(finding) if annotate else ""
            if annotation:
                print(annotation)
            if finding.severity is Severity.ERROR:
                exit_code = 1
    return exit_code


def run_json(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> int:
    """Opt-in structured output: one JSON document of all findings on stdout.

    Prints a single object ``{"findings": [...], "coverage": [...], "exit_code": N}``
    so a consumer can parse the result without scraping the text lines. Returns the
    SAME exit code as ``run`` (1 iff any ERROR finding). Rule behavior is unchanged —
    only the rendering differs. ``bootstrapped`` gates the KIT_SELF tier skip (Spec A).

    ``coverage`` is ADDITIVE and advisory: it records whether each rule actually ran
    (see ``coverage_census``) and never contributes to ``exit_code``. Making an
    unevaluated rule fail the build is a separate, owner-ratified decision, because a
    fail-closed rule must be finding-free on main before it can land.

    The default text output (``run``) is deliberately NOT extended: its line shape is
    a contract that CI diffs against, so the census surfaces here and in the review
    pack instead.
    """
    findings = _collect(rules, ctx, bootstrapped=bootstrapped)
    exit_code = _exit_code(findings)
    census = coverage_census(rules, ctx, bootstrapped=bootstrapped)
    print(
        json.dumps(
            {
                "findings": [f.to_dict() for f in findings],
                "coverage": [record.to_dict() for record in census],
                "exit_code": exit_code,
            },
            indent=2,
        )
    )
    return exit_code


def run_sarif(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> int:
    """Emit SARIF 2.1.0 with the same findings and exit policy as text/JSON."""
    from .sarif import sarif_document

    findings = _collect(rules, ctx, bootstrapped=bootstrapped)
    print(json.dumps(sarif_document(findings), indent=2))
    return _exit_code(findings)


def run_review(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> int:
    """Emit the stable change-review envelope without expanding gate authority."""
    from .review_integration import build_review_result
    from .status_surface import build_status_projection

    findings = _collect(rules, ctx, bootstrapped=bootstrapped)
    status = build_status_projection(ctx.repo_root)
    next_actions = [
        table["next_action"]
        for table in status["tables"]
        if isinstance(table.get("next_action"), str) and table["next_action"]
    ]
    try:
        result = build_review_result(
            findings,
            repo_root=ctx.repo_root,
            commit_range=ctx.commit_range,
            next_actions=next_actions,
        )
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "outcome": "input_defect",
                    "error": str(exc),
                    "exit_code": 2,
                },
                indent=2,
            )
        )
        return 2
    result["exit_code"] = _exit_code(findings)
    print(json.dumps(result, indent=2))
    return result["exit_code"]
