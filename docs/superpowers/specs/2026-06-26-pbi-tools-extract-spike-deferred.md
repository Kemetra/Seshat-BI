# pbi-tools extract spike — DEFERRED (2026-06-26)

> The third ranked forward bet from ADR-0013 / the autopilot final report
> ("Run the pbi-tools extract spike — confirm the extracted `model.tmdl` parses
> under `tmdl.py`"). Attempted on 2026-06-26; **deferred — no live target and no
> runnable tool on this machine.** This is the honest verdict, not a PASS: unlike
> the F038 BPA spike (Tabular Editor present, six gates run live), pbi-tools could
> not be executed here, so the make-or-break gate never ran.

## VERDICT: **DEFERRED** — premise has no target in this repo, and the tool cannot run on this machine.

## Why the spike does not retire its risk today

ADR-0013 frames pbi-tools as closing **the one path `retail check` can't handle:
an opaque binary `.pbix` instead of a committed PBIP `definition/` folder.** The
spike's job is to prove that `pbi-tools extract` turns that binary into TMDL
**fully headless**, and that the emitted `model.tmdl` **parses under
`src/seshat/tmdl.py`** (a format-drift smoke test). Two independent facts block that
proof here:

| Fact | Probe result (2026-06-26) | Consequence |
|------|---------------------------|-------------|
| **No binary `.pbix` in the repo** | `git`-tracked tree is already PBIP-source (committed `*.SemanticModel/definition/` TMDL). `**/*.pbix` → none. | The opaque-`.pbix` hole pbi-tools closes **does not exist in this repo today**. There is no live target to extract. |
| **`pbi-tools` not installed** | Not on PATH; `PBI_TOOLS_PATH` unset; absent from all common install locations. | Cannot run a live extract. |
| **Power BI Desktop not installed** | `PBIDesktop.exe` absent in both Program Files and the WindowsApps package path. | Cannot mint a `.pbix` from the committed model, and cannot satisfy a Desktop-dependent extract. |
| **No .NET SDK (runtime only)** | `dotnet --list-sdks` → empty; `--list-runtimes` → `Microsoft.NETCore.App 8.0.28` + `Microsoft.WindowsDesktop.App 8.0.28`. | `dotnet tool install pbi-tools` is not possible (needs an SDK). |
| **Self-contained build exists but cannot be auto-fetched** | `pbi-tools.core.1.2.0_win-x64.zip` is published (self-contained, would not need an SDK). | Downloading + executing an agent-chosen external binary was **blocked by the coding-agent sandbox** as untrusted-code integration — correctly. A live run requires an explicit operator install. |

## The format-drift test is NOT vacuously passable here

A tempting shortcut is to feed the **committed** `model.tmdl` back through
`parse_tmdl` and call it a parse-back proof. **That is circular and was rejected.**
The committed model already parses by construction — the entire D1–D11 rule suite
depends on it parsing. The risk the spike exists to retire is *format drift*:
pbi-tools may serialize TMDL differently (property order, quoting, optional
properties, line endings) from what Power BI Desktop committed. Feeding the
committed file back tests the parser against the format it was built for, so it
**structurally cannot detect drift** — drift is exactly the case where pbi-tools'
output ≠ the committed file. A non-circular parse-back requires a **genuinely
pbi-tools-emitted** `model.tmdl`, which requires actually running the tool.

What *was* confirmed (a real but partial result): `src/seshat/tmdl.py` parses the
committed `powerbi/Retailgold.SemanticModel/definition/` cleanly — 7 table files,
14 measures on `fct_sales`, and `model.tmdl` correctly returns `None` (a
header-only file) without raising. This establishes the parser handles the
*current* TMDL shape; it does **not** establish that it handles pbi-tools' emitted
shape. That gap is the deferred work.

## Why no runner / stub was shipped

Shipping an F038-shaped runner now would be a **hollow gate**: CI never has
pbi-tools installed, so a green CI run would only ever exercise the *skip* path,
while the surrounding evidence would read as a PASS for a tool that never once
performed its core function. That misrepresents state. Per the kit's honesty
discipline (hard rule #9, "no fake confidence"), a deferral is recorded instead of
a green-but-meaningless stub.

## Enable steps (to run the real spike on a future machine)

1. Install **pbi-tools** — either the self-contained `pbi-tools.core` build
   (no SDK/Desktop needed if it runs on the present .NET 8 runtime — itself worth
   confirming) or via an SDK + `dotnet tool install`. Set `PBI_TOOLS_PATH` to the
   executable, mirroring the F038 `TABULAR_EDITOR_PATH` pattern.
2. Obtain an **input `.pbix`** — saved from Power BI Desktop, or a small synthetic
   fixture. (The repo is PBIP-source-only by norm; a binary `.pbix` is **not**
   committed — it stays a local/scratch input.)
3. Run `pbi-tools extract <pbix> -extractFolder <scratch>` **headless** (bounded
   timeout; a hang ⇒ GUI/prompt ⇒ gate-1 failure). The `compile` command
   (PBIP→.pbix→Service) stays **FORBIDDEN** — it is F016's publish territory
   (ADR-0013's highest-severity MUST-NOT); the runner must never build that argv,
   and a test must assert it.
4. Feed the **tool-emitted** `model.tmdl` through `retail.tmdl.parse_tmdl` and
   diff structure against the committed model — the **non-circular** format-drift
   smoke test. Only this proves the integration seam.

## Authority boundary (unchanged)

If adopted later, pbi-tools `extract` is a **pre-processor / advisory engine** — it
produces the TMDL D1–D11 then read; it writes derived `evidence[]`, never a stage
`pass`, never publishes. `compile` is walled off (F016). No new `retail check`
rule, no new readiness stage, no core dependency (`dependencies = []` holds).

## Disposition

- **pbi-tools pilot:** parked as **"no live target — revisit when a `.pbix`
  workflow or an installed toolchain appears."** ADR-0013's PILOT verdict stands;
  only the *spike execution* is deferred.
- **Next ranked item taken instead:** **#4 — the L4 value proxy** (`retail
  value-check`, lazy `psycopg2`, stdlib-only core), which *is* buildable and
  testable on this machine. See its own design doc + spec.
