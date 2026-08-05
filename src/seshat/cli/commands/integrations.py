"""``seshat integrations setup`` command.

The default run is a plan. Installation happens only when the operator says so:
`--apply`, `--yes`, or a "yes" at an interactive prompt. A piped or CI run has no
prompt to answer, so it reports the plan and changes nothing.

`--repo` is validated rather than trusted, exactly as `seshat mcp` validates it:
this verb writes into `.seshat/integrations/`, and a directory that is not a
Seshat workspace is refused by name instead of being seeded with one.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from seshat.integrations_setup import IntegrationResult


def _attended() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _prompted(planned: list[IntegrationResult]) -> bool:
    from seshat.integrations_setup import confirm, render_results

    if not _attended():
        return False
    print(render_results(planned))
    return confirm("Install these integrations now? [y/N]: ")


def _approved(args: Namespace, planned: list[IntegrationResult]) -> bool:
    if args.apply:
        return True
    if args.yes:
        return True
    if not any(item.status == "planned" for item in planned):
        return False
    return _prompted(planned)


def _workspace(repo: str) -> Path | None:
    from seshat.workspace_root import WorkspaceRootError, resolve_workspace_root

    try:
        return resolve_workspace_root(repo)
    except WorkspaceRootError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def integrations_main(args: Namespace) -> int:
    from seshat.integrations_setup import (
        needs_operator_action,
        render_results,
        setup_integrations,
    )

    root = _workspace(args.repo)
    if root is None:
        return 2
    planned = setup_integrations(root, apply=False)
    results = (
        setup_integrations(root, apply=True) if _approved(args, planned) else planned
    )
    print(render_results(results, as_json=args.as_json))
    return 1 if needs_operator_action(results) else 0
