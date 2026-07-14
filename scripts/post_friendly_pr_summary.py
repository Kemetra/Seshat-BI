"""Post/update the Friendly PR Summary sticky comment (spec 130, US3).

THIN, OPT-IN WRAPPER -- not part of the tested deterministic core. The core
(rendering, masking, classification, comment composition) lives in
``seshat.pr_summary`` and is unit-tested in ``tests/unit/test_pr_summary.py``
with no network. This script is the only piece that touches the network (via
the ``gh`` CLI + ``GH_TOKEN``); it is invoked ONLY from the additive, off-by-
default CI step in ``.github/workflows/ci.yml`` (gated on the repo variable
``POST_FRIENDLY_PR_SUMMARY``). A repository that has not opted in never runs
this script and sees no behavior change (FR-015, SC-005).

Reads the review envelope JSON already produced by ``retail check --format
review`` (no new analysis, FR-001/FR-002). If that JSON is the CLI's error
shape (``{"outcome": "input_defect", ...}`` -- emitted by ``run_review`` on a
bad commit range, NEVER by ``build_review_result`` itself), the envelope is
treated as absent, the same honesty branch as "envelope absent" (spec 130
Edge Cases), not a third outcome value.

Best-effort readiness read: if the envelope names exactly one changed
``readiness-status.yaml``, that file is parsed (via ``pyyaml``, already an
installed ``[dev]``-extra dependency -- no new dependency added) and passed
through verbatim. Any other case (zero or several changed readiness files, or
an unreadable one) leaves readiness absent; ``render_summary`` then reports
each affected stage ``unknown``, sourced, never assumed ``pass``.

The base-branch temporal fingerprint diff (US2) is not wired in here yet --
fetching a base run is deferred (see docs/tools/friendly-pr-reviewer.md); the
rendered summary honestly states the new-vs-pre-existing distinction could
not be determined rather than defaulting every finding to "new".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from seshat.pr_summary import compose_comment, find_existing, render_summary


def _load_envelope(review_path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    # `run_review`'s CLI-only error shape -- not an outcome value
    # `build_review_result` itself ever emits. Same honesty branch as absent.
    if raw.get("outcome") == "input_defect":
        return None
    return raw


def _load_readiness(envelope: dict[str, Any] | None) -> dict[str, Any] | None:
    if envelope is None:
        return None
    changed = envelope.get("changed_readiness_state")
    if not isinstance(changed, list) or len(changed) != 1:
        return None
    try:
        import yaml  # lazy: already an installed [dev]-extra dependency

        data = yaml.safe_load(Path(str(changed[0])).read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _gh_json(*args: str) -> Any:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path, help="review.json path")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr", required=True, help="pull request number")
    args = parser.parse_args(argv)

    envelope = _load_envelope(args.review)
    readiness = _load_readiness(envelope)
    summary = render_summary(envelope, readiness)
    comment = compose_comment(summary)

    existing = _gh_json(
        "api", f"repos/{args.repo}/issues/{args.pr}/comments", "--paginate"
    )
    bodies = [c["body"] for c in existing] if isinstance(existing, list) else []
    action, index = find_existing(bodies)

    body_file = Path("friendly-pr-summary-body.txt")
    body_file.write_text(comment.body, encoding="utf-8")

    if action == "update" and index is not None:
        comment_id = existing[index]["id"]
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "PATCH",
                f"repos/{args.repo}/issues/comments/{comment_id}",
                "-F",
                f"body=@{body_file}",
            ],
            check=True,
        )
    else:
        subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "POST",
                f"repos/{args.repo}/issues/{args.pr}/comments",
                "-F",
                f"body=@{body_file}",
            ],
            check=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
