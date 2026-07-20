# Source Intelligence (Layer 2)

Planning (docs/templates; no runtime code).

Layer 2 of the Tower BI Agent Kit -- Source Intelligence. This doc explains the two
OPTIONAL semantic-proposal artifacts that strengthen **Source Ready (Stage 1)** and how
a filled copy of each contributes `evidence[]` to a table's readiness status. It adds
NO new stage, status, blocking reason, or confidence number; it reuses the Source Ready
vocabulary already defined in `docs/readiness/source-ready.md`.

## The two artifacts

| Artifact (template) | Records | A filled copy lives at |
|---------------------|---------|------------------------|
| `templates/business-meaning-registry.md` | a business term -> canonical meaning -> surface forms -> `proposed`/`confirmed` status -> evidence | `mappings/<table>/business-meaning-registry.md` |
| `templates/retail-term-dictionary.md` | a source-language (e.g. Arabic) term -> canonical English meaning -> synonyms/variants -> status -> evidence, with RC8 returns discipline | `mappings/<table>/retail-term-dictionary.md` |

Both are GENERIC schemas. The filled bilingual values for a real table are a per-table
instance authored during onboarding (roadmap F006), never baked into the templates. The
C086 reference mappings in `docs/data-dictionary.md` are the worked example the
templates CITE.

## Why they exist

Source Ready requires the analyst to PROPOSE the semantic meaning of a raw source --
what a column means, what a coded value rolls up to, what a bilingual billing/segment
term means in English -- and to mark each as a proposal awaiting sign-off, never as
invented fact (`docs/readiness/source-ready.md`). These two templates give that
"PROPOSED, not invented" work a reusable, reviewable shape instead of ad-hoc prose, so a
new source does not re-derive it each time.

## How they feed Source Ready evidence (the generic trace)

These artifacts contribute `evidence[]`; they never themselves grant a `pass`. The
mapping onto the EXISTING Source Ready statuses (no new status introduced):

| State of the registry/dictionary | Source Ready status | Why |
|-----------------------------------|---------------------|-----|
| Absent (or no semantic work done) | `not_started` / `blocked` | the profile may exist, but the semantic-proposal half is missing -- the stage is not `pass` on numbers alone |
| Filled, every meaning `proposed` + flagged, profile recorded | contributes to `pass` evidence -- BUT `pass` only AFTER the analyst confirms | a proposal is not yet a confirmed meaning; the named human sign-off is what promotes the stage |
| Filled but a meaning is INVENTED (asserted as fact, a self-confirmed rollup/PII) | `blocked` | uses the EXISTING blocking reason "Semantic meaning INVENTED ... rather than PROPOSED" -- no new blocking reason |

So: an empty registry maps to `blocked`/`warning`; a filled-and-proposed registry is
`pass` EVIDENCE once the analyst confirms; an invented-meaning registry is a `blocked`
with the blocking reason that already exists in `source-ready.md`. The whole trace uses
only the four-value spine vocabulary plus the `proposed`/`confirmed` entry-level status
-- and no numeric confidence score anywhere (roadmap rule #9).

## What this does NOT change

- It adds NO new readiness stage, status, blocking reason, or required artifact. The ONE
  required Source Ready artifact stays `source-profile.md`; the gate stays a review.
- It adds NO `seshat check` rule, NO Python, NO dependency.
- The `proposed`/`confirmed` value is an ENTRY-LEVEL meaning status inside a registry,
  not a new stage status -- the table's Source Ready stage status remains the four-value
  spine vocabulary.

## See also

- The stage advanced: `readiness/source-ready.md`.
- The spine + status vocabulary + no-fake-confidence rule: `readiness/readiness-model.md`,
  `readiness/readiness-pipeline.md`.
- The two templates: `../templates/business-meaning-registry.md`,
  `../templates/retail-term-dictionary.md`.
- The roadmap row + hard rules: `roadmap/roadmap.md` (F007, Layer 2; #7/#8/#9).
- Principles: `../.specify/memory/constitution.md` V, VI/RC8, VII.
- The filled instance the templates cite: `data-dictionary.md`,
  a filled worked example under `worked-examples/`.
