"""`retail explorer` handler (spec 120, US8): build.

Generates the self-contained offline readiness explorer HTML under the
contained `.seshat-output/` root. Fail-closed: a blocked disclosure result
(secret, absolute path, pass-without-evidence, blocked-without-reason)
prevents generation entirely -- no partial or redacted page is written.
Publishing the generated file anywhere is a separate, explicit human action;
this command only ever writes locally.

Exit codes (stable):
  0 explorer written
  1 generation blocked by disclosure findings
  2 input defect: uncontained output path
"""

from __future__ import annotations

import argparse
from pathlib import Path


def explorer_main(args: argparse.Namespace) -> int:
    from seshat.cli.guards import resolve_local_output
    from seshat.explorer.build import build_explorer_projection, render_explorer_html

    root = Path(args.repo).resolve()
    projection = build_explorer_projection(root)
    disclosure = projection["disclosure"]
    if disclosure["status"] != "pass":
        print("error: explorer generation is blocked by disclosure findings:")
        for finding in disclosure["findings"]:
            print(f"  [{finding['rule']}] {finding['locator']}: {finding['message']}")
        return 1
    try:
        target = resolve_local_output(root, args.output)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_explorer_html(projection, repo=root), encoding="utf-8")
    print(f"tables: {len(projection['tables'])}")
    print(f"written: {target.relative_to(root).as_posix()}")
    print(
        "The page is local and offline; publishing it anywhere is an explicit "
        "human action after disclosure review."
    )
    return 0
