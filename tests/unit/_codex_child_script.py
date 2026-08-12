"""A fake Codex app-server child, for lifecycle tests over a real pipe.

Deliberately NOT a mock. The concurrency model under test uses a reader thread and
OS pipes; a mocked stream cannot deadlock, so it would verify the wrong property.

The replayed content comes from the committed fixtures T019 derived from Codex's
REAL generated schema (guarded by `test_codex_fixture_provenance.py`), so this
child cannot drift into emitting whatever the client happens to expect.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "codex_app_server"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture")
    parser.add_argument("--crash-after", type=int, default=None)
    parser.add_argument("--hang", action="store_true")
    parser.add_argument("--stderr", default=None)
    #: Keep stdout OPEN after the fixture is exhausted, the way a real app-server
    #: does. Without this the child reaches EOF on its own, which silently rescues
    #: a bridge that never stops reading after a terminal event -- the fixture ends
    #: the loop for it. A live server never would, so the turn would stall until
    #: `frames()` timed out.
    parser.add_argument("--stay-open", action="store_true")
    args = parser.parse_args()

    if args.stderr is not None:
        sys.stderr.write(args.stderr + "\n")
        sys.stderr.flush()

    if args.hang:
        time.sleep(60)
        return 0

    path = _FIXTURES / f"{args.fixture}.jsonl"
    written = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        written += 1
        if args.crash_after is not None and written >= args.crash_after:
            return 1
    if args.stay_open:
        time.sleep(60)  # outlive any test; the bridge must not wait for our EOF
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
