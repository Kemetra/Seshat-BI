"""Bootstrap token exchange, session state, and Host/Origin enforcement.

Source of truth:
``specs/139-seshat-studio-foundation/contracts/security-boundary.md``.

The token is high-entropy, stored only as a digest, compared in constant time, and
invalidated after exactly one successful exchange. The raw token and the cookie
value never enter logs, agent context, events, errors, or durable files -- which is
why :class:`SessionStore` keeps no plaintext attribute and overrides ``__repr__``.

Standard library only, by contract: importable without the ``studio`` extra.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

#: 32 bytes = 256 bits, the contract's floor. `token_urlsafe` renders this as 43
#: characters, so the length assertion in the tests tracks the entropy requirement.
_TOKEN_BYTES = 32

#: Exact cookie name from the contract.
SESSION_COOKIE_NAME = "seshat_studio_session"


def generate_bootstrap_token() -> str:
    """A cryptographically secure one-time bootstrap token (at least 256 bits)."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def session_cookie_attributes() -> dict[str, Any]:
    """The cookie flags the contract requires.

    ``Secure`` is omitted -- not forgotten -- because the loopback origin is HTTP.
    Exact ``Host`` enforcement is what prevents that from widening the boundary, so
    the two decisions are load-bearing together.

    ``Domain`` is absent by construction: setting it would widen the cookie to
    sibling hosts, and a host-only cookie is strictly narrower.
    """
    return {
        "httponly": True,
        "samesite": "strict",
        "path": "/",
        "secure": False,
    }


class SessionStore:
    """One process's bootstrap token and its issued session.

    Holds digests only. A failed exchange never consumes the real token, so a wrong
    guess cannot deny the legitimate browser its one exchange.
    """

    __slots__ = ("_token_digest", "_session_digest")

    def __init__(self, bootstrap_token: str) -> None:
        self._token_digest: str | None = _digest(bootstrap_token)
        self._session_digest: str | None = None

    def __repr__(self) -> str:  # pragma: no cover - exercised via the redaction test
        """Deliberately opaque: no token or cookie material, even in a traceback."""
        token_state = "unused" if self._token_digest else "exchanged"
        session_state = "set" if self._session_digest else "none"
        return f"<SessionStore token={token_state} session={session_state}>"

    def exchange(self, presented_token: str) -> str | None:
        """Trade a valid bootstrap token for a session cookie value, once.

        Returns the cookie value, or ``None`` if the token is wrong or already used.
        Comparison is constant time: a short-circuiting ``==`` would leak how much
        of a guess was correct.
        """
        if self._token_digest is None:
            return None
        if not hmac.compare_digest(_digest(presented_token), self._token_digest):
            return None

        self._token_digest = None  # one exchange only
        cookie_value = secrets.token_urlsafe(_TOKEN_BYTES)
        self._session_digest = _digest(cookie_value)
        return cookie_value

    def is_valid_session(self, presented_cookie: str) -> bool:
        """Constant-time check of a presented session cookie."""
        if self._session_digest is None:
            return False
        return hmac.compare_digest(_digest(presented_cookie), self._session_digest)

    def shutdown(self) -> None:
        """Invalidate the token and the session; access ends immediately."""
        self._token_digest = None
        self._session_digest = None


def host_is_allowed(header: str, expected_host: str, expected_port: int) -> bool:
    """Exact ``Host`` match against the selected loopback host and port.

    A DNS-rebinding guard. Only ``<host>:<port>`` is accepted -- not a bare host, not
    ``localhost`` (which can resolve elsewhere), and not a suffix like
    ``127.0.0.1:8931.evil.com``, which a substring or prefix test would admit.
    """
    return header == f"{expected_host}:{expected_port}"


def origin_is_allowed(header: str, expected_host: str, expected_port: int) -> bool:
    """Exact ``Origin`` match against the Studio origin.

    CORS is never enabled, so there is no scheme or host to negotiate: the only
    acceptable origin is Studio's own. A missing or ``null`` origin is refused --
    mutating requests must prove same-origin, and absence is not proof.
    """
    return header == f"http://{expected_host}:{expected_port}"
