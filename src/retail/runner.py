from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .core import Finding, RegisteredRule, RuleContext, RuleTier, Severity

# git's "not a git repository" sentinel exit code (the expected non-repo case).
_GIT_NOT_A_REPO = 128


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
    result = subprocess.run(
        ["git", "ls-files"],
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
    # git ls-files already emits forward slashes; split on newlines, drop blanks.
    return tuple(line for line in result.stdout.splitlines() if line)


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
    """The INFO finding emitted in place of a skipped KIT_SELF rule (Spec A)."""
    return Finding(
        rule_id=registered.id,
        severity=Severity.INFO,
        message="skipped (kit-self rule; repo not kit-bootstrapped)",
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


def _exit_code(findings: list[Finding]) -> int:
    """1 if any ERROR finding is present, else 0 (WARNING/INFO never fail)."""
    return 1 if any(f.severity is Severity.ERROR for f in findings) else 0


def run(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> int:
    """Default human-readable output: one ``_format`` line per finding.

    This is the default ``retail check`` output and its text shape is a contract
    (CI diffs against it). It iterates inline rather than reusing ``_collect`` so
    its behavior stays exactly what it was before B2; the JSON output is a
    SEPARATE path (``run_json``). ``bootstrapped`` gates the KIT_SELF tier skip
    (Spec A); it defaults True so the kit's own (bootstrapped) repo is unchanged.
    """
    exit_code = 0
    for registered in rules:
        for finding in _rule_findings(registered, ctx, bootstrapped=bootstrapped):
            print(_format(finding))
            if finding.severity is Severity.ERROR:
                exit_code = 1
    return exit_code


def run_json(
    rules: tuple[RegisteredRule, ...], ctx: RuleContext, *, bootstrapped: bool = True
) -> int:
    """Opt-in structured output: one JSON document of all findings on stdout.

    Prints a single object ``{"findings": [...], "exit_code": N}`` so a consumer
    can parse the result without scraping the text lines. Returns the SAME exit
    code as ``run`` (1 iff any ERROR finding). Rule behavior is unchanged — only
    the rendering differs. ``bootstrapped`` gates the KIT_SELF tier skip (Spec A).
    """
    findings = _collect(rules, ctx, bootstrapped=bootstrapped)
    exit_code = _exit_code(findings)
    print(
        json.dumps(
            {"findings": [f.to_dict() for f in findings], "exit_code": exit_code},
            indent=2,
        )
    )
    return exit_code
