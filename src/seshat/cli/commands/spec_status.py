"""`seshat spec-status` -- validate or normalize a spec's `**Status**:` line.

This is the PRODUCTION seam for spec 151 FR-025. Upstream Spec Kit's
`create-new-feature.ps1` copies `spec-template.md` verbatim, so a freshly
scaffolded spec carries `**Status**: Draft` -- capital, and outside the closed
ADR-0019 vocabulary. Seshat must not edit the upstream template to change what
it seeds (that is the fork spec 151 removed), and it must not edit the upstream
scaffold script either -- both files are tracked in the spec-kit manifests. So
the normalization runs from Seshat's own CLI, on the scaffolded OUTPUT:

    /speckit-specify ...            # upstream scaffolds the spec, untouched
    seshat spec-status --fix ...    # Seshat normalizes what it produced

`--fix` is idempotent and fails closed: an unreadable file, a missing status
line, or a value that is not a case variant of a vocabulary value is an error,
never a silent rewrite.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def spec_status_main(args: argparse.Namespace) -> int:
    from seshat.spec_status_policy import (
        StatusPolicyError,
        normalize_spec_file,
        validate_spec_file,
    )

    target = Path(args.spec)
    if getattr(args, "fix", False):
        try:
            changed = normalize_spec_file(target)
        except StatusPolicyError as exc:
            print(f"[error] {exc}")
            return 1
        print(
            f"[ok] normalized {target.as_posix()}"
            if changed
            else f"[ok] already canonical: {target.as_posix()}"
        )
        return 0

    verdict = validate_spec_file(target)
    if verdict.ok:
        print(f"[ok] {target.as_posix()}: status `{verdict.value}`")
        return 0
    print(f"[error] {target.as_posix()}: {verdict.detail}")
    return 1
