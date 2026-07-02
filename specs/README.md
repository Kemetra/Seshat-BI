# specs/ -- reference conventions and known provenance caveats

This directory holds the per-feature spec dirs. Two facts about how they are named
and referenced are load-bearing; read them before you cite a spec by number.

## 1. The full-slug directory name is the canonical reference -- NOT the bare number

Some spec numbers are DUPLICATED across two different directories. A bare "spec NNN"
reference is therefore ambiguous and unreliable. Always cite a spec by its full slug
directory name (e.g. `specs/067-seed-route-honesty-rule`) -- or by the commit SHA / PR
number that shipped it -- never by the bare number alone.

## 2. Duplicate-numbered directory pairs

| Number | Directory A | Directory B |
| --- | --- | --- |
| 044 | `specs/044-kpi-derivation-lineage` | `specs/044-live-surface-protocol` |
| 067 | `specs/067-bi-python-cleaning-artifacts` | `specs/067-seed-route-honesty-rule` |

Both members of each pair are real, committed spec dirs about different features. The
bare number does not disambiguate them.

## 3. Some shipped rules cite a bare number that matches NO committed spec dir

A bare "spec NNN" tag in a commit message is not a guarantee that a matching spec dir
exists. Confirmed example:

- Rule **AL2** (assumption-coherence) shipped in **PR #129 / commit cc606b8**, whose
  message reads `feat: AL2 cross-contract assumption-coherence rule (067, H2)`. That
  bare "067" matches NEITHER committed 067 dir -- neither `067-bi-python-cleaning-artifacts`
  nor `067-seed-route-honesty-rule` is about assumption-coherence. AL2 was hand-built
  (not spec-driven) and has no committed spec. See the provenance note in the docstring
  of `src/retail/rules/assumption_coherence.py`. This is acknowledged provenance debt.

Takeaway: bare "spec NNN" references cannot be trusted. Always resolve a spec by its
full slug directory or by the commit / PR that shipped it.
