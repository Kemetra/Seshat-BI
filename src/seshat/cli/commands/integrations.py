"""``seshat integrations setup`` command.

Three gates, each independent, and none of them implied by another:

* **The network gate is `--refresh`.** Without it nothing is looked up; the plan
  reads the catalog and the lock file only.
* **The write gate is `--apply`.** Without it nothing is cloned, installed, or
  registered, and the lock file is never written.
* **`--yes` only CONFIRMS.** It answers a prompt an already-requested `--apply`
  would have raised. It never turns on `--refresh` or `--apply` by itself,
  because a flag that silently widens what a command does is the flag an
  operator will reach for in CI by accident.

`--json` emits one JSON document and nothing else -- no text plan ahead of it, no
prompt, no banner -- so a consumer can pipe it straight into a parser. That also
means JSON mode never prompts: a machine has no answer to give.

`--repo` is validated rather than trusted, exactly as `seshat mcp` validates it:
this verb writes into `.seshat/integrations/`, and a directory that is not a
Seshat workspace is refused by name instead of being seeded with one.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path


def _attended() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _prompted(rendered: str) -> bool:
    from seshat.integrations_setup import confirm

    if not _attended():
        return False
    print(rendered)
    return confirm("Install these integrations now? [y/N]: ")


def _authorized(root: Path, components: tuple[str, ...]) -> tuple[bool, str]:
    """Whether a COMMITTED named-human approval authorizes provisioning.

    Split from `_approved` deliberately: intent and authority are different
    questions, and only this one may say yes. Returns `(authorized, next_action)`.
    """
    from seshat.integrations.approval import evaluate

    verdict = evaluate(root, components)
    return verdict.authorized, verdict.next_action


def _requested_components(outcome: object) -> tuple[str, ...]:
    """The component ids the plan would install, in recorded order.

    Derived from the plan, never from argv: the scope an approval is matched
    against must not be something the caller can assert.
    """
    rows = getattr(outcome, "rows", ()) or ()
    return tuple(str(getattr(row, "component", "")) for row in rows)


def _approved(args: Namespace, rendered: str) -> bool:
    """Whether the operator has REQUESTED an install (intent only).

    This answers intent, NOT authority. `--apply` is the request; `--yes`
    suppresses the prompt; `--yes` alone is not a request. None of these
    authorizes anything -- authorization is `_authorized()`, which reads a
    committed named-human approval at HEAD.

    Before spec 154 this function's True return WAS the authorization, so an
    agent-built `Namespace(apply=True, yes=True)` installed software with no
    human involved (issue #671). Intent is now necessary and never sufficient.
    """
    if not getattr(args, "apply", False):
        return False
    if getattr(args, "yes", False):
        return True
    # A machine-readable run must never block on a prompt.
    if getattr(args, "as_json", False):
        return False
    return _prompted(rendered)


def _workspace(repo: str) -> Path | None:
    from seshat.workspace_root import WorkspaceRootError, resolve_workspace_root

    try:
        return resolve_workspace_root(repo)
    except WorkspaceRootError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def integrations_main(args: Namespace) -> int:
    from seshat.integrations.catalog import DEFAULT_PROFILE, UnknownProfile
    from seshat.integrations_setup import (
        apply_profile,
        live_resolvers,
        plan_profile,
        render_json,
        render_text,
    )

    root = _workspace(args.repo)
    if root is None:
        return 2

    profile = getattr(args, "profile", None) or DEFAULT_PROFILE
    as_json = getattr(args, "as_json", False)
    harnesses = tuple(dict.fromkeys(getattr(args, "harness", ()) or ()))
    # Live resolvers are constructed ONLY for --refresh. Without the flag the
    # plan cannot reach the network even by mistake: there is no index to call.
    resolvers = live_resolvers() if getattr(args, "refresh", False) else None

    try:
        plan_kwargs = {"profile": profile, "resolvers": resolvers}
        if harnesses:
            plan_kwargs["harnesses"] = harnesses
        outcome = plan_profile(root, **plan_kwargs)
    except UnknownProfile as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if _approved(args, render_text(outcome)):
        # Intent is established. Authority is a separate question, and only a
        # committed named-human approval answers it (spec 154, issue #671).
        authorized, next_action = _authorized(root, _requested_components(outcome))
        if not authorized:
            print(
                "error: provisioning needs a committed named-human approval -- "
                f"{next_action}",
                file=sys.stderr,
            )
            return 2
        if resolvers is None:
            # Installing needs exact coordinates, and only --refresh resolves
            # them. Refusing here is what stops an --apply from falling back to
            # a floating reference.
            print(
                "error: --apply needs --refresh so every component resolves to an "
                "exact version, tag, or commit before anything is installed",
                file=sys.stderr,
            )
            return 2
        try:
            apply_kwargs = {"profile": profile, "resolvers": resolvers}
            if harnesses:
                apply_kwargs["harnesses"] = harnesses
            outcome = apply_profile(root, **apply_kwargs)
        except UnknownProfile as exc:  # pragma: no cover - already validated above
            print(f"error: {exc}", file=sys.stderr)
            return 2

    print(render_json(outcome) if as_json else render_text(outcome))
    return 1 if outcome.needs_action else 0
