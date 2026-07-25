# Nulls, Missing Values, Blanks, and Sentinels

Use this route to classify missing-looking values before filling, dropping, or
standardizing them. End on `checklists/dataframe-review-checklist.md`.

## Decision this route supports

Decide which missing representations are equivalent, which retain distinct meaning,
and which require a named owner decision.

## Required evidence

- raw representations and counts by field/segment;
- field role: key, measure, category, timestamp, or descriptive text;
- source-system sentinel documentation;
- downstream KPI and mapping requirements;
- named authority for unresolved dispositions.

## Reasoning sequence

**PY-PB-014 — Missingness classification**

- **PY-CN-111 — Null, blank, whitespace, and sentinel are not automatically equal.**
- **PY-CN-112 — Missingness has causes.** Not captured, not applicable, not yet
  available, redacted, and invalid should remain distinguishable when policy requires.
- **PY-CN-113 — Null keys threaten identity.** Quantify and quarantine before joins.
- **PY-CN-114 — Null measures are not zero.** Filling changes aggregates and requires
  a metric/source policy.
- **PY-CN-115 — Unknown categories require an approved member.** Display convenience
  does not authorize a business rollup.
- **PY-CN-116 — Sentinel mapping is lineage.** Preserve original literal, mapped value,
  rule identifier, affected count, and authority.

**PY-BP-012 — Defer irreversible filling.** Classify and record first; transform only
after the source map or owner decision specifies the disposition.

## Failure modes

- blanket `fillna(0)`;
- blank keys retained as joinable members;
- `-1` or `999` included in sums;
- `Unknown` invented without model policy;
- missing timestamps dropped, hiding late-data problems.

## Evidence-based verdict

- **CLEAN** — representations, causes, and approved dispositions are recorded.
- **BLOCKED** — disposition changes business meaning or identity without authority.
- **HANDOFF** — send unresolved sentinel/null decisions to source mapping/readiness.

## Stop and handoff

This layer records and applies approved decisions; it never self-grants the decision.
