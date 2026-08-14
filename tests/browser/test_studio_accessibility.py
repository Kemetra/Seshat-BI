"""Real-browser accessibility acceptance for Studio (T032, SC-007).

These tests launch the actual loopback server and the packaged frontend in a Chromium
rendering engine.  Component tests remain useful, but jsdom cannot evaluate media
queries, paint focus rings, calculate browser contrast, or expose layout overflow.
"""

from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.unit._studio_workspace_fixtures import (
    write_blocked_table,
    write_empty_workspace,
    write_ready_table,
)

#: CI selects tests by MARKER (`pytest -m unit` and `pytest -m "integration and not
#: live_db and not statistics"` in ci.yml), so an unmarked file is deselected by every
#: lane -- green because it never ran, not because it passed. `test_studio_package_
#: contract.py` records the same defect reaching main on #641. The `browser`-extra
#: skip below is the separate, intentional opt-in gate.
pytestmark = pytest.mark.integration

playwright = pytest.importorskip(
    "playwright.sync_api", reason="requires the `browser` extra"
)

ROOT = Path(__file__).resolve().parents[2]
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
AXE = ROOT / "studio-ui" / "node_modules" / "axe-core" / "axe.min.js"
LAUNCH_URL = re.compile(r"http://127\.0\.0\.1:\d+/\?token=[A-Za-z0-9_-]+")


@contextmanager
def _running_studio(workspace: Path) -> Iterator[str]:
    """Start the real launcher and yield its one-time browser URL."""

    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)
    environment.pop("CODEX_API_KEY", None)
    process = subprocess.Popen(  # noqa: S603 - fixed interpreter/module argv
        [
            sys.executable,
            "-m",
            "seshat.studio",
            "--repo",
            str(workspace),
            "--agent",
            "fake",
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    lines: queue.Queue[str] = queue.Queue()

    def _read_stderr() -> None:
        assert process.stderr is not None
        for line in process.stderr:
            lines.put(line)

    threading.Thread(target=_read_stderr, daemon=True).start()
    observed: list[str] = []
    try:
        for _ in range(100):
            try:
                line = lines.get(timeout=0.1)
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            observed.append(line)
            match = LAUNCH_URL.search(line)
            if match is not None:
                yield match.group(0)
                return
        pytest.fail(
            "Studio did not emit a launch URL: "
            + "".join(observed)[-1000:].replace(str(workspace), "<workspace>")
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _open(page, url: str) -> None:  # type: ignore[no-untyped-def]
    """Navigate without sleeping; retry only while the bound server starts accepting."""

    last_error: Exception | None = None
    for _ in range(50):
        try:
            page.goto(url, wait_until="networkidle", timeout=1_000)
            page.get_by_role("heading", level=1).wait_for(timeout=1_000)
            return
        except playwright.Error as error:
            last_error = error
    raise AssertionError("Studio never became reachable") from last_error


def _serious_axe_violations(
    page,
) -> list[dict[str, object]]:  # type: ignore[no-untyped-def]
    """Run axe after paint and return only SC-007's release-blocking impacts."""

    assert AXE.is_file(), "run the canonical frontend build before browser acceptance"
    # Studio's CSP correctly rejects an inline ``<script>`` tag. Playwright's
    # evaluation world is the test boundary: it can load axe without weakening the
    # response policy the browser is also exercising.
    page.evaluate(AXE.read_text(encoding="utf-8"))
    result = page.evaluate(
        """async () => await axe.run(document, {
            runOnly: {
                type: "tag",
                values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
            },
        })"""
    )
    return [
        violation
        for violation in result["violations"]
        if violation.get("impact") in {"critical", "serious"}
    ]


def _format_violations(violations: list[dict[str, object]]) -> str:
    return "; ".join(
        f"{violation.get('impact')} {violation.get('id')}: "
        f"{len(violation.get('nodes', []))} node(s)"
        for violation in violations
    )


def test_running_command_room_draws_visible_keyboard_focus(tmp_path: Path) -> None:
    """A removed/transparent `:focus-visible` outline must fail in a painted browser."""

    write_blocked_table(tmp_path)
    assert EDGE.is_file(), "the Windows release gate requires an installed Edge browser"

    with _running_studio(tmp_path) as url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(EDGE), headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            _open(page, url)
            page.keyboard.press("Tab")
            focus = page.evaluate(
                """() => {
                    const element = document.activeElement;
                    const style = element ? getComputedStyle(element) : null;
                    return style ? {
                        tag: element.tagName,
                        width: parseFloat(style.outlineWidth),
                        style: style.outlineStyle,
                        color: style.outlineColor,
                    } : null;
                }"""
            )
        finally:
            browser.close()

    assert focus is not None
    assert focus["tag"] in {"BUTTON", "SUMMARY", "TEXTAREA"}
    assert focus["style"] not in {"none", "hidden"}
    assert focus["width"] >= 2
    assert focus["color"] not in {"transparent", "rgba(0, 0, 0, 0)"}


@pytest.mark.parametrize(
    ("build_workspace", "expected_heading"),
    [
        (write_ready_table, "Tables"),
        (write_empty_workspace, "No tables are onboarded yet"),
        (write_blocked_table, "Tables"),
    ],
    ids=("command-room", "empty", "blocked"),
)
def test_running_critical_states_have_no_serious_axe_violations(
    tmp_path: Path, build_workspace, expected_heading: str
) -> None:  # type: ignore[no-untyped-def]
    """Removing a name, landmark, contrast pair, or semantic role must fail here."""

    build_workspace(tmp_path)
    assert EDGE.is_file(), "the Windows release gate requires an installed Edge browser"

    with _running_studio(tmp_path) as url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(EDGE), headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            remote_requests: list[str] = []
            page.on(
                "request",
                lambda request: (
                    remote_requests.append(request.url)
                    if not request.url.startswith("http://127.0.0.1:")
                    else None
                ),
            )
            _open(page, url)
            page.get_by_role("heading", name=expected_heading).wait_for()
            violations = _serious_axe_violations(page)
        finally:
            browser.close()

    assert not violations, _format_violations(violations)
    assert not remote_requests, (
        f"browser requested non-loopback assets: {remote_requests}"
    )


def test_running_approval_state_has_no_serious_axe_violations(tmp_path: Path) -> None:
    """The distinct live-approval DOM must pass axe, not only the quiet composer."""

    write_blocked_table(tmp_path)
    assert EDGE.is_file(), "the Windows release gate requires an installed Edge browser"

    with _running_studio(tmp_path) as url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(EDGE), headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            _open(page, url)
            with page.expect_response(
                lambda response: (
                    response.url.endswith("/api/v1/agent/threads")
                    and response.request.method == "POST"
                )
            ) as created:
                page.get_by_role("button", name="Ask about this workspace").click()
            thread_id = created.value.json()["thread_id"]
            response = page.evaluate(
                """async (threadId) => {
                    const workspace = await fetch("/api/v1/workspace")
                        .then(r => r.json());
                    const started = await fetch(
                        `/api/v1/agent/threads/${encodeURIComponent(threadId)}/turns`,
                        {
                            method: "POST",
                            headers: {"Content-Type": "application/json"},
                            body: JSON.stringify({
                                prompt: "Please update the mapping declaration",
                                snapshot_revision: workspace.identity.revision,
                                requested_mode: "propose_changes",
                            }),
                        },
                    );
                    return {status: started.status, body: await started.json()};
                }""",
                thread_id,
            )
            assert response["status"] == 202, response
            page.get_by_text("Apply the proposed mapping change?").wait_for(
                timeout=15_000
            )
            violations = _serious_axe_violations(page)
        finally:
            browser.close()

    assert not violations, _format_violations(violations)


def test_reduced_motion_media_query_disables_page_motion(tmp_path: Path) -> None:
    """Deleting the real media query must leave measurable non-zero motion here."""

    write_blocked_table(tmp_path)
    assert EDGE.is_file(), "the Windows release gate requires an installed Edge browser"

    with _running_studio(tmp_path) as url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(EDGE), headless=True)
        try:
            page = browser.new_page(
                viewport={"width": 1280, "height": 800}, reduced_motion="reduce"
            )
            _open(page, url)
            motion = page.evaluate(
                """() => {
                    const probe = document.createElement("div");
                    probe.style.animation = "spin 2s linear infinite";
                    probe.style.transition = "opacity 2s linear";
                    document.body.append(probe);
                    const style = getComputedStyle(probe);
                    return {
                        media: matchMedia("(prefers-reduced-motion: reduce)").matches,
                        animationDuration: style.animationDuration,
                        animationIterations: style.animationIterationCount,
                        transitionDuration: style.transitionDuration,
                    };
                }"""
            )
        finally:
            browser.close()

    assert motion["media"] is True
    assert float(motion["animationDuration"].removesuffix("s")) <= 0.00001
    assert motion["animationIterations"] == "1"
    assert float(motion["transitionDuration"].removesuffix("s")) <= 0.00001


@pytest.mark.parametrize(("width", "height"), [(320, 568), (768, 1024), (1440, 900)])
def test_running_command_room_has_no_horizontal_viewport_overflow(
    tmp_path: Path, width: int, height: int
) -> None:
    """Fixed-width content or an unwrapped technical value must fail a real layout."""

    write_blocked_table(tmp_path)
    assert EDGE.is_file(), "the Windows release gate requires an installed Edge browser"

    with _running_studio(tmp_path) as url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(EDGE), headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            _open(page, url)
            layout = page.evaluate(
                """() => ({
                    viewport: window.innerWidth,
                    document: document.documentElement.scrollWidth,
                    main: document.querySelector("main")?.getBoundingClientRect().width,
                    offenders: [...document.querySelectorAll("*")]
                        .map(element => {
                            const rect = element.getBoundingClientRect();
                            const style = getComputedStyle(element);
                            return {
                                tag: element.tagName,
                                className: typeof element.className === "string"
                                    ? element.className : "",
                                text: element.textContent?.trim().slice(0, 80),
                                left: rect.left,
                                width: rect.width,
                                right: rect.right,
                                clientWidth: element.clientWidth,
                                scrollWidth: element.scrollWidth,
                                minWidth: style.minWidth,
                                overflowX: style.overflowX,
                                whiteSpace: style.whiteSpace,
                            };
                        })
                        .filter(item =>
                            item.right > window.innerWidth + 1
                            || item.left < -1
                            || item.width > window.innerWidth + 1
                            || item.scrollWidth > item.clientWidth + 1
                        )
                        .slice(0, 20),
                })"""
            )
        finally:
            browser.close()

    assert layout["document"] <= layout["viewport"], layout["offenders"]
    assert layout["main"] <= layout["viewport"]
