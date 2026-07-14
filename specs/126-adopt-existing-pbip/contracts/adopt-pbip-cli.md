# CLI Contract: `seshat adopt-pbip`

## Assess

```console
seshat adopt-pbip assess --project PATH [--format text|json]
```

- `--project` is required and identifies one PBIP directory or a `.pbix` file for
  boundary guidance.
- `--format` defaults to `text`; `json` conforms to
  `pbip-adoption-assessment.schema.json`.
- Reads local files and Git metadata only. It writes no file, opens no Desktop,
  database, service, network, or Power BI execution adapter.
- Text and JSON are rendered from the same normalized assessment.
- Successful, blocked, and supported-stop assessments all return the facts and
  exactly one `next_step`.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Assessment completed and returned an unblocked next action |
| `1` | Assessment completed with a governed blocker or terminal supported stop |
| `2` | Invalid/unsafe input prevented a trustworthy assessment |

## Scaffold

```console
seshat adopt-pbip scaffold --project PATH \
  --accept-assessment SHA256 [--format text|json]
```

- Recomputes the assessment and accepts only its exact current digest.
- Requires an existing Git worktree. It never invokes `git init`.
- The accepted assessment must declare exactly
  `.seshat/adoption/pbip-adoption.yaml` as a new write.
- Preflight resolves every path beneath the selected root and refuses linked
  escapes, dirty accepted inputs, an existing target, or a changed digest.
- It stages the complete UTF-8/LF manifest, publishes only to an absent target,
  cleans handled failures, and never opens an existing PBIP/TMDL/PBIR/DAX/SQL,
  mapping, metric, decision, approval, readiness, or source artifact for writing.
- The result reports `written: []` on every refusal. On success, `written`
  contains the one relative manifest path and `approvals` remains empty.
- JSON results conform to `pbip-adoption-scaffold-result.schema.json`; text is
  derived from the same normalized result and carries equivalent substantive
  facts.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Exact assessment accepted and the one manifest was created |
| `1` | Governed refusal: stale digest, Git prerequisite, dirty input, collision, unsafe path, or staged-publication failure |
| `2` | Invalid command/input shape |

## Determinism and safety

- No timestamps or machine-local roots are included in substantive output.
- SHA-256 identifies content equality only and is never displayed as a score.
- Lists are deterministically ordered and JSON keys are serialized canonically for
  digest computation.
- Errors are concise, redacted, and traceback-free for supported failure modes.
- `.pbix` is never opened or parsed; the response explains how to save a PBIP and
  stops.
