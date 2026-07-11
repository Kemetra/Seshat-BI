"""B3 -- live-surface import boundary guard.

The live-surface modules (``validate.py``, ``value_proxy.py``, ``semantic.py``,
``dax_gen.py``) are the ones that MAY touch a live database or read optional
dependencies -- but only LAZILY, inside the handler that actually connects. The
repo's deliberate invariant (constitution Principle VIII) is that importing any of
these modules opens nothing: every driver/network import is done inside a function,
never at module scope. Today that invariant is honored only as PROSE/policy (a
docstring + an inline ``# lazy`` comment); nothing enforces it structurally.

B3 makes it a structural ERROR rule -- the live-surface complement of B1
(``never_execute.py``), which guards the static-core modules. B3 reuses B1's
``module_scope_violations`` AST helper and forbidden-root sets UNCHANGED (Principle
II -- depend, never fork): it parses source text, it never imports or runs the
module, so the guard itself never executes. The policy inversion is only in WHICH
files are scanned -- B3's ``_LIVE_SURFACE`` set is provably disjoint from B1's
governed set, so the two halves never double-cover a file.

Severity is ERROR (matching B1): a module-scope connection-capable import in a
driver-free module is a proven breach of an absolute invariant, not a suspect
pattern with a legitimate override.

The four live-surface modules keep their driver imports lazy today, so B3 reports
zero findings on the current tree and fires only on a regression.

NOTE (ratified 2026-06-30): the registry id ``B3`` and the closed ``_LIVE_SURFACE``
set membership were resolved at the spec's ratify gate (see
``specs/048-live-surface-import-boundary-guard/spec.md`` ## Clarifications):
``metric_drift.py`` is excluded because it is an L3 *static* YAML check that opens
no connection; future live surfaces are added by a one-line set edit.
"""

from __future__ import annotations

from typing import Iterable

from ..core import Finding, RuleContext, Severity
from ..registry import register

# Reuse B1's AST helper + forbidden sets UNCHANGED -- no parallel parser.
from .never_execute import module_scope_violations

# The live-surface modules: they may connect, but ONLY lazily inside a handler, so
# importing them must open nothing. Repo-relative POSIX paths, matched against
# tracked files. Provably disjoint from B1's ``_GOVERNED_MODULES`` / prefix
# (asserted by a wiring test), so no file is double-covered.
_LIVE_SURFACE: frozenset[str] = frozenset(
    {
        "src/seshat/validate.py",
        "src/seshat/value_proxy.py",
        "src/seshat/semantic.py",
        "src/seshat/dax_gen.py",
        "src/seshat/dialect.py",
    }
)


@register(
    "B3", "No module-scope DB/network import in a live-surface module (keep it lazy)"
)
def check_live_surface_imports(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in sorted(p for p in ctx.tracked_files if p in _LIVE_SURFACE):
        try:
            source = (ctx.repo_root / rel).read_text(encoding="utf-8")
            names = module_scope_violations(source)
        except (SyntaxError, OSError) as exc:
            # A live-surface module that cannot be read or parsed fails loud as a
            # Finding rather than crashing the gate (never a vacuous green). OSError
            # covers a tracked-but-missing/unreadable file; SyntaxError covers
            # unparseable source.
            findings.append(
                Finding(
                    rule_id="B3",
                    severity=Severity.ERROR,
                    message=f"could not read/parse module for lazy-import check: {exc}",
                    locator=rel,
                )
            )
            continue
        for name in names:
            findings.append(
                Finding(
                    rule_id="B3",
                    severity=Severity.ERROR,
                    message=(
                        f"module-scope import of {name!r} in a live-surface module "
                        f"-- import it LAZILY inside the handler that connects; "
                        f"importing this module must never open a connection"
                    ),
                    locator=rel,
                )
            )
    return findings
