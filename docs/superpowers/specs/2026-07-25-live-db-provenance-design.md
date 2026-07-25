# Live-DB provenance for readiness evidence -- design note (issue #485)

- **Date:** 2026-07-25
- **Status:** **DESIGN NOTE -- decides nothing.** Written at owner direction
  ("design note only, no code"). No field is added, no schema is edited, and no
  rule is wired by this note. It exists so the owner can rule on a concrete shape
  rather than on a bug report.
- **Revised 2026-07-25** after a follow-up investigation, which changed the
  recommendation. Two claims in the first draft were wrong and are corrected
  below: (1) the change is **not** a breaking schema change -- see "Cost
  correction"; (2) the hard part is not adding the field but **wiring a writer
  that cannot lie** -- see "The decisive question". A hand-authored provenance
  field is now explicitly recommended AGAINST.
- **Issue:** #485 -- `seshat next` reports `terminal_pass` from committed
  `mappings/` evidence without cross-checking live DB identity.
- **Related:** #486 (rule-scope qualification), #487 (approval-shape
  qualification). All three are the same seam at different levels; see "Why this
  is the third instance" below.

## The defect, reproduced

Built offline, no database touched: a temp repo with one
`mappings/sales_c086_raw/readiness-status.yaml` at seven stages `pass` with
shape-valid approvals and evidence strings naming "Ex-1 (live)", plus `.env` and
process env pointing `ANALYTICS_DB_NAME` / `SESHAT_DBT_DBNAME` at an unrelated
database. Result:

```
outcome = terminal_pass | readiness_state = pass | caveats = []
```

The evidence is echoed verbatim. Nothing indicates the configured live DSN now
resolves to a different -- and far less complete -- database.

Reporter's field case: `bronze.sales_c086_raw` was copied into a new database
`ex-3` (bronze only, no silver/gold ever built there) and `.env` repointed. The
tool still reported all seven stages `pass`, citing the `Ex-1` evidence.

## Root cause

`terminal_pass` is decided after looping the seven stages of the committed YAML,
whose sole input is the readiness file:

- `src/seshat/run_next.py:420-422` -- returns `terminal_pass`
- `src/seshat/agent_next.py:288-306` -- `readiness_state` becomes `"pass"`
  unconditionally when `outcome == "terminal_pass"`
- `src/seshat/status_surface.py:118-138` -- `seshat status` projects the same
  YAML verbatim, same gap

There is no DB-identity comparison anywhere in this path, by design: these
modules document a no-DB/no-network contract (`agent_next.py:19-24`,
`status_surface.py:9-11`, `run_next.py:5-7`). **The bug is not that they refuse
to connect -- it is that the evidence they trust carries no machine-checkable
statement of which live system earned it.**

### No structured DB-identity field exists today

Grepped `templates/`, `schemas/`, and every committed `mappings/*`: no
`database` / `dbname` / `host` / `fingerprint` field anywhere. DB identity exists
only as free prose inside `evidence[]` -- e.g.
`mappings/retail_store_sales/readiness-status.yaml:42` reads
`"...0003_create_silver_retail_store_sales.sql applied to training; 12,575 silver
rows"`, where `training` is a database name in a sentence. Adjacent evidence
schemas do not carry it either: `dbt-run-evidence.schema.json:63`'s `target` is
`{"name": {"const": "shadow"}, "schemas": {...}}`; `dagster-run-evidence` carries
`run_id, commit_sha, workspace_dirty, tables, run_status`.

### A precision caveat, so the record is accurate

`next_allowed_action` *can* emit a `STOP ... [PENDING LIVE PROFILE]` line via
`_live_validation_next_override` (`agent_next.py:242-274`), and it did fire in the
reproduction. But that override keys on **committed-artifact / repo-revision**
identity, not database identity: `_dagster_run_states`
(`portfolio_watch.py:479-521`) checks `commit_sha`, `workspace_dirty`, input
digests, and `run_status`. With verified run evidence present it returns
`verified` and the override goes silent -- even when that evidence was produced
against a different database. `outcome`, `readiness_state`, and `evidence[]` are
never qualified on any path.

## The decisive question: would the field be TRUSTWORTHY?

This is the question that actually chooses between the options below, and it was
not asked in the first draft of this note. A structured field is only an
improvement over prose if its value cannot be typed by whoever is claiming the
readiness. Otherwise it relocates the honesty problem into a tidier format.

**Finding: nothing in the codebase writes stage status today.** An exhaustive
grep for writers of `readiness-status.yaml` yields three touch points, none of
which authors a `status`, `evidence[]`, or `approvals[]` value:

- `stage1_scaffold.py:36,232,307-349` -- copies the BLANK template via `O_EXCL`
  atomic create; every stage `not_started`
- `demo/fixtures.py:88` -- byte-copies an already-filled fixture
- `reset.py:465-475` -- deletes/edits; never authors status

Every real value is hand-authored by an agent or human through the skills
(`retail-onboard-table/SKILL.md:99-100`, `approval-console/SKILL.md:163`). So a
`sha256(host/dbname)` computed from `.env` is **forgeable by any agent that can
read `.env` without ever opening a socket.** That field would be tool-formatted
prose. It must not be added on those terms.

**Where a trustworthy value could come from -- three existing seams:**

1. **`seshat validate` is the natural capture point and records nothing today.**
   It connects (`cli/commands/validate.py:93-112`), prints findings, sets an exit
   code, and persists no artifact. It is the only place a *server-echoed*
   identity is obtainable -- `select current_database()` through the `QueryRunner`
   Protocol (`validate.py:34-37`). Server-echoed beats env-derived: the database
   itself asserts its own name.
2. **`readiness_evidence.py` is already built and UNWIRED.** It is EMIT-only by
   FR-013 (`readiness_evidence.py:26`), returns a dict, writes nothing, and only
   tests call `build_gold_ready_block`. A dead seam waiting for exactly this.
3. **The dbt adapter already holds the value and deliberately throws it away.**
   `dbt/project.py:30-38` reads the real host/dbname at run time;
   `dbt/redaction.py:13-40` discards them. What it records instead is a *profile
   alias*: `evidence.py:663` writes `target={"name": plan.runtime.target, ...}`
   and the schema pins that to `{"const": "shadow"}`
   (`dbt-run-evidence.schema.json:68`). Its write path is otherwise sound --
   sanitize -> schema-validate -> atomic write into a COMMITTED
   `mappings/<table>/dbt-evidence/<id>.json` (`dbt/evidence.py:785-797`).

## Cost correction -- the schema break claim was WRONG

The first draft of this note asserted that `schemas/agent-status.schema.json`
being `additionalProperties: false` makes the field a breaking change. **That is
refuted.** That schema self-describes (`:5`) as the contract for
`retail status --format json` -- an OUTPUT projection. **No schema in `schemas/`
validates `readiness-status.yaml` as an input file at all**; only rule RS1 reads
it. And `status_surface.py:80-97` projects a strict six-key whitelist, silently
dropping unknown input keys.

Therefore: **adding the field to the YAML is ADDITIVE -- zero schema edit, zero
break.** It becomes breaking only if someone *chooses* to project it into the
output contract, which is severable and need not happen in the same change.

**And the migration cost is avoidable too.** `source_kind` (commit `64e3f88`,
#120) is the house precedent: an optional field added to an already-filled
artifact, where absence carries a valid legacy meaning
(`templates/readiness-status.yaml:56-59`) and the gate fires **only when the field
is present** (`rules/readiness_status.py:393-400`). Zero migration was needed.
The same shape applies here.

So the real cost profile inverts the first draft: **the field is cheap; the
writer that cannot lie is the expensive part.**

## A separate defect found while investigating this

Worth its own issue rather than being folded in here. Dagster raw run records are
**gitignored** (`.gitignore:111`), yet `portfolio_watch.py:479-521`
(`_dagster_run_states`) reads exactly that path and can return `verified` -- and
`verified` is the state that SILENCES the `[PENDING LIVE PROFILE]` caveat in
`agent_next.py:242-274`. So machine-local, unreviewable, uncommitted evidence can
suppress a safety caveat on a surface another person then reads as authoritative.
That is a trust-boundary problem independent of DB identity.

### Hard constraint: the field must not store a raw DSN

`ANALYTICS_DB_NAME` is on this repo's own secret/redaction lists
(`dagster_adapter/redaction.py:53`, `rules/git_meta.py:506,513`,
`severity_posture.py:375`). A provenance field that committed a raw host or
database name would put a redacted value into a tracked file -- trading a
correctness bug for a secret-hygiene bug. It must store a **stable, salted-or-
plain digest** (e.g. `sha256("<host>/<dbname>")`, truncated) that can be compared
without disclosing the target.

### Comparison is possible without opening a connection

Two existing helpers make a *recorded-vs-configured* check feasible while keeping
the no-DB contract intact:

- `seshat.validate.resolve_dsn(env)` (`validate.py:53-83`) -- pure env -> string,
  explicitly driver-free (`validate.py:47`)
- `seshat.connection_env.connection_environment(repo_root)`
  (`connection_env.py:105-115`) -- `.env` overlay without mutating `os.environ`

So the check reads config, never the database. Note `rules/live_surface_boundary.py`
(B3) is an *import-boundary* guard and cannot be extended for this.

## Options for the owner (revised after the trustworthiness finding)

The original A/B/C framing was wrong because it treated "add the field" as the
hard part. The real axis is *who writes it*.

**A1 -- Hand-authored provenance field. REJECT.**
Add the field, document it, let the skills fill it. Cheap, additive, no
migration -- and worthless: the only writers are agents editing YAML, so the
digest is forgeable from `.env` without touching a database. This would let a
table claim machine-checked provenance it never earned, which is strictly worse
than today's honest silence. **Recommend against.**

**A2 -- Machine-written provenance, server-echoed (the real fix).**
Wire `validate.py` (the code that already connects) through the built-but-unwired
`readiness_evidence.py` to persist a digest of `select current_database()` at the
moment findings were produced; have `next`/`status` compare that against the
configured DSN and downgrade with a named blocker on mismatch. Use the
`source_kind` shape: optional field, gate fires only when present, zero
migration, no output-schema change. Optionally also stop `dbt/redaction.py`
discarding the digest it already holds. **Cost is in the writer, not the field.**

**B -- Non-blocking caveat only.**
`next`/`status` always state that stage evidence carries no machine-checkable DB
provenance. Honest and cheap, but warns identically on every table, so it will be
tuned out and does not detect the reporter's case. Useful as an interim signal
*alongside* A2, not as a resolution.

**C -- Document the limitation, change nothing.**
Leaves an agent or analyst able to read `terminal_pass` for a database that has
none of the claimed objects -- the specific trust failure the gate exists to
prevent.

**Recommendation: A2, with B shipped first as the interim signal.** Explicitly
reject A1 -- if A2's writer is not built, prefer B's honest silence over a field
that can be typed. Neither B nor C should be treated as closing #485.

**Sequencing note:** A2 is a genuine feature with a live-connection write path,
not a bug fix. It wants its own spec and an owner decision on whether `validate`
may write a committed artifact at all (today it deliberately writes nothing).
That is the one question to settle before any code.

## Why this is the third instance of one seam

#485, #486, and #487 are the same architectural gap at three levels: evidence is
trusted for what it *asserts*, never qualified by *where it came from*.

- #487 -- shape level: is this approvals[] entry well-formed? (three surfaces
  disagreed; fixed by one shared predicate)
- #486 -- scope level: does this rule even apply to this repo? (substrate presence
  was mistaken for kit identity; fixed by splitting the predicate)
- #485 -- provenance level: which live system earned this evidence? (**open** --
  no field exists to answer it)

Each fix adds a *qualifier* to a fail-closed gate, and adding a qualifier can flip
currently-passing states. #487's tightening was safe because a census proved every
committed entry already used `at:`. #485 differs in kind: no committed record
carries provenance at all, so the qualifier cannot be *required* -- it has to fire
only when present (the `source_kind` shape), which is why the migration cost
initially attributed to it does not actually apply.

The sharper lesson from #485 is one the other two did not raise: **a qualifier is
only worth adding if the party being qualified cannot author it.** #487's `at:` is
weakly self-authored but harmless (a wrong date does not fake a database), and
#486's predicate reads immutable repo facts. #485's provenance is the first
qualifier where the writer's honesty is the entire question -- which is why A1 is
rejected and A2 needs a spec.

## Governance

No hard rule is violated by the current behavior: the surfaces faithfully report
committed state and fabricate nothing. This is a **qualification gap**, not a
fabricated-readiness defect. Nothing in this note grants a stage, ratifies a
decision, or emits a confidence score.
