"""Small request helpers shared by the Studio route modules.

One definition each, so the route modules cannot drift apart. Deliberately free of any
`app` import: `app` imports the route modules, so a helper living there could not be
reached from them without a cycle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    """The current UTC time in the second-precision form every Studio record uses."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def json_body(request: Any) -> dict[str, Any]:
    """The request body as a mapping; a non-mapping becomes an empty one.

    Returning {} rather than raising lets each route's own field checks produce the
    contracted 422 with a useful message instead of a framework-shaped error.
    """
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}
