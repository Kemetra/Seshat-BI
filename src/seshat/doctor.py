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


#: The Principle-I boundary marker: doctor is advisory, `check` is the gate.
_GATE_POINTER = (
    "\n\n(advisory digest -- the `{prog} check` gate exit code remains the "
    "authority; run it to gate.)"
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
        message="skipped (kit-self checks; not the kit's own repo)",
        locator="(foreign repo)",
    )


def collect_findings(ctx: RuleContext) -> list[Finding]:
    """Run every aggregated read-only check and return the combined findings.

    Pure: context in, findings out. No writes, no DB, no execution.

    Every aggregated check (A1/A3/SC1) is a KIT_SELF check, and the load-bearing
    docs are all kit-authored artifacts. A repo that is not the kit itself can't
    have them, so -- exactly as ``check`` does (Spec A) -- doctor SKIPS the whole
    aggregation there with a single INFO, rather than ERROR-ing on manifests a
    downloaded-into repo will never carry (#377). This keeps doctor and check in
    agreement on the same tree, including on a consumer repo that has run
    ``seshat init`` (issue #486).
    """
    from .kit_lint import is_kit_self_repo

    if not is_kit_self_repo(ctx.repo_root):
        return [_foreign_repo_skip()]

    findings: list[Finding] = []
    findings.extend(check_routes_resolve(ctx))
    findings.extend(check_route_coverage(ctx))
    findings.extend(check_status_claims(ctx))
    findings.extend(_probe_loadbearing(ctx))
    return findings


def format_digest(findings: list[Finding], prog: str = "seshat") -> str:
    """Render the findings as a human digest (no score -- a list + a count)."""
    if not findings:
        return f"{prog} doctor: no drift found across the aggregated read-only checks."
    lines = [f"{prog} doctor: {len(findings)} finding(s) across read-only checks:"]
    for rule_id, group in group_by_rule(findings).items():
        lines.append("")
        lines.append(f"{rule_id}: {len(group)} finding(s)")
        for f in group:
            lines.append(f"  [{f.severity.value}] {f.message} ({f.locator})")
        lines.append(f"  hint: {repair_hint(rule_id)}")
    lines.append(
        f"\n(advisory digest -- the `{prog} check` gate exit code remains the "
        "authority; run it to gate.)"
    )
    return "\n".join(lines)


#: Non-mutating repair guidance, keyed by the rule area that raised the finding.
#: Text ONLY -- doctor reads and reports, never fixes (M8: "repair hints that do
#: not modify files"). Nothing here is executed, and no entry is a command the
#: tool will run on the user's behalf.
_REPAIR_HINTS: dict[str, str] = {
    "A1": (
        "a route in docs/routing/routes.yaml does not resolve -- check the "
        "manifest exists and every target it names is a tracked file"
    ),
    "A3": (
        "route coverage is not a bijection -- a route lacks a surface, or a "
        "surface lacks a route; reconcile docs/routing/routes.yaml with the "
        "shipped verbs"
    ),
    "SC1": (
        "a prose status claim disagrees with its evidence -- correct the claim "
        "or the doc it points at; never loosen the claim to match stale prose"
    ),
    "DOCTOR": (
        "a load-bearing doc is untracked -- add the file, or `git add` it if it "
        "exists but was never committed"
    ),
}

#: The hint offered when a rule area has no specific entry above. Deliberately
#: names the read-only next step rather than inventing guidance.
_DEFAULT_HINT = (
    "inspect the locator above; this finding is advisory and no file was changed"
)


def repair_hint(rule_id: str) -> str:
    """The non-mutating repair hint for a rule area (M8 deliverable 3)."""
    return _REPAIR_HINTS.get(rule_id, _DEFAULT_HINT)


def group_by_rule(findings: list[Finding]) -> dict[str, list[Finding]]:
    """Group findings by their EXISTING ``rule_id`` (M8 deliverable 2).

    Derived from a field the findings already carry -- deliberately not a second
    classification vocabulary layered over the rule registry.
    """
    grouped: dict[str, list[Finding]] = {}
    for f in findings:
        grouped.setdefault(f.rule_id, []).append(f)
    return grouped


def build_digest_payload(findings: list[Finding]) -> dict[str, object]:
    """The machine-readable digest (M8 deliverable 1).

    Reuses the SHIPPED :meth:`Finding.to_dict` / ``FindingDict`` shape that
    ``check --format json`` already emits, deliberately rather than defining a
    second finding vocabulary: an agent that can read one verb's JSON can read
    this one. Categorical only -- a count, never a numeric health score (hard
    rule #9).
    """
    entries: list[dict[str, object]] = []
    for f in findings:
        entry: dict[str, object] = dict(f.to_dict())
        entry["repair_hint"] = repair_hint(f.rule_id)
        entries.append(entry)
    return {
        "findings": entries,
        "finding_count": len(findings),
    }


def next_allowed_action(repo_root: Path) -> str:
    """The truthful next readiness action, from the SHIPPED producer.

    Delegates to :func:`seshat.agent_next.build_agent_next_document`, which
    already owns "the one truthful next readiness action" -- deliberately NOT a
    second readiness model computed here. Naming an action is not taking it:
    doctor advances no stage and grants no approval (Principle V).
    """
    from .agent_next import build_agent_next_document

    document = build_agent_next_document(repo_root, None)
    action = document.get("next_allowed_action")
    return str(action) if action else "(no action available)"


def format_digest_with_next_action(
    findings: list[Finding], repo_root: Path, prog: str = "seshat"
) -> str:
    """The digest plus the agent-safe next action (M8 deliverable 4).

    The gate-authority pointer is KEPT: doctor must never read as a second gate
    (Principle I). M8 adds the next action; it does not license removing that
    boundary marker.
    """
    action = next_allowed_action(repo_root)
    digest = format_digest(findings, prog)
    if not findings:
        # The CLEAN digest is a one-liner carrying no gate pointer.
        # Append it so the Principle-I boundary marker survives on a
        # clean repo too -- otherwise the reassuring path is the one
        # that silently drops the governance note.
        digest += _GATE_POINTER.format(prog=prog)
    return digest + f"\n\nnext allowed action: {action}"


def run_doctor(
    repo_root: Path,
    strict: bool = False,
    prog: str = "seshat",
    output_format: str = "text",
) -> int:
    """Print the digest. Return 0 (advisory) unless ``strict`` and drift exists.

    ``--strict`` counts only actionable findings (WARNING/ERROR); an INFO -- such
    as the foreign-repo skip -- is not drift, so a not-kit-bootstrapped repo never
    fails strict for its (correctly skipped) kit manifests (#377).
    """
    import sys

    from .core import Severity
    from .runner import build_context

    try:
        ctx = build_context(repo_root)
    except (OSError, RuntimeError) as exc:
        # build_context -> _git_ls_files exercises git before anything else. A git
        # that cannot launch (OSError) or fails non-zero/non-128 (RuntimeError) must
        # surface as a clean error, not a raw traceback (the #371 crash class) --
        # same posture as the `check` handler. git exit-128 (non-repo) is tolerated
        # upstream, so doctor still runs on a fresh workspace. (#394, reframed.)
        print(
            f"error: git is required to run 'doctor' but failed: {exc}", file=sys.stderr
        )
        return 1
    findings = collect_findings(ctx)
    if output_format == "json":
        import json

        print(json.dumps(build_digest_payload(findings), indent=2))
    else:
        print(format_digest_with_next_action(findings, repo_root, prog))
    actionable = [
        f for f in findings if f.severity in (Severity.ERROR, Severity.WARNING)
    ]
    if strict and actionable:
        return 1
    return 0
