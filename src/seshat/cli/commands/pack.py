"""`retail pack` handler (spec 120, US5): scaffold + validate.

`scaffold` writes one new declarative pack skeleton at an explicit local
path. `validate` checks each named manifest and the cross-pack selection
graph, reporting every finding BEFORE any pack content could contribute to a
readiness output (FR-032). No global activation state exists: validating a
pack installs nothing.

Exit codes (stable):
  0 scaffold succeeded / every pack and the selection validated cleanly
  1 validation findings
  2 input defect: unknown category, malformed pack id, existing target,
    or an unreadable/schema-invalid manifest
"""

from __future__ import annotations

import argparse
import json


def _run_scaffold(args: argparse.Namespace) -> int:
    from seshat.packs.model import PackError, PackSpec
    from seshat.packs.scaffold import scaffold_pack

    spec = PackSpec(pack_id=args.pack_id, category=args.category, owner=args.owner)
    try:
        written = scaffold_pack(args.repo, spec, target_dir=args.dir)
    except PackError as exc:
        print(f"error: {exc}")
        return 2
    for path in written:
        print(f"written: {path}")
    print("next: fill in the starter content, then run the pack's verification.")
    return 0


def _validate_all(repo: str, manifest_paths: list[str]) -> tuple[list, list, bool]:
    from seshat.packs.validator import validate_pack, validate_selection

    manifests = []
    findings = []
    unreadable = False
    for manifest_path in manifest_paths:
        manifest, pack_findings = validate_pack(repo, manifest_path)
        findings.extend(pack_findings)
        if manifest is None:
            unreadable = True
        else:
            manifests.append(manifest)
    findings.extend(validate_selection(manifests))
    return manifests, findings, unreadable


def _print_validate_result(output_format: str, manifests: list, findings: list) -> None:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "status": "blocked" if findings else "pass",
                    "packs": [manifest.pack_id for manifest in manifests],
                    "findings": findings,
                },
                indent=2,
            )
        )
        return
    for finding in findings:
        print(f"[{finding['rule']}] {finding['locator']}: {finding['message']}")
    label = ", ".join(m.pack_id for m in manifests) or "none readable"
    print(f"packs: {label}")
    print(f"result: {'blocked' if findings else 'pass'}")


def _run_validate(args: argparse.Namespace) -> int:
    manifests, findings, unreadable = _validate_all(args.repo, args.pack)
    _print_validate_result(args.output_format, manifests, findings)
    if unreadable:
        return 2
    return 1 if findings else 0


def pack_main(args: argparse.Namespace) -> int:
    if args.pack_command == "scaffold":
        return _run_scaffold(args)
    return _run_validate(args)
