"""The live resolvers' HTTP boundary, tested without touching the network.

Only https is fetched, redirects may not leave https or the original host, the
opener carries no file/ftp/data handler, a response body is size-capped, and an
upstream tag is escaped (and validated) before it is put into an API path.
"""

from __future__ import annotations

import io
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from seshat.integrations import resolvers
from tests.unit._curated_stack_fixtures import FakeGitHub, _github_component

pytestmark = pytest.mark.unit


def _redirect(old: str, new: str):
    handler = resolvers._HttpsSameHostRedirect()
    return handler.redirect_request(Request(old), io.BytesIO(), 302, "Found", {}, new)


def test_a_redirect_to_plain_http_is_refused() -> None:
    with pytest.raises(HTTPError):
        _redirect("https://pypi.org/pypi/x/json", "http://pypi.org/pypi/x/json")


def test_a_redirect_to_another_host_is_refused() -> None:
    with pytest.raises(HTTPError):
        _redirect("https://api.github.com/repos/a/b", "https://evil.example/x")


def test_a_same_host_https_redirect_is_followed() -> None:
    followed = _redirect(
        "https://api.github.com/repos/a/b", "https://api.github.com/repos/a/c"
    )
    assert followed is not None
    assert followed.full_url == "https://api.github.com/repos/a/c"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x/y", "data:,x"])
def test_the_opener_has_no_non_https_handlers(url: str) -> None:
    with pytest.raises(URLError):
        resolvers._OPENER.open(Request(url), timeout=1)


def test_a_non_https_url_is_refused_before_any_request(monkeypatch) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("urlopen was reached for a non-https URL")

    monkeypatch.setattr(resolvers, "urlopen", _boom)
    with pytest.raises(ValueError, match="non-https"):
        resolvers._get_json("http://pypi.org/pypi/x/json")


def test_an_oversized_response_is_refused(monkeypatch) -> None:
    class _Huge:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, size: int = -1) -> bytes:
            assert size > 0, "the body must be read with a cap"
            return b" " * size

    monkeypatch.setattr(resolvers, "urlopen", lambda *a, **k: _Huge())
    with pytest.raises(ValueError, match="exceeds"):
        resolvers._get_json("https://pypi.org/pypi/x/json")


def test_commit_lookup_escapes_the_ref(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(resolvers, "_get_json", lambda url: seen.append(url) or {})

    resolvers.LiveGitHub().commit_for_ref("a/b", "v1#x?y")

    assert seen == ["https://api.github.com/repos/a/b/commits/v1%23x%3Fy"]


@pytest.mark.parametrize("tag", ["v1#x", "-v1", "v1..2", "v 1"])
def test_an_unsafe_release_tag_is_refused(tag: str) -> None:
    index = FakeGitHub(release={"tag_name": tag}, commits={tag: {"sha": "a" * 40}})

    result = resolvers.resolve_github(_github_component(), index)

    assert not result.ok
    assert result.status == resolvers.FAILED
    assert not any(call.startswith("commit:") for call in index.calls)


def test_the_opener_honours_an_environment_https_proxy(monkeypatch) -> None:
    """A corporate proxy keeps working: https is tunnelled through it."""
    from urllib.request import ProxyHandler

    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:3128")
    monkeypatch.setenv("https_proxy", "http://proxy.example:3128")
    opener = resolvers._build_opener()

    proxies = [h for h in opener.handlers if isinstance(h, ProxyHandler)]
    assert proxies and proxies[0].proxies.get("https") == "http://proxy.example:3128"
