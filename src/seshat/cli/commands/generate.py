"""`retail generate` handler: verified DAX measure generation from a contract.

Extracted verbatim from the former ``retail/cli.py`` (CodeScene hotspot split).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run_generate(args: argparse.Namespace) -> int:
    """Generate a verified DAX measure from a metric contract YAML.

    Lazy imports (dax_gen, yaml via load_contract) live INSIDE this handler so
    the stdlib-only `retail check` import chain never pulls them. Fail-closed:
    stdout carries ONLY verified output; every refusal/error writes to stderr
    and returns 1, leaving stdout empty (safe for shell redirection).

    --out guard: resolve the path before writing; refuse if it resolves under
    the repo's powerbi/ directory (prevents model mutation), and refuse if the
    target file already exists (no silent overwrite).
    """
    import json

    from seshat.dax_gen import generate_measure, load_contract

    # 1. Read and parse the contract file.
    try:
        contract = load_contract(args.contract)
    except Exception as exc:
        print(f"[error] cannot read contract: {exc}", file=sys.stderr)
        return 1

    # 2. Validate required `name` field.
    name = contract.get("name")
    if not name:
        print("[error] contract has no `name`", file=sys.stderr)
        return 1

    # 3. Generate the measure (fail-closed: refuses bad contracts).
    result = generate_measure(
        contract.get("definition") or {},
        name=name,
        doc_intent=contract.get("formula_intent"),
    )
    if not result.ok:
        print(f"[refused] {name}: {result.reason}", file=sys.stderr)
        return 1

    # 4a. --out mode: write to a file with powerbi/ and overwrite guards.
    if args.out:
        out = Path(args.out).resolve()
        # PRIMARY guard (cwd-INDEPENDENT, defense in depth): refuse if ANY path
        # component of the resolved target is `powerbi` (case-insensitive). This
        # catches absolute paths into any powerbi/ tree, `../powerbi`, and nested
        # cases regardless of the process cwd -- closing the cwd-anchored hole.
        if "powerbi" in [p.lower() for p in out.parts]:
            print(
                f"[refused] --out resolves under powerbi/: {out}",
                file=sys.stderr,
            )
            return 1
        # SECONDARY guard (cwd-relative, cheap): the live model under THIS cwd.
        powerbi = (Path.cwd() / "powerbi").resolve()
        if out == powerbi or powerbi in out.parents:
            print(
                f"[refused] --out resolves under powerbi/: {out}",
                file=sys.stderr,
            )
            return 1
        if out.exists():
            print(f"[refused] --out file already exists: {out}", file=sys.stderr)
            return 1
        # M3: do NOT silently create parent dirs -- refuse cleanly if absent.
        if not out.parent.exists():
            print(
                f"[refused] --out parent directory does not exist: {out.parent}",
                file=sys.stderr,
            )
            return 1
        out.write_text(result.tmdl_block, encoding="utf-8")
        return 0

    # 4b. Stdout mode: emit verified output only.
    if args.fmt == "json":
        print(
            json.dumps(
                {
                    "ok": True,
                    "dax": result.dax,
                    "tmdl_block": result.tmdl_block,
                    "warnings": list(result.warnings),
                }
            )
        )
    else:
        print(result.tmdl_block)
    return 0
