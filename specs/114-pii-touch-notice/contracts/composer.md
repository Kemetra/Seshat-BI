# Contract: PII Notice composer + CLI verb

## Python API

`src/retail/pii_notice.py`

```
def build_pii_notice(repo_root: Path | str, table: str) -> dict
```

- **Reads**: `<repo_root>/mappings/<table>/source-map.yaml` ONLY (via a private
  `_load_yaml_mapping` mirroring `blocker_explainer._load_yaml_mapping`:
  `utf-8-sig` read, returns None on OSError/UnicodeDecodeError/YAMLError).
- **Returns** a dict (the PiiNotice model in data-model.md):
  ```
  {
    "table": str,
    "source_path": str,                 # repo-relative
    "findings": [ {                     # one per pii:true column
        "column": str,
        "decision": str | None,
        "state": "decided_kept" | "decided_dropped" | "undecided" | "inconsistent",
        "disposition": str | None,      # VERBATIM echo; None when undecided
        "disposition_source": str | None,
    }, ... ],
    "no_pii": bool,
    "document_gap": str | None,
    "read_only_proof": True,
  }
  ```
- **Writes**: NOTHING from `build_*`. A separate `render_markdown(notice) -> str`
  produces the ASCII notice body; the CLI handler writes it to
  `mappings/<table>/pii-touch-notice.md` (the ONLY write, FR-008/Q2).
- **Never**: opens a DB/network/PBIP connection; imports a driver at module load;
  writes any upstream artifact; emits a score/count.

## Rendered markdown shape (ASCII, UTF-8 no BOM)

```
# Personal-Data-Touch Notice -- <table>

Source: mappings/<table>/source-map.yaml
This notice echoes committed PII flags and recorded governance dispositions.
It records no new judgment, grants no approval, and moves no stage.

## PII-flagged columns

- <column> -- flagged pii:true, decision:keep. Recorded disposition:
  "<verbatim disposition>" (mappings/<table>/source-map.yaml, defaults.deviations[RC4]).
- <column> -- flagged pii:true, decision:drop. Recorded reason:
  "<verbatim reason>" (mappings/<table>/source-map.yaml, columns[<name>].reason).

## Gaps

- GAP: <column> -- pii:true with NO recorded governance disposition
  (checked: mappings/<table>/source-map.yaml columns[<name>], defaults.deviations).
  This column is NOT cleared; a named human decision is not recorded.

<or, when no pii:true columns:>
## PII-flagged columns

No column in this table is flagged as personal data (pii:true) in source-map.yaml.

<or, document-level gap:>
GAP: document -- source-map.yaml missing or unreadable
(checked: mappings/<table>/source-map.yaml). No PII finding could be composed.
```

Rules the render obeys: verbatim disposition in quotes with its in-file locus;
a GAP line always carries "NOT cleared" framing (never clearance); no numeric
token anywhere; ASCII `--`/`->`, no glyphs.

## CLI verb

`src/retail/cli/commands/pii_notice.py` (mirrors `commands/blockers.py`):

```
retail pii-notice --table <table> [--format text|json] [--write]
```

- Default `--format text` prints the rendered notice; `--format json` prints the
  `build_pii_notice` dict.
- `--write` writes `mappings/<table>/pii-touch-notice.md` (idempotent overwrite);
  without it, the notice is printed only (a dry read).
- Returns exit `0` always (it is not a gate; FR-007). A missing source-map yields
  a document-level GAP in the output, not a non-zero exit.
- Registered in `cli/parser.py` and dispatched in the CLI dispatch table,
  following the shipped `blockers` / `next` wiring.

## Non-gating verifier (tests, FR-011)

`tests/unit/test_pii_notice.py` provides a reusable
`assert_notice_is_faithful(notice_text, source_map_path)` helper asserting V1-V4
(data-model.md). It is a TEST artifact; there is NO `@register` retail check rule
and NO change to the rules manifest (FR-007).
