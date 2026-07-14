# Agent Compatibility Evidence (`seshat agent verify`)

`seshat agent verify --target claude|codex` answers one question per shipped
agent integration: *does this integration install correctly, and does it
ship the Seshat governance contract intact?* It answers as **categorical
evidence**, never a certification.

## The three verdicts

Every required check resolves to exactly one of:

- **PASS** -- the check ran, its evidence is present, and it matched the
  expected outcome.
- **BLOCKED** -- the check ran but did not pass: a governance mismatch, a
  drifted bundle, an incompatible version, or missing/malformed evidence.
  Fail-closed; carries at least one concrete blocking reason.
- **UNAVAILABLE** -- the check could not run at all (an unsupported surface,
  such as no IDE surface for a target that ships none). Distinct from
  BLOCKED; never coerced to PASS.

Verify never emits or implies a score, percentage, rank, pass-rate, grade,
leaderboard, or a single rolled-up "certified"/"verified" pass. The overall
result is the set of per-check verdicts plus a truthful summary naming any
non-PASS check.

## Exit codes

```text
0  every required check is PASS
1  at least one required check is BLOCKED
2  input defect: unknown --target, or an uncontained --output/--publish path
3  at least one required check is UNAVAILABLE and none is BLOCKED
```

An UNAVAILABLE-only run never exits `0` -- that would read as a false pass.

## The eleven required checks

Six are **per-target** (the layer that genuinely differs between
`--target claude` and `--target codex`):

| check_id | foundation | evidence source |
|---|---|---|
| `install_discovery` | release-verification (spec 108) | plugin manifest + marketplace/discovery entry + provenance manifest |
| `version_compatibility` | release-verification (spec 108) | `scripts.check_release_versions.audit_versions` |
| `update_integrity` | the exporter's provenance manifest | `output_sha256` per generated file |
| `uninstall_integrity` | the exporter's provenance manifest | the declared installed footprint (destination paths) |
| `ide_surface` | the target's own declared metadata | `plugin.json`'s `interface` block, only where declared |
| `governance_contract_presence` | the target's own exported bundle | that target's `portable-operating-contract.md` |

Five are **shared-baseline** (repo-level, target-invariant; the committed
benchmark scenarios and the read-only governor are identical regardless of
`--target`, so their evidence is labeled a shared baseline, not per-target):

| check_id | cited scenario / surface |
|---|---|
| `readiness_routing` | the read-only governor (`seshat.governor.service`) |
| `pii_refusal` | `rs-pii-exposure` |
| `no_self_approval` | `hs-self-grant-approval` |
| `no_silver_before_mapping` | `hs-silver-before-mapping` |
| `no_invented_metric_meaning` | `rs-metric-without-approval` |

## Static-first, not live-agent-driving

Verify inspects the **installed bundle and its static governance contract**:
the generated plugin files, the provenance manifest, the version/
compatibility declarations, and the committed benchmark scenarios matched
against the deterministic scripted reference. It never launches Claude or
Codex, sends a live prompt, or observes a stochastic model's behavior. It
requires no database, no credentials, no external service, and no running
IDE (every required check either runs fully offline or reports UNAVAILABLE).

## Running

```console
$ seshat agent verify --target codex
agent verify --target codex
[PASS] install_discovery (per_target)
    evidence: plugin manifest resolved: ...
...
summary: every required check is PASS (evidence only; grants no approval)
written: .seshat-output/agent-verify/record.json

$ seshat agent verify --target claude
...
[UNAVAILABLE] ide_surface (per_target)
    unavailable: claude declares no IDE surface for this bundle
summary: UNAVAILABLE: ide_surface
written: .seshat-output/agent-verify/record.json
```

The evidence record is written locally under `.seshat-output/` by default.
Publication (`--publish`) is an explicit, owner-controlled action gated on a
clean disclosure scan (no secret, connection string, absolute path, or
possible PII); it is refused otherwise, and no external submission is
performed.

## What verify does not do

- It does not grant readiness or approval to any agent, and it does not
  advance any readiness stage (Principle V; hard rule #9).
- It does not reimplement hashing, version parsing, scenario execution, or
  governance rules -- it reuses the shipped release-verification, benchmark,
  and governor surfaces.
- It does not certify an agent as "compliant"; a PASS only means the cited
  static evidence and the deterministic reference baseline are present and
  match the declared expectation.
