"""`retail passport` handler (spec 120, US4): export + verify.

`export` assembles a portable readiness passport from committed state and
writes it under the contained `.seshat-output/` root only after the document
passes the shared disclosure scan (fail closed: findings mean no file).
`verify` re-derives artifact identities and reports the categorical result;
it never rewrites the passport or any source artifact.

Exit codes (stable):
  0 export succeeded / every artifact verified or disclosed as unavailable
    (prose or deferred-live evidence has no hash to re-check -- a disclosed
    limit, not a failure)
  1 verification found changed or missing evidence,
    or export was blocked by disclosure findings
  2 input defect: unknown table, unreadable passport, incompatible schema,
    or an uncontained output path
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _print_verify_text(result: dict) -> None:
    print(f"passport: {result.get('passport_id')}")
    print(f"outcome: {result['outcome']}")
    match = result.get("source_revision_match")
    if match is not None:
        print(f"source_revision_match: {str(match).lower()}")
    for item in result["artifacts"]:
        line = f"  [{item['verification']}] {item['path']}"
        if item.get("note"):
            line += f" -- {item['note']}"
        print(line)
    if result.get("note"):
        print(f"note: {result['note']}")


def _print_disclosure_block(disclosure: dict) -> None:
    print("error: passport export is blocked by disclosure findings:")
    for finding in disclosure["findings"]:
        print(f"  [{finding['rule']}] {finding['locator']}: {finding['message']}")


def _print_export_result(
    args: argparse.Namespace, passport: dict, written: str
) -> None:
    if args.output_format == "json":
        print(json.dumps(passport, indent=2))
        return
    print(f"passport: {passport['passport_id']}")
    print(f"scope: {', '.join(passport['scope'])}")
    print(f"artifacts: {len(passport['artifacts'])} identities recorded")
    print(f"written: {written}")
    print(passport["authority_disclaimer"])


def _run_export(args: argparse.Namespace) -> int:
    from seshat.cli.guards import resolve_local_output
    from seshat.disclosure import scan_disclosure
    from seshat.ecosystem_contracts import ContractError
    from seshat.passport import build_passport

    root = Path(args.repo).resolve()
    try:
        passport = build_passport(root, tables=args.table or None)
        target = resolve_local_output(root, args.output)
    except (ContractError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    disclosure = scan_disclosure(passport)
    if disclosure["status"] != "pass":
        _print_disclosure_block(disclosure)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(passport, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    _print_export_result(args, passport, target.relative_to(root).as_posix())
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    from seshat.passport import verify_passport

    try:
        document = json.loads(Path(args.passport).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: passport is unreadable: {exc}")
        return 2
    result = verify_passport(Path(args.repo).resolve(), document)
    if args.output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        _print_verify_text(result)
    if result["outcome"] in ("verified", "unavailable"):
        return 0
    if result["outcome"] == "incompatible":
        return 2
    return 1


def passport_main(args: argparse.Namespace) -> int:
    if args.passport_command == "export":
        return _run_export(args)
    return _run_verify(args)
