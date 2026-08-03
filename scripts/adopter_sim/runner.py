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
    timings_baseline_path,
    update_findings_baseline,
)
from scripts.adopter_sim.blindness import assert_no_leak, run_pre_journey_assertions
from scripts.adopter_sim.env import build_client_env
from scripts.adopter_sim.evaluate import StepOutcome, cascade, evaluate_step
from scripts.adopter_sim.exitcodes import Exit, RunOutcome, classify
from scripts.adopter_sim.fixtures import assert_clean, assert_messy
from scripts.adopter_sim.journey import load_journey
from scripts.adopter_sim.metrics import TOLERANCE, median, normalise
from scripts.adopter_sim.model import NOT_RUN, AdopterSimError, Journey
from scripts.adopter_sim.quorum import tally
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
    raw_timings: dict[int, list[float]],
    started: float,
) -> tuple[list[dict[str, object]], bool]:
    """Every (dataset, repeat) run, plus whether the ceiling truncated them."""
    runs: list[dict[str, object]] = []
    root = resolve_root()
    for dataset in args.datasets:
        for index in range(args.runs):
            if time.monotonic() - started > args.ceiling:
                print("[FAIL] invocation ceiling reached; run truncated", flush=True)
                return runs, True
            runs.append(
                _one_run(
                    journey=journey,
                    dataset=dataset,
                    index=index,
                    wheel=wheel,
                    driver=driver,
                    args=args,
                    raw_timings=raw_timings,
                    root=root,
                )
            )
    return runs, False


def _report_verdicts(journey_name: str, verdicts) -> None:
    baseline = load_findings_baseline(findings_baseline_path(REPO_ROOT, journey_name))
    for row in diff_findings(verdicts, baseline):
        print(f"[{row.state.upper()}] step {row.step}: {row.kind}", flush=True)
    for verdict in verdicts:
        print(
            f"[{verdict.status.upper()}] step {verdict.step} {verdict.kind} "
            f"(seen {verdict.seen} of {verdict.evaluable} evaluable runs): "
            f"{verdict.detail}",
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

    raw_timings: dict[int, list[float]] = {}
    try:
        runs, truncated = _gather_runs(
            journey=journey,
            wheel=wheel,
            driver=active_driver,
            args=args,
            raw_timings=raw_timings,
            started=started,
        )
    except AdopterSimError as exc:
        return _fail(Exit.BLINDNESS_ABORT, exc, prefix="blindness: ")
    partial = partial or truncated

    verdicts = tally(journey, runs, single_run=args.runs == 1)
    _report_verdicts(journey.name, verdicts)
    metric_out_of_band = _report_timings(journey.name, raw_timings)

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
    raw_timings: dict[int, list[float]],
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
    return {"findings": findings, "evaluable": evaluable, "calibration": calibration_ms}


def _agent_step(step, paths, client_env, driver, args) -> tuple[StepOutcome, str]:
    reply = driver.run(
        step.prompt or "",
        cwd=paths.root,
        env=client_env,
        timeout=args.agent_timeout,
    )
    return (
        StepOutcome(step.number, reply.observed, reply.text, True, ""),
        reply.text,
    )


def _cli_step(step, paths, client_env, args, raw_timings) -> tuple[StepOutcome, str]:
    command = [str(paths.venv_bin / (step.command or ("seshat",))[0])]
    command += list((step.command or ())[1:])
    elapsed, output, ok = _time_cli(command, paths, client_env, args)
    raw_timings.setdefault(step.number, []).append(elapsed)
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
    raw_timings: dict[int, list[float]],
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
    """Findings and evaluable steps, skipping not_evaluable and not_run steps."""
    resolved = cascade(journey, outcomes)
    findings: list[tuple[int, str, str]] = []
    evaluable: list[int] = []
    for step in journey.steps:
        outcome = outcomes[step.number]
        if resolved[step.number] != "ok" or outcome.observed == NOT_RUN:
            continue
        evaluable.append(step.number)
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


def _report_timings(journey_name: str, raw_timings: dict[int, list[float]]) -> bool:
    """Record and print timings.

    Returns False always: there is no accepted timing reference until a first
    full run is recorded, and gating against an absent baseline would fail every
    first run. See the plan's Self-Review for the follow-up that enforces it.
    """
    if not raw_timings:
        return False
    medians = {step: median(values) for step, values in raw_timings.items()}
    timings = normalise(medians, medians.get(min(medians)))
    path = timings_baseline_path(REPO_ROOT, journey_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"step {timing.step}: {timing.raw_ms:.0f} ms ratio={timing.ratio}"
        for timing in timings
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for line in lines:
        print(f"[TIME] {line}", flush=True)
    print(
        f"[TIME] tolerance band +/-{TOLERANCE:.0%}; not gated until a baseline "
        "is accepted",
        flush=True,
    )
    return False
