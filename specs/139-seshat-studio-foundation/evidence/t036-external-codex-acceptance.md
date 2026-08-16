# T036 external Codex acceptance

**Captured:** 2026-08-16
**Result:** PASS -- T036 closed

## Runtime

- OS: Windows 11 build 22631 (`Microsoft Windows NT 10.0.22631.0`)
- Python: 3.13.12
- Seshat BI: 1.1.0 source checkout
- Studio UI assets: `index-CKJk5uPb.js`, `index-DvDek9hM.css`
- Codex CLI: 0.147.0
- Repository commit before recording this evidence: `121e60d2`
- Authentication: Codex-managed ChatGPT account; signed in
- `OPENAI_API_KEY` supplied to Studio: no

No account identifier, token, credential path, raw provider frame, model response,
bootstrap token, rate-limit value, screenshot, or browser profile was retained.

## Live provider acceptance

The final acceptance run used the production Studio bridge and loopback HTTP/SSE
surface with the installed Codex app-server. It demonstrated:

1. Studio reported `healthy` before and after the real provider turns by probing the
   stable `account/read` method at startup.
2. A read-only turn completed with ordered events:
   `thread_started`, `turn_started`, `thread_started`, `agent_message`,
   `turn_completed`.
3. A second real turn emitted `item/commandExecution/requestApproval`. Studio exposed
   the technical approval, accepted one `deny` decision, translated it to provider
   decision `decline`, and the turn reached a terminal event.
4. The denied marker change was absent and the tracked workspace digest was unchanged.
5. The child process inherited no `OPENAI_API_KEY`; authentication remained the
   Codex-managed ChatGPT subscription path.

The focused installed-provider integration also passed both real-provider tests: the
app-server handshake correlated and a read-only turn reached exactly one successful
terminal event (`2 passed in 28.69s`).

## Running-browser acceptance

Installed Microsoft Edge rendered the running loopback app. A local Playwright/axe
acceptance pass over that rendered page reported:

- `browser_render=pass`
- `axe_serious_critical=0`
- `focus_ring_visible=true`
- `mobile_responsive=true` at a 390 x 844 viewport
- `reduced_motion=true`

The browser profile and screenshot were temporary and were removed with the harness.
The test loaded the repository's installed local `axe-core` script with CSP bypassed
only in the test browser context; the production server policy was not changed.

## Defects found and corrected

The first acceptance attempt found two production contract mismatches:

- startup checked only `codex --version` and hard-coded signed-out health; Studio now
  performs a redacted `account/read` probe and retains only the signed-in boolean;
- `approvalPolicy: on-request` did not surface the required request on Codex 0.147.0.
  The stable `untrusted` policy did, while the granular policy required an experimental
  capability forbidden by the Foundation contract.

Generated Codex 0.147.0 schemas also confirmed that the stable provider response values
are `accept` and `decline`; Studio's translation now uses those values. Focused tests
were written to fail for each mismatch before the implementation changed.

## Closure

T036's signed-in health, ordered real turn, real approval-denial round trip, no-change
proof, browser render, and subscription-without-API-key boundaries all pass. Ahmed
Shaaban subsequently supplied the separate named-human approval for T037 and accepted
the scoped redaction ruling recorded under T034 on 2026-08-16.
