# T033 — SC-008 install acceptance

**Measured 2026-08-14** against `main` at `84357775` (the merge of #642, which closed
issue #641). Python **3.13.14** — the same minor CI pins.

SC-008: *"The installed wheel opens Studio with Python and a browser only; no Node
executable or remote browser asset is required at runtime."*

T033 says "Build **sdist/wheel** and test clean base and Studio-extra installs", so the
matrix is run twice — once per artifact. Running only the wheel would have asserted
exactly the half that already worked: the sdist is the path #641 had broken.

## Artifacts

`python -m build` from a clean tree produced both, each carrying three
`seshat/studio/static` members (`index.html`, `index-C5rU9Cr2.js`,
`index-wG-qF5IE.css`):

> The asset filenames are content hashes, recorded as measured on 2026-08-14. Any edit to
> the frontend or its tokens changes them by design — T032 did exactly that shortly after.
> Nothing pins these literals; the counts, sizes, and status codes are the claim.

| Artifact | Size | Frontend members |
|---|---|---|
| `seshat_bi-1.0.0-py3-none-any.whl` | 1,568,861 B | 3 |
| `seshat_bi-1.0.0.tar.gz` | 1,290,167 B | 3 |

## Method — the real process, not a test client

Each leg installs into a **fresh venv** and launches the actual `seshat-studio`
console script as a subprocess. Not `TestClient`, and not `--no-serve`:

- #608 is the precedent — `TestClient` derived its `base_url` from the app's own state,
  so 34 tests passed while every real request 403'd.
- `--no-serve` stops before binding a port by design, so it can never show that a UI
  is *served*.

Studio assigns its port via port 0 (FR-003) and its Host guard compares against the
port actually bound, so the port and the single-use bootstrap token are parsed from the
launcher's own stderr banner rather than guessed. The probe then does what a browser
does: `POST /api/v1/bootstrap?token=…` to mint the session cookie, then requests every
asset the served HTML references.

**Node was removed from `PATH` for every launch** (`which node` → "no node in …"). The
development box has Node v24.14.0 installed, so without stripping it the "no Node
runtime" clause would have been untested.

## Results — 4/4 legs pass

| Leg | Artifact | Install | Outcome |
|---|---|---|---|
| 1 | wheel | base (no extra) | **exit 2**, named diagnostic |
| 2 | wheel | `[studio]` | **UI served** |
| 3 | sdist | base (no extra) | **exit 2**, named diagnostic |
| 4 | sdist | `[studio]` | **UI served** |

### Clean base (legs 1, 3) — FR-006

Proven clean *before* launching: `import fastapi` / `uvicorn` / `starlette` all raise
`ModuleNotFoundError` in the base venvs. Without that, a stray transitive dependency
could make the diagnostic path unreachable and the leg would prove nothing.

Both legs exit **2** — a refusal, not a crash — with stderr naming the extra, the
missing module, and both install lanes, and **no traceback**:

```
Seshat Studio needs the optional `studio` extra, which is not installed (missing: fastapi).
The base seshat-bi install stays free of Studio web dependencies by design; enable the extra with one of:
       pipx install:  pipx inject seshat-bi --force "fastapi>=0.115" "uvicorn>=0.34"
       pip install:   pip install "seshat-bi[studio]"
```

This is a genuinely different test from the existing unit test, which monkeypatches
`__import__`: here the extra is really absent from a real install.

### Studio extra (legs 2, 4) — FR-005 / SC-008

Byte-identical results from both artifacts:

The **200 responses are the proof** that a server bound and served; the stderr banner is
only how the port and token were discovered. (The banner is printed before the
`--no-serve` branch returns, so a banner alone would not establish a listening socket —
these legs pass no `--no-serve`, and the 200s settle it regardless.)

| Probe | Leg 2 (wheel) | Leg 4 (sdist) |
|---|---|---|
| banner parsed (port/token discovery) | yes | yes |
| process alive at probe time | yes | yes |
| `GET /` | **200** `text/html`, 678 B | **200** `text/html`, 678 B |
| `POST /api/v1/bootstrap` | **204**, cookie set | **204**, cookie set |
| `index-C5rU9Cr2.js` | **200**, 211,678 B, `text/javascript` | **200**, 211,678 B |
| `index-wG-qF5IE.css` | **200**, 6,940 B, `text/css` | **200**, 6,940 B |
| non-loopback requests | **0** | **0** |

## No remote asset fetch — resolved, not just grepped

Every asset the shell references was **served 200 from loopback**, which is the
substantive proof: an asset answered by `127.0.0.1` is not coming from a CDN. Zero
requests left the local server.

A textual scan of the whole 219,285-byte corpus (shell + both assets) reports two
hosts, and **neither is a runtime fetch** — recorded here rather than filtered
silently, because "the scan found nothing" would be a weaker and less honest claim:

- `www.w3.org` — XML namespace URIs passed to `createElementNS("http://www.w3.org/2000/svg", …)`.
  DOM *identifiers*, never dereferenced; present in any React build that renders SVG.
- `react.dev` — React's minified-error helper builds `"https://react.dev/errors/" + code`
  for a console message when an invariant fires. A string concatenation, not a request.

This is why both checks are run: the textual scan alone would **false-positive** on
SC-008, and asset resolution alone would miss a genuinely remote reference.

## Falsified, not assumed

An absence-assertion that has never fired proves nothing (the T034 precedent). Deleting
the installed `static/` directory and relaunching yields:

```
EXIT=2
Studio frontend assets are missing: <redacted-path> does not exist. This wheel was built
without the frontend build step. Rebuild with the documented Studio build command, or
reinstall a wheel that includes the prebuilt assets.
```

So a UI-less install is a **named refusal**, never a blank page — and this is precisely
what the pre-#641 sdist install would have produced. The green legs above are therefore
load-bearing. Note the path is redacted in that message, which is FR-026 holding on the
failure path too.

## Scope not covered

SC-008 names "Python and a browser only". This exercises the **server** end-to-end and
proves every byte the browser needs is served locally — it does not drive a real browser
and render the page. Browser acceptance over the running app is **T036** (owner-gated,
needs a signed-in Codex CLI), and T032's note already draws the same boundary for the
jsdom audit. No claim is made here about rendered visual behaviour.
