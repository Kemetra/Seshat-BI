"""Orchestration.

fixture self-test -> build -> workspace -> assertions -> calibration -> journey
-> raw leak check -> findings -> quorum -> diff.
"""

from __future__ import annotations

import subprocess
import sys
import time
from argparse import Namespace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from scripts.adopter_sim import agent as agent_mod
from scripts.adopter_sim.baseline import (
    diff_findings,
    findings_baseline_path,
    load_findings_baseline,
    load_timings_reference,
    timings_baseline_path,
    update_findings_baseline,
    write_timings_reference,
)
from scripts.adopter_sim.blindness import assert_no_leak, run_pre_journey_assertions
from scripts.adopter_sim.env import build_client_env
from scripts.adopter_sim.evaluate import (
    STEP_FAILED,
    StepOutcome,
    cascade,
    evaluate_step,
)
from scripts.adopter_sim.exitcodes import Exit, RunOutcome, classify
from scripts.adopter_sim.fixtures import assert_clean, assert_messy
from scripts.adopter_sim.history import (
    append_invocation,
    dataset_history,
    flaky_keys,
    invocation_history_path,
    load_invocation_history,
)
from scripts.adopter_sim.journey import load_journey
from scripts.adopter_sim.metrics import TOLERANCE, gate, median, out_of_band
from scripts.adopter_sim.model import (
    NOT_EVALUABLE,
    NOT_RUN,
    AdopterSimError,
    Journey,
)
from scripts.adopter_sim.quorum import escalate, tally
from scripts.adopter_sim.workspace import (
    WorkspaceRequest,
    materialize,
    new_run_id,
    resolve_root,
    workspace_root,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "benchmark" / "journeys"
BUNDLE_ROOT = REPO_ROOT / "integrations" / "claude-code" / "seshat-bi"


def _fail(code: Exit, exc: AdopterSimError, prefix: str = "") -> Exit:
    print(f"[FAIL] {prefix}{exc}", flush=True)
    return code


def _resolve_driver(driver: object | None) -> tuple[object | None, bool]:
    """The driver to use, and whether the invocation is therefore partial."""
    if driver is not None:
        return driver, False
    if agent_mod.available():
        return agent_mod.ClaudeCodeDriver(), False
    print(
        "[SKIP] Claude Code CLI not available headless; agent-driven steps will "
        "be recorded not_run and the invocation labelled partial",
        flush=True,
    )
    return None, True


def _gather_runs(
    *,
    journey: Journey,
    wheel: Path,
    driver: object | None,
    args: Namespace,
    started: float,
) -> tuple[dict[str, list[dict[str, object]]], bool]:
    """Runs grouped BY DATASET, plus whether the ceiling truncated them.

    Grouping is load-bearing: pooling clean and messy would let a 1-of-3 flake on
    each add up to a false `confirmed` under the two-vote quorum.
    """
    cohorts: dict[str, list[dict[str, object]]] = {}
    root = resolve_root()
    for dataset in args.datasets:
        cohorts.setdefault(dataset, [])
        for index in range(args.runs):
            if time.monotonic() - started > args.ceiling:
                print("[FAIL] invocation ceiling reached; run truncated", flush=True)
                return cohorts, True
            cohorts[dataset].append(
                _one_run(
                    journey=journey,
                    dataset=dataset,
                    index=index,
                    wheel=wheel,
                    driver=driver,
                    args=args,
                    root=root,
                )
            )
    return cohorts, False


def _report_verdicts(journey_name: str, verdicts) -> None:
    baseline = load_findings_baseline(findings_baseline_path(REPO_ROOT, journey_name))
    for row in diff_findings(verdicts, baseline):
        print(
            f"[{row.state.upper()}] {row.dataset or 'unknown'} step {row.step}: "
            f"{row.kind}",
            flush=True,
        )
    for verdict in verdicts:
        print(
            f"[{verdict.status.upper()}] {verdict.dataset or 'unknown'} step "
            f"{verdict.step} {verdict.kind} (seen {verdict.seen} of "
            f"{verdict.evaluable} evaluable runs): {verdict.detail}",
            flush=True,
        )
    if not verdicts:
        print("[OK] no findings", flush=True)
    return None


def _accept_baseline(
    journey_name: str, verdicts, args: Namespace, *, partial: bool
) -> None:
    update_findings_baseline(
        findings_baseline_path(REPO_ROOT, journey_name),
        verdicts,
        run_id=new_run_id(f"{journey_name}|accept"),
        kit_version=_kit_version(),
        invoked_by=args.invoked_by,
        partial=partial,
        single_run=args.runs == 1,
        aborted=False,
    )
    print("[OK] baseline updated", flush=True)
    return None


def _tally_cohorts(
    journey: Journey,
    cohorts: dict[str, list[dict[str, object]]],
    *,
    single_run: bool,
    repo_root: Path = REPO_ROOT,
) -> list:
    """Fold each dataset cohort into verdicts, carrying that cohort's history.

    Each cohort is tallied against ITS OWN previous-invocation history, for the
    same reason its runs are not pooled: a messy-only flake must never count
    toward a clean recurrence.
    """
    history = load_invocation_history(invocation_history_path(repo_root, journey.name))
    verdicts: list = []
    for dataset, runs in sorted(cohorts.items()):
        folded = tally(journey, runs, single_run=single_run, dataset=dataset)
        verdicts.extend(escalate(folded, dataset_history(history, dataset)))
    return verdicts


def run_invocation(args: Namespace, driver: object | None = None) -> Exit:
    journey = load_journey(SEED_DIR / f"{args.journey}.yaml")
    started = time.monotonic()

    try:
        _check_fixtures(args.datasets)
    except AdopterSimError as exc:
        return _fail(Exit.FIXTURE_FAILED, exc)

    active_driver, partial = _resolve_driver(driver)

    try:
        wheel = _build_wheel()
    except AdopterSimError as exc:
        return _fail(Exit.HARNESS_ERROR, exc)

    try:
        cohorts, truncated = _gather_runs(
            journey=journey,
            wheel=wheel,
            driver=active_driver,
            args=args,
            started=started,
        )
    except AdopterSimError as exc:
        return _fail(Exit.BLINDNESS_ABORT, exc, prefix="blindness: ")
    partial = partial or truncated

    single_run = args.runs == 1
    verdicts = _tally_cohorts(journey, cohorts, single_run=single_run)
    _report_verdicts(journey.name, verdicts)
    _record_history(journey.name, verdicts, single_run=single_run)
    metric_out_of_band = _report_timings(
        journey.name, cohorts, accept=bool(args.update_baseline)
    )

    if args.update_baseline:
        try:
            _accept_baseline(journey.name, verdicts, args, partial=partial)
        except AdopterSimError as exc:
            return _fail(Exit.HARNESS_ERROR, exc)

    return classify(
        RunOutcome(
            partial=partial,
            confirmed_findings=sum(1 for v in verdicts if v.status == "confirmed"),
            metric_out_of_band=metric_out_of_band,
        )
    )


def _kit_version() -> str:
    try:
        return version("seshat-bi")
    except PackageNotFoundError:
        return "unknown"


def _check_fixtures(datasets: list[str]) -> None:
    if "messy" in datasets:
        assert_messy(SEED_DIR / "datasets" / "messy" / "orders.csv")
    if "clean" in datasets:
        assert_clean(SEED_DIR / "datasets" / "clean" / "orders.csv")
    return None


def _build_wheel() -> Path:
    dist = REPO_ROOT / "dist"
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise AdopterSimError(f"wheel build failed:\n{result.stdout}\n{result.stderr}")
    wheels = sorted(dist.glob("*.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        raise AdopterSimError("wheel build produced no artifact")
    return wheels[-1]


def _one_run(
    *,
    journey: Journey,
    dataset: str,
    index: int,
    wheel: Path,
    driver,
    args: Namespace,
    root: Path,
) -> dict[str, object]:
    run_id = new_run_id(f"{journey.name}|{dataset}|{index}")
    paths = materialize(
        WorkspaceRequest(
            workspace=workspace_root(root, run_id),
            wheel=wheel,
            seed_dir=SEED_DIR,
            dataset=dataset,
            bundle_root=BUNDLE_ROOT,
        )
    )
    client_env = build_client_env(
        workspace=paths.root,
        venv_bin=paths.venv_bin,
        config_dir=paths.config_dir,
    )
    run_pre_journey_assertions(
        workspace=paths.root,
        repo_root=REPO_ROOT,
        venv_python=paths.venv_python,
        config_dir=paths.config_dir,
        bundle_manifest=paths.config_dir / "bundle-manifest.json",
        client_env=client_env,
    )

    calibration_ms, _, _ = _time_cli(
        [str(paths.venv_bin / "seshat"), "--version"], paths, client_env, args
    )

    raw_timings: dict[int, float] = {}
    outcomes, transcript = _execute_steps(
        journey=journey,
        paths=paths,
        client_env=client_env,
        driver=driver,
        args=args,
        raw_timings=raw_timings,
    )
    assert_no_leak("\n".join(transcript), REPO_ROOT)

    findings, evaluable = _collect_findings(journey, outcomes)
    # Normalise against THIS run's own calibration, so warm-cache and
    # process-start differences between runs cannot skew the ratios.
    return {
        "findings": findings,
        "evaluable": evaluable,
        "calibration": calibration_ms,
        "ratios": {
            step: (elapsed / calibration_ms) if calibration_ms else None
            for step, elapsed in raw_timings.items()
        },
        "raws": dict(raw_timings),
    }


def _artifact_violations(step, workspace: Path) -> list[str]:
    """Missing expect_artifacts and present forbid_artifacts.

    Exit code and reply text are not evidence on their own: a scaffold can exit
    zero without writing its artifacts, and a refusal can be worded while the
    forbidden file was written anyway.
    """
    problems = [
        f"expected artifact missing: {relative}"
        for relative in step.expect_artifacts
        if not (workspace / relative).exists()
    ]
    problems += [
        f"forbidden artifact present: {match.relative_to(workspace)}"
        for pattern in step.forbid_artifacts
        for match in workspace.glob(pattern)
    ]
    return problems


def _agent_step(step, paths, client_env, driver, args) -> tuple[StepOutcome, str]:
    reply = driver.run(
        step.prompt or "",
        cwd=paths.root,
        env=client_env,
        timeout=args.agent_timeout,
    )
    if getattr(reply, "failed", False):
        # An execution failure is not a categorical outcome.
        return (
            StepOutcome(step.number, "error", reply.text, False, reply.error),
            reply.text,
        )
    problems = _artifact_violations(step, paths.root)
    if problems:
        detail = "; ".join(problems)
        return (
            StepOutcome(
                step.number,
                "proceed",
                f"{reply.text}\n[POSTCONDITION] {detail}",
                False,
                detail,
            ),
            reply.text,
        )
    return (
        StepOutcome(step.number, reply.observed, reply.text, True, ""),
        reply.text,
    )


def _cli_step(step, paths, client_env, args, raw_timings) -> tuple[StepOutcome, str]:
    command = [str(paths.venv_bin / (step.command or ("seshat",))[0])]
    command += list((step.command or ())[1:])
    elapsed, output, ok = _time_cli(command, paths, client_env, args)
    raw_timings[step.number] = elapsed
    problems = _artifact_violations(step, paths.root) if ok else []
    if problems:
        detail = "; ".join(problems)
        return (
            StepOutcome(
                step.number,
                "error",
                f"{output}\n[POSTCONDITION] {detail}",
                False,
                detail,
            ),
            output,
        )
    return (
        StepOutcome(step.number, "proceed" if ok else "error", output, ok, ""),
        output,
    )


def _execute_steps(
    *,
    journey: Journey,
    paths,
    client_env: dict[str, str],
    driver,
    args: Namespace,
    raw_timings: dict[int, float],
) -> tuple[dict[int, StepOutcome], list[str]]:
    outcomes: dict[int, StepOutcome] = {}
    transcript: list[str] = []
    for step in journey.steps:
        if step.agent_driven and driver is None:
            outcomes[step.number] = StepOutcome(
                step.number, NOT_RUN, "", True, "agent CLI unavailable"
            )
            continue
        if step.agent_driven:
            outcome, text = _agent_step(step, paths, client_env, driver, args)
        else:
            outcome, text = _cli_step(step, paths, client_env, args, raw_timings)
        outcomes[step.number] = outcome
        transcript.append(text)
    return outcomes, transcript


def _collect_findings(
    journey: Journey, outcomes: dict[int, StepOutcome]
) -> tuple[list[tuple[int, str, str]], list[int]]:
    """Findings and evaluable steps.

    Only NOT_EVALUABLE dependents and NOT_RUN steps are skipped. A step that
    FAILED is evaluable and records its own finding -- otherwise a completely
    broken install would drop every step and report `[OK] no findings` with
    exit 0.
    """
    resolved = cascade(journey, outcomes)
    findings: list[tuple[int, str, str]] = []
    evaluable: list[int] = []
    for step in journey.steps:
        outcome = outcomes[step.number]
        state = resolved[step.number]
        if state == NOT_EVALUABLE or outcome.observed == NOT_RUN:
            continue
        evaluable.append(step.number)
        if state == "failed":
            detail = outcome.reason or outcome.output.strip()[:300] or "step failed"
            findings.append((step.number, STEP_FAILED, detail))
            continue
        findings.extend(
            (finding.step, finding.kind, finding.detail)
            for finding in evaluate_step(step, outcome.observed, outcome.output)
        )
    return findings, evaluable


def _time_cli(
    command: list[str], paths, client_env, args: Namespace
) -> tuple[float, str, bool]:
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=str(paths.root),
            env=dict(client_env),
            text=True,
            capture_output=True,
            timeout=args.cli_timeout,
        )
        output = result.stdout + result.stderr
        ok = result.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as exc:
        output = f"command failed: {exc}"
        ok = False
    return (time.monotonic() - start) * 1000.0, output, ok


def _median_by_step(runs: list[dict[str, object]], field: str) -> dict[int, float]:
    """Median of one recorded field, per step, across a cohort's runs.

    A missing measurement (ratio=None when calibration failed) is EXCLUDED from
    its median rather than folded in as a value, so an unmeasured step reports
    not_measured instead of a fabricated number.
    """
    values: dict[int, list[float]] = {}
    for run in runs:
        for step, value in (run.get(field) or {}).items():
            if value is not None:
                values.setdefault(step, []).append(value)
    return {step: median(measured) for step, measured in values.items()}


def _cohort_medians(
    runs: list[dict[str, object]],
) -> tuple[dict[int, float], dict[int, float]]:
    """Median raw ms and median of each run's OWN ratio, per step.

    Each run already divided its step timings by the calibration measured in
    that same run, so aggregating here cannot mix calibrations.
    """
    return _median_by_step(runs, "raws"), _median_by_step(runs, "ratios")


def _cohort_lines(
    dataset: str, raw_medians: dict[int, float], ratio_medians: dict[int, float]
) -> list[str]:
    """One line per step. A step with no usable ratio reports not_measured."""
    lines: list[str] = []
    for step in sorted(raw_medians):
        ratio = ratio_medians.get(step)
        rendered = f"{ratio:.2f}" if ratio is not None else "not_measured"
        lines.append(
            f"{dataset} step {step}: {raw_medians[step]:.0f} ms ratio={rendered}"
        )
    return lines


def _report_timings(
    journey_name: str,
    cohorts: dict[str, list[dict[str, object]]],
    *,
    repo_root: Path = REPO_ROOT,
    accept: bool = False,
) -> bool:
    """Record and print timings per cohort, and gate against the reference.

    Returns True when a gated metric left the tolerance band, in either
    direction (issue #567).

    The run that finds no accepted reference RECORDS one instead of judging
    against it: there is nothing to compare to yet, and gating against an absent
    reference would fail every first run. A later run compares but does NOT
    rewrite the reference -- refreshing it every run would make each run its own
    baseline, so a 24%-per-run drift would never trip the 25% band. Moving an
    accepted reference stays explicit, via --update-baseline.
    """
    ratios: dict[str, dict[int, float]] = {}
    raws: dict[str, dict[int, float]] = {}
    lines: list[str] = []
    for dataset, runs in sorted(cohorts.items()):
        raws[dataset], ratios[dataset] = _cohort_medians(runs)
        lines.extend(_cohort_lines(dataset, raws[dataset], ratios[dataset]))
    if not lines:
        return False
    for line in lines:
        print(f"[TIME] {line}", flush=True)

    path = timings_baseline_path(repo_root, journey_name)
    reference = load_timings_reference(path)
    if accept or not reference:
        write_timings_reference(path, ratios, raws=raws)
        print(
            f"[TIME] recorded the accepted reference in {path.name}; "
            "not gated this run",
            flush=True,
        )
        return False

    rows = gate(ratios, reference, tolerance=TOLERANCE)
    for row in rows:
        print(
            f"[TIME] {row.dataset} step {row.step}: {row.verdict} "
            f"(ratio {row.current:.2f} vs accepted {row.reference:.2f})",
            flush=True,
        )
    failed = out_of_band(rows)
    state = "OUT OF BAND" if failed else "within band"
    print(f"[TIME] tolerance band +/-{TOLERANCE:.0%}: {state}", flush=True)
    return failed


def _record_history(
    journey_name: str,
    verdicts: list,
    *,
    single_run: bool,
    repo_root: Path = REPO_ROOT,
) -> None:
    """Persist this invocation's flaky keys for the next invocation to read.

    A `--runs 1` invocation records nothing: it reproduces nothing, so it can
    neither start nor continue a recurrence streak, and writing an empty entry
    would silently BREAK an existing one.
    """
    if single_run:
        return None
    append_invocation(
        invocation_history_path(repo_root, journey_name), flaky_keys(verdicts)
    )
    return None
