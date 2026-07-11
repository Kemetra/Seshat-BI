"""`retail benchmark` handler (spec 120, US7): run + report.

`run` executes the named scenario manifests against the deterministic
scripted reference participant and writes the disclosed run document under
the contained `.seshat-output/` root. `report` renders a run document as the
categorical scenario matrix -- never an aggregate score, rank, or winner.

Exit codes (stable):
  0 run written / report rendered
  1 the run is incomplete (missing FR-041 disclosure)
  2 input defect: invalid scenario manifest, unreadable run document,
    or an uncontained output path
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _run_run(args: argparse.Namespace) -> int:
    from seshat.benchmark.model import BenchmarkError, RunConditions
    from seshat.benchmark.reference import reference_participant
    from seshat.benchmark.runner import load_scenarios, run_benchmark
    from seshat.cli.guards import resolve_local_output

    root = Path(args.repo).resolve()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conditions = RunConditions(
        instructions=(
            "Answer each scenario from its declared expected behavior and "
            "observable evidence (deterministic reference script)."
        ),
        started_at=started_at,
        completed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        environment={"runner": "seshat-cli", "participant_source": "reference"},
        repetitions=args.repetitions,
    )
    try:
        scenarios = load_scenarios(root, *args.scenarios)
        run = run_benchmark(scenarios, reference_participant(), conditions)
    except BenchmarkError as exc:
        print(f"error: {exc}")
        return 2
    try:
        target = resolve_local_output(root, args.output)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    document = run.to_document()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(document, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print(f"run: {run.run_id}")
    print(f"scenarios: {len(scenarios)}")
    print(f"repetitions: {run.repetitions}")
    print(f"written: {target.relative_to(root).as_posix()}")
    return 0


def _run_report(args: argparse.Namespace) -> int:
    from seshat.benchmark.render import render_report_document, render_report_text

    try:
        document = json.loads(Path(args.run).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: run document is unreadable: {exc}")
        return 2
    if not isinstance(document, dict):
        print("error: run document is not a mapping")
        return 2
    report = render_report_document(document)
    if args.output_format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_report_text(document))
    return 1 if report["state"] == "incomplete" else 0


def benchmark_main(args: argparse.Namespace) -> int:
    if args.benchmark_command == "run":
        return _run_run(args)
    return _run_report(args)
