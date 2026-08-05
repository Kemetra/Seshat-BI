"""``seshat integrations setup`` command."""

import sys
from pathlib import Path


def integrations_main(args) -> int:
    from seshat.integrations_setup import render_results, setup_integrations

    root = Path(args.repo)
    if args.apply or args.yes:
        results = setup_integrations(root, apply=True)
    else:
        planned = setup_integrations(root, apply=False)
        needs_approval = any(item.status == "planned" for item in planned)
        approved = False
        if needs_approval and sys.stdin.isatty() and sys.stdout.isatty():
            print(render_results(planned))
            try:
                answer = (
                    input("Install these integrations now? [y/N]: ").strip().lower()
                )
            except (EOFError, KeyboardInterrupt):
                answer = ""
            approved = answer in {"y", "yes"}
        results = setup_integrations(root, apply=True) if approved else planned

    print(render_results(results, as_json=args.as_json))
    return 1 if any(item.status in {"failed", "unavailable"} for item in results) else 0
