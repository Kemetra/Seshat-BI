"""`retail drift` handler (F014 source-drift detector runtime).

Two-mode, mirroring `validate`: without a --dsn (no observed re-profile) it
reports the deferred [PENDING LIVE RE-PROFILE] state and returns 1 -- it NEVER
fabricates a comparison (Principle VIII). A non-conformant baseline is reported
as uncomparable rather than guessed at, and a missing --baseline path is a clean
error, never a raw traceback. The live leg (build a QueryRunner, call
retail.profile.profile, diff) is wired through the cli seams so tests patch it
without touching a real DB.
"""

from __future__ import annotations

import argparse
import json
import sys


def run_drift(args: argparse.Namespace) -> int:
    from retail.source_profile_reader import read_source_profile

    # A missing/unreadable --baseline path is a distinct failure from a
    # non-conformant one; surface it as a clean message (never a traceback),
    # matching run_validate's "actionable message, not a stack trace" posture.
    try:
        parsed = read_source_profile(args.baseline)
    except OSError as exc:
        print(
            f"retail drift: cannot read baseline {args.baseline!r}: {exc}",
            file=sys.stderr,
        )
        return 1

    if parsed.uncomparable is not None:
        print(f"retail drift: {parsed.uncomparable}", file=sys.stderr)
        return 1

    if not args.dsn:
        # Deferred-live: emit a schema-valid pending document; never a fake diff.
        from retail.drift import to_findings_dict

        doc = to_findings_dict(
            baseline=parsed.profile,
            observed=None,
            baseline_ref=str(args.baseline),
            evidence=[str(args.baseline)],
        )
        if getattr(args, "output_format", "text") == "json":
            print(json.dumps(doc, indent=2))
        print(
            "retail drift: [PENDING LIVE RE-PROFILE] -- no --dsn given, so no "
            "observed re-profile was taken. status=pending_live_reprofile + "
            "warning; no comparison fabricated. Pass --dsn to run the live leg.",
            file=sys.stderr,
        )
        return 1

    # Live leg: build the read-only runner via the cli seam (patched in tests),
    # re-profile the SAME table, diff, emit.
    #
    # KNOWN LIMITATION (flagged, not hidden): the baseline markdown proves PK
    # uniqueness but does not carry the PK column set as a machine field (it is
    # prose in the "Candidate grain & candidate PK" section). Until the reader
    # extracts it, the live re-profile uses the first parsed column as the
    # candidate PK -- correct for a single-key transaction grain, best-effort
    # otherwise. This path has no unit coverage (no live DB in the suite); it is
    # exercised by the filled baselines when a DSN is available (a tests/live_db
    # follow-up, consistent with the repo's honest-skip live-test posture).
    from retail import cli
    from retail.drift import to_findings_dict
    from retail.profile import profile as run_profile

    runner = cli._make_runner(args.dsn)
    candidate_pk = (parsed.profile.columns[0].name,)
    observed = run_profile(runner, parsed.profile.table, candidate_pk)
    doc = to_findings_dict(
        baseline=parsed.profile,
        observed=observed,
        baseline_ref=str(args.baseline),
        evidence=[str(args.baseline)],
        reprofiled_by="agent (retail.profile, read-only session)",
    )
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(doc, indent=2))
    else:
        n = len(doc["findings"])
        print(f"retail drift: status={doc['status']}; {n} finding(s)")
        for r in doc["blocking_reasons"]:
            print(f"  blocking_reason: {r}")
    return 0 if doc["status"] in ("pass", "warning") else 1
