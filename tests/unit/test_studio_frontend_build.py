"""The built frontend must load nothing remote and ship inside the wheel.

FR-033: "Studio MUST load no remote fonts, scripts, images, analytics, or other browser
assets." FR-005: the frontend ships PREBUILT in the wheel; end users need no Node.

These tests read the BUILT output, so they only run where `studio-ui/dist` exists --
CI builds it, and a developer who has not run `npm run build` gets a skip rather than a
false failure.

**Why not just grep for `https://`.** The bundle legitimately contains inert URL
STRINGS: the SVG namespace (`http://www.w3.org/2000/svg`) and React's own error-message
link (`https://react.dev/...`). Neither is ever fetched. A substring test would fail on
both while still missing a genuine remote load written as a protocol-relative `//cdn/…`.
So these assert on the LOADING mechanisms -- `src`/`href` attributes, CSS `@import` and
`url()` -- which is what the browser actually acts on.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DIST = _REPO_ROOT / "studio-ui/dist"
_PACKAGED = _REPO_ROOT / "src/seshat/studio/static"

#: Anything the browser would resolve off-origin: an absolute scheme, or the
#: protocol-relative `//host/path` form a naive scheme check misses entirely.
_REMOTE_TARGET = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:)?//")


def _built() -> Path:
    if not (_DIST / "index.html").is_file():
        pytest.skip("studio-ui/dist is not built; run `npm run build` in studio-ui")
    return _DIST


def _attribute_targets(html: str) -> list[str]:
    return re.findall(r'(?:src|href)="([^"]+)"', html)


def test_the_entry_html_loads_only_relative_assets() -> None:
    html = (_built() / "index.html").read_text(encoding="utf-8")

    targets = _attribute_targets(html)
    assert targets, "the built index.html references no assets at all"

    remote = [target for target in targets if _REMOTE_TARGET.match(target)]
    assert not remote, f"FR-033: the entry HTML loads remote assets: {remote}"


def test_the_entry_html_declares_no_remote_font_or_stylesheet_import() -> None:
    html = (_built() / "index.html").read_text(encoding="utf-8")

    assert "fonts.googleapis" not in html
    assert "fonts.gstatic" not in html
    assert "@import" not in html


def test_the_built_css_imports_and_urls_are_all_local() -> None:
    """A webfont or CDN background would arrive through `@import` or `url()`."""
    for stylesheet in _built().rglob("*.css"):
        text = stylesheet.read_text(encoding="utf-8")

        for target in re.findall(r"url\(\s*['\"]?([^'\")]+)", text):
            assert not _REMOTE_TARGET.match(target), (
                f"FR-033: {stylesheet.name} loads a remote asset: {target}"
            )
        for target in re.findall(r"@import\s+(?:url\()?['\"]([^'\"]+)", text):
            assert not _REMOTE_TARGET.match(target), (
                f"FR-033: {stylesheet.name} imports remotely: {target}"
            )


def test_the_bundle_declares_no_analytics_or_tag_manager() -> None:
    """Named explicitly by FR-033, and easy to add by accident with a dependency."""
    for asset in _built().rglob("*.js"):
        text = asset.read_text(encoding="utf-8", errors="ignore").lower()

        for tracker in (
            "googletagmanager",
            "google-analytics",
            "gtag(",
            "segment.com",
            "sentry.io",
            "hotjar",
            "mixpanel",
        ):
            assert tracker not in text, (
                f"FR-033: {asset.name} references analytics: {tracker}"
            )


def test_the_build_output_carries_no_source_map() -> None:
    """A source map would ship the whole frontend source inside the wheel."""
    maps = list(_built().rglob("*.map"))

    assert not maps, f"source maps must not ship: {[m.name for m in maps]}"


def test_asset_urls_are_relative_so_any_loopback_port_works() -> None:
    """The port is OS-assigned, so an absolute `/assets/...` root path is fine but a
    hardcoded origin is not -- and a relative path survives being served from a
    subpath too."""
    html = (_built() / "index.html").read_text(encoding="utf-8")

    for target in _attribute_targets(html):
        assert target.startswith("./") or target.startswith("/"), (
            f"asset reference is neither relative nor root-absolute: {target}"
        )


# --------------------------------------------------------------------------- #
# FR-005 -- the built output lands where the wheel ships it                    #
# --------------------------------------------------------------------------- #


def test_the_packaged_static_directory_is_inside_the_wheel_package() -> None:
    """No force-include: the path sits inside `packages = ["src/seshat"]`.

    A force-include pointing at a not-yet-built directory made metadata generation fail
    for EVERY install, so the asset path deliberately lives inside an already-declared
    package instead.
    """
    from seshat.studio import assets

    assert assets.packaged_static_directory() == _PACKAGED


def test_the_documented_build_command_exists() -> None:
    """`npm run build` must be real, and must typecheck before bundling."""
    import json

    scripts = json.loads(
        (_REPO_ROOT / "studio-ui/package.json").read_text(encoding="utf-8")
    )["scripts"]

    assert "build" in scripts
    assert "tsc" in scripts["build"], (
        "the build must typecheck; a bundler alone will happily ship broken types"
    )
