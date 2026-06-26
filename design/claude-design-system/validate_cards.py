#!/usr/bin/env python3
"""Render-check validator for the Seshat BI Claude Design System preview cards.

Asserts the DesignSync render-check invariants so a card fails until it is
correct (RED), then passes (GREEN). stdlib only. ASCII output only.
"""
import re
import sys
from pathlib import Path

MARKER = re.compile(
    r'<!--\s*@dsCard\s+group="[^"]+"\s+name="[^"]+"\s+'
    r'subtitle="[^"]+"\s+viewport="\d+x\d+"\s*-->'
)
# Off-host http(s) reference. The inline-SVG namespace http://www.w3.org/2000/svg
# is NOT a network fetch (inline SVG in HTML needs no xmlns at all, but if one is
# present it must not trip the gate), so exempt it explicitly.
OFFHOST = re.compile(r'https?://(?!www\.w3\.org/)', re.I)
# CSS may only reference project-relative siblings; a remote @import is the CSP trap.
CSS_OFFHOST = re.compile(r'@import\s+url\(\s*[\'"]?https?://', re.I)
FORBIDDEN_DATA = re.compile(r'\bC086\b|pharmacy', re.I)


def check_card(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    head = "\n".join(text.splitlines()[:2])
    if not MARKER.search(head):
        issues.append("missing/invalid @dsCard marker (need group/name/subtitle/viewport on line 1-2)")
    if OFFHOST.search(text):
        issues.append("off-host reference (http/https) -- CSP forbids external hosts")
    if FORBIDDEN_DATA.search(text):
        issues.append("contains real-data token (C086/pharmacy) -- cards must be data-free")
    # thin: a card with almost no body content is flagged
    body = text.split("<body>", 1)[-1]
    if len(re.sub(r"<[^>]+>|\s", "", body)) < 40:
        issues.append("thin card -- body has < 40 chars of visible content")
    if path.name == "brand-seven-star.html" and 'data-points="7"' not in text:
        issues.append('seven-point star card must carry data-points="7" (visual-identity sec 3.1)')
    return issues


def check_css(path: Path) -> list[str]:
    """CSS files: only the remote-@import CSP trap is checked (no marker/thin rules)."""
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    if CSS_OFFHOST.search(text) or OFFHOST.search(text):
        issues.append("CSS references an external host (remote @import / url) -- CSP forbids it")
    return issues


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).parent / "preview"
    cards = sorted(root.glob("*.html"))
    # CSS the bundle depends on: the shared card CSS (in preview/) and the tokens
    # file (in the parent dir) -- both are where the CSP @import trap would land.
    css_files = sorted(root.glob("*.css")) + sorted(root.parent.glob("colors_and_type.css"))
    if not cards:
        print(f"[FAIL] no cards found in {root}")
        return 1
    total_issues = 0
    for c in cards:
        for issue in check_card(c):
            print(f"[FAIL] {c.name}: {issue}")
            total_issues += 1
    for f in css_files:
        for issue in check_css(f):
            print(f"[FAIL] {f.name}: {issue}")
            total_issues += 1
    if total_issues:
        print(f"[FAIL] {total_issues} issues across {len(cards)} cards + {len(css_files)} css")
        return 1
    print(f"[OK] {len(cards)} cards, {len(css_files)} css clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
