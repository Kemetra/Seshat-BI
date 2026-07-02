# Ratify Ledger — 076 extract the pure agent-driven BI kit

**This is the STOP point. It is a SPEC — it executes nothing.** No data deleted, no
history rewritten, no file moved, the in-flight c086 work untouched (SC-006). The
implementation is a SEPARATE future PR, gated on (a) the decisions below and (b) the
in-flight c086 supersession work resolving.

## What was delivered (the 5 requested outputs)

| Deliverable | File |
|-------------|------|
| 1. spec.md | `spec.md` — scope, complete-classification requirement, non-regression, security + acceptance |
| 2. plan.md | `plan.md` — classification table + catch-all, 3-strategy comparison + recommendation, migration runbook, security decision, acceptance criteria |
| 3. tasks.md | `tasks.md` — Group A (spec deliverables) + Group B (future-PR runbook, not executed) |
| 4. adversarial / risk review | `risk-review.md` — my risk pass + an independent skeptic (BLOCK → fixed → PASS-WITH-NOTES) |
| 5. recommendation | below + plan §Recommendation |
| (support) research.md | `research.md` — package-clean proof, data-independence, security scoping, ASSESS method |

## The adversarial review earned its keep

The independent skeptic **BLOCKED the first draft** and was right: my classification
**omitted `powerbi/`** — which ships a full client BI model (`c086 _sales.*` + a
generically-NAMED copy `Retailgold.*` = the same c086 star) — and my "no host committed"
finding was **false** (the real cluster id `db-<cluster-id>` + `ezaby_demo` are in 7
files, evading both the C2 gate's FQDN-only regex and my first grep). Both would have let
the future PR **ship client data while reporting "clean."** Fixed: complete top-level
classification + a catch-all, `powerbi/` archived, corrected security finding, broadened
acceptance grep (verified it now catches `powerbi/c086 _sales.*` + the cluster id). The
true blast radius is **126 tracked files** carrying client markers.

## The RECOMMENDATION (deliverable 5)

**Package + archive — NOT a repo split.** The tool is ALREADY a clean pip package
(`pyproject.toml` packages only `src/retail`; the wheel carries zero data — verified). So
"extract the pure tool" is largely already true at the PACKAGE boundary; what remains is
cleaning the SOURCE TREE (archive the 126 client-marker files out) + a history decision.
A full repo split is heavier than the goal ("pure reusable kit") requires. Split only if
the training repo must live on as its own maintained thing — a later call, not required.

**Security: current-tip redaction now; git-history purge ONLY on a public-release /
erasure trigger.** No credential/PII-rows committed (host id is identifying, not secret);
the shipped wheel never carried the data; a 302-commit purge is disproportionate for a
private repo. Add the cluster id + `ezaby_demo` + bare `c086` to the redaction; keep purge
as a separate, explicitly-authorized operation.

## Decisions the owner must make (the STOP)

1. **DEC-1 — Extraction strategy:** package+archive (recommended) / repo split / other.
2. **DEC-2 — Security posture:** tip-redaction now (recommended) / purge history now /
   defer purge to a public-release trigger (recommended default = tip-redaction +
   trigger-gated purge).
3. **DEC-3 — Synthetic examples:** narrative-only + one tiny synthetic table (recommended)
   / narrative-only / build a synthetic warehouse.
4. **DEC-4 — Ordering ack:** confirm the future PR waits for the in-flight c086
   supersession work to land/discard first.

## Approval slot — TO BE FILLED BY A NAMED HUMAN

> To authorize the future implementation PR: state DEC-1..DEC-4 and set `spec.md` Status
> to Ratified. The implementation PR is a SEPARATE, later change; this spec builds nothing.

- **DEC-1 strategy**: **package + archive** (NOT a repo split) — the recommended default.
- **DEC-2 security**: **current-tip redaction now** (add cluster id `db-<cluster-id>`
  + `ezaby_demo` + bare `c086` to the redaction targets); **history purge DEFERRED** to a
  public-release / erasure trigger, as a separately-authorized operation — the recommended
  default.
- **DEC-3 examples**: **narrative-only worked example + one tiny synthetic table** — the
  recommended default.
- **DEC-4 ordering ack**: **acknowledged** — the extraction PR waits for the in-flight
  c086 supersession work to resolve first (now clean).
- **Named owner / date**: **Ahmed Shaaban, 2026-07-02** (owner directive "ratify 076 with
  recommended decisions"; transcribed per the delegated-authority pattern, cf. 062/072).
- **Build authorization** (may the future extraction PR proceed, post-c086-resolution?):
  **Yes** — the future extraction PR (tasks.md Group B) is authorized under DEC-1..DEC-4.
  It is a SEPARATE change; its own PR merge remains a distinct act.

`spec.md` is now **Ratified (Ahmed Shaaban, 2026-07-02)**. The future extraction PR is
authorized under the four decisions above; no extraction/deletion/history change occurs
until that separate PR runs.
