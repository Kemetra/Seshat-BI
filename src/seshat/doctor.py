"""E7 -- ``retail doctor``: a read-only, repo-wide drift diagnostician.

``retail scaffold --doctor`` (062) checks ONE thing: the five-place rule-WIRING
lockstep. ``retail doctor`` is broader: it aggregates several existing READ-ONLY
checks into a single findings digest so a maintainer can spot repo drift at a
glance, without running the full gate or reading each surface by hand.

What it aggregates (all already shipped, all read-only):
  * A1  route registry resolution        (routes.check_routes_resolve)
  * A3  route-coverage bijection         (routes_coverage.check_route_coverage)
  * SC1 prose status-claim honesty       (status_claims.check_status_claims)
  * a lightweight file-existence probe of a few load-bearing docs.

Discipline: doctor **reads and reports, never fixes** (it writes nothing, opens no
DB, executes nothing). It emits **no numeric score** (hard rule #9): the digest is a
list of categorical findings + a count, never a health percentage. It **self-grants
nothing**. By default it is ADVISORY -- it prints the digest and exits 0 even when
findings exist -- so it never becomes a second gate competing with ``retail check``
(the gate remains the single authority, Principle I). Pass ``--strict`` to make it
exit non-zero when an ACTIONABLE finding (WARNING/ERROR) is present (opt-in, for a
maintainer who wants it to fail a pre-push hook). An INFO -- e.g. the foreign-repo
skip below -- is not drift and never fails ``--strict``.

Like ``retail check`` (Spec A), doctor SKIPS its aggregated kit-self checks in a
repo that is not kit-bootstrapped: those checks (and the load-bearing docs) are the
KIT's own artifacts, absent by design in a repo the kit was merely downloaded into,
so reporting them as errors there would be a false alarm (#377).
"""

from __future__ import annotations

from pathlib import Path

from .core import Finding, RuleContext
from .rules.routes import check_routes_resolve
from .rules.routes_coverage import check_route_coverage
from .rules.status_claims import check_status_claims

# A few load-bearing docs whose absence is itself a drift signal worth surfacing.
_LOADBEARING_DOCS: tuple[str, ...] = (
    "docs/glossary.md",
    "docs/knowledge-map.md",
    "COMPASS.md",
    "AGENTS.md",
    "docs/routing/routes.yaml",
)


def _probe_loadbearing(ctx: RuleContext) -> list[Finding]:
    """Report any load-bearing doc that is not a tracked file (read-only probe)."""
    from .core import Severity

    tracked = set(ctx.tracked_files)
    findings: list[Finding] = []
    for rel in _LOADBEARING_DOCS:
        if rel not in tracked:
            findings.append(
                Finding(
                    rule_id="DOCTOR",
                    severity=Severity.WARNING,
                    message=f"load-bearing doc {rel!r} is not a tracked file",
                    locator=rel,
                )
            )
    return findings


def _foreign_repo_skip() -> Finding:
    """The single INFO emitted in place of the aggregation on a foreign repo.

    Mirrors the runner's KIT_SELF skip (Spec A) so ``doctor`` presents the same
    verdict as ``check`` on the same tree.
    """
    from .core import Severity

    return Finding(
        rule_id="DOCTOR",
        severity=Severity.INFO,
        message="skipped (kit-self checks; repo not kit-bootstrapped)",
        locator="(foreign repo)",
    )


def collect_findings(ctx: RuleContext) -> list[Finding]:
    """Run every aggregated read-only check and return the combined findings.

    Pure: context in, findings out. No writes, no DB, no execution.

    Every aggregated check (A1/A3/SC1) is a KIT_SELF check, and the load-bearing
    docs are all kit-authored artifacts. A repo that is not kit-bootstrapped can't
    have them, so -- exactly as ``check`` does (Spec A) -- doctor SKIPS the whole
    aggregation there with a single INFO, rather than ERROR-ing on manifests a
    downloaded-into repo will never carry (#377). This keeps doctor and check in
    agreement on the same tree.
    """
    from .kit_lint import is_bootstrapped

    if not is_bootstrapped(ctx.repo_root):
        return [_foreign_repo_skip()]

    findings: list[Finding] = []
    findings.extend(check_routes_resolve(ctx))
    findings.extend(check_route_coverage(ctx))
    findings.extend(check_status_claims(ctx))
    findings.extend(_probe_loadbearing(ctx))
    return findings


def format_digest(findings: list[Finding]) -> str:
    """Render the findings as a human digest (no score -- a list + a count)."""
    if not findings:
        return "retail doctor: no drift found across the aggregated read-only checks."
    lines = [f"retail doctor: {len(findings)} finding(s) across read-only checks:"]
    for f in findings:
        lines.append(f"  [{f.severity.value}] {f.rule_id} {f.message} ({f.locator})")
    lines.append(
        "\n(advisory digest -- the `seshat check` gate exit code remains the "
        "authority; run it to gate.)"
    )
    return "\n".join(lines)


def run_doctor(repo_root: Path, strict: bool = False) -> int:
    """Print the digest. Return 0 (advisory) unless ``strict`` and drift exists.

    ``--strict`` counts only actionable findings (WARNING/ERROR); an INFO -- such
    as the foreign-repo skip -- is not drift, so a not-kit-bootstrapped repo never
    fails strict for its (correctly skipped) kit manifests (#377).
    """
    from .core import Severity
    from .runner import build_context

    ctx = build_context(repo_root)
    findings = collect_findings(ctx)
    print(format_digest(findings))
    actionable = [
        f for f in findings if f.severity in (Severity.ERROR, Severity.WARNING)
    ]
    if strict and actionable:
        return 1
    return 0
